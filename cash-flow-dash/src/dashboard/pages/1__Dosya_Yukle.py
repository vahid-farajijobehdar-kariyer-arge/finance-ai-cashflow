"""
📤 Dosya Yükle - Kariyer.net Finans

Banka POS ekstre dosyalarını yükleyin ve analiz edin.
Desteklenen formatlar: Excel (.xlsx, .xls), CSV

© 2026 Kariyer.net Finans Ekibi
"""

import hashlib
import logging
from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import streamlit as st

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control, get_control_summary
from processing.calculator import filter_successful_transactions, calculate_ground_totals

sys.path.insert(0, str(Path(__file__).parent.parent))
from format_utils import tl
from storage.metadata import MetadataManager, FileMetadata
from storage.cache import FileCache
from storage.azure_storage import (
    upload_file_to_azure, 
    is_azure_configured, 
    backup_all_raw_files,
    restore_from_azure
)

# Import auth module
sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password
from cache_utils import clear_all_data_caches, invalidate_data

# Data paths
RAW_PATH = PROJECT_ROOT.parent / "data" / "raw"
logger = logging.getLogger(__name__)


def init_upload_state():
    """Initialize upload session state."""
    # Bu session'da kaydedilen dosyaları takip et
    if "saved_file_hashes" not in st.session_state:
        st.session_state.saved_file_hashes = set()
    
    # File uploader key - değiştirerek uploader'ı sıfırla
    if "uploader_key" not in st.session_state:
        st.session_state.uploader_key = 0


def mark_file_as_saved(file_hash: str):
    """Dosyayı kaydedildi olarak işaretle."""
    st.session_state.saved_file_hashes.add(file_hash)


def is_just_saved(file_hash: str) -> bool:
    """Dosya az önce kaydedildi mi kontrol et."""
    return file_hash in st.session_state.get("saved_file_hashes", set())


def reset_uploader():
    """File uploader'ı sıfırla."""
    st.session_state.uploader_key += 1
    # Kaydedilen dosya listesini temizle
    st.session_state.saved_file_hashes = set()


def calculate_file_hash(file_content: bytes) -> str:
    """Dosya içeriğinin MD5 hash'ini hesapla."""
    return hashlib.md5(file_content).hexdigest()


def get_existing_file_hashes() -> dict:
    """Mevcut tüm dosyaların hash'lerini döndür."""
    hashes = {}
    
    if not RAW_PATH.exists():
        return hashes
    
    # Düz dosyalar
    for f in RAW_PATH.glob("*"):
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in [".csv", ".xlsx", ".xls"]:
            try:
                with open(f, "rb") as file:
                    file_hash = hashlib.md5(file.read()).hexdigest()
                    hashes[file_hash] = f
            except Exception:
                pass
    
    # Organize yapıdaki dosyalar
    for bank_dir in RAW_PATH.iterdir():
        if bank_dir.is_dir() and not bank_dir.name.startswith("."):
            for month_dir in bank_dir.iterdir():
                if month_dir.is_dir():
                    for f in month_dir.glob("*"):
                        if f.is_file() and f.suffix.lower() in [".csv", ".xlsx", ".xls"]:
                            try:
                                with open(f, "rb") as file:
                                    file_hash = hashlib.md5(file.read()).hexdigest()
                                    hashes[file_hash] = f
                            except Exception:
                                pass
    
    return hashes


def check_duplicate(file_content: bytes) -> tuple:
    """
    Dosyanın daha önce yüklenip yüklenmediğini kontrol et.
    
    Returns:
        (is_duplicate, existing_path) tuple
    """
    new_hash = calculate_file_hash(file_content)
    
    # Bu session'da az önce kaydedildiyse duplike değil
    if is_just_saved(new_hash):
        return False, None
    
    existing_hashes = get_existing_file_hashes()
    
    if new_hash in existing_hashes:
        return True, existing_hashes[new_hash]
    
    return False, None


def init_managers():
    """Initialize storage managers."""
    if "metadata_manager" not in st.session_state:
        st.session_state.metadata_manager = MetadataManager()
    if "file_cache" not in st.session_state:
        st.session_state.file_cache = FileCache()
    if "bank_reader" not in st.session_state:
        st.session_state.bank_reader = BankFileReader()
    return st.session_state.metadata_manager, st.session_state.file_cache


# Desteklenen banka listesi (dropdown'da kullanılan)
BANK_OPTIONS = ["Vakıfbank", "Akbank", "Garanti", "Halkbank", "Ziraat", "YKB", "QNB", "İşbankası"]

# Banka adı eşleştirme - API'den gelen adları standart adlara çevir
BANK_NAME_MAPPING = {
    # Akbank
    "akbank": "Akbank",
    "akbank t.a.s.": "Akbank",
    "akbank t.a.ş.": "Akbank",
    # Garanti
    "garanti": "Garanti",
    "garanti bbva": "Garanti",
    "t. garanti bankasi a.s.": "Garanti",
    # Vakıfbank
    "vakıfbank": "Vakıfbank",
    "vakifbank": "Vakıfbank",
    "t. vakiflar bankasi t.a.o.": "Vakıfbank",
    "t. vakıflar bankası t.a.o.": "Vakıfbank",
    # Halkbank
    "halkbank": "Halkbank",
    "t. halk bankasi a.s.": "Halkbank",
    # Ziraat
    "ziraat": "Ziraat",
    "t.c. ziraat bankasi a.s.": "Ziraat",
    "ziraat bankası": "Ziraat",
    # YKB
    "ykb": "YKB",
    "yapı kredi": "YKB",
    "yapıkredi": "YKB",
    "yapi ve kredi bankasi a.s.": "YKB",
    # QNB
    "qnb": "QNB",
    "qnb finansbank": "QNB",
    "qnb finansbank a.s.": "QNB",
    "finans": "QNB",
    # İşbankası
    "işbankası": "İşbankası",
    "isbank": "İşbankası",
    "işbank": "İşbankası",
    "t. is bankasi a.s.": "İşbankası",
    "türkiye iş bankası": "İşbankası",
}


def normalize_bank_name(bank_name: str) -> str:
    """Normalize bank name to standard dropdown value."""
    if not bank_name:
        return None
    
    bank_lower = bank_name.lower().strip()
    
    # Önce tam eşleşme dene
    if bank_lower in BANK_NAME_MAPPING:
        return BANK_NAME_MAPPING[bank_lower]
    
    # Parçalı eşleşme dene
    for pattern, standard_name in BANK_NAME_MAPPING.items():
        if pattern in bank_lower or bank_lower in pattern:
            return standard_name
    
    # Dropdown'daki değerlerle doğrudan eşleşme
    for opt in BANK_OPTIONS:
        if opt.lower() in bank_lower or bank_lower in opt.lower():
            return opt
    
    return None


def detect_bank_from_filename(filename: str) -> str:
    """Detect bank name from filename."""
    filename_lower = filename.lower()
    
    for pattern, standard_name in BANK_NAME_MAPPING.items():
        if pattern in filename_lower:
            return standard_name
    
    return None


def analyze_uploaded_file(file_content: bytes, filename: str) -> dict:
    """Analyze uploaded file using BankFileReader."""
    import tempfile

    tmp_path: Path | None = None
    
    try:
        # Save to temp file for BankFileReader
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(file_content)
            tmp_path = Path(tmp.name)

        # Use BankFileReader to parse
        reader = BankFileReader()
        df = reader.read_file(tmp_path)
        
        # Detect bank
        bank_name = detect_bank_from_filename(filename)
        if "bank_name" in df.columns and df["bank_name"].iloc[0]:
            bank_name = df["bank_name"].iloc[0]
        
        # Filter successful transactions
        df_filtered = filter_successful_transactions(df)
        
        # Add commission control
        df_controlled = add_commission_control(df_filtered, bank_name or "Unknown")
        
        # Get summary
        control_summary = get_control_summary(df_controlled)
        
        # Calculate totals
        totals = calculate_ground_totals(df_controlled)
        
        return {
            "success": True,
            "row_count": len(df),
            "filtered_count": len(df_filtered),
            "columns": list(df.columns),
            "bank_name": bank_name,
            "control_summary": control_summary,
            "totals": totals,
            "df": df_controlled,  # Keep for display
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "row_count": 0,
        }
    finally:
        if tmp_path:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Geçici dosya silinemedi: %s", tmp_path)

def sanitize_filename(filename: str) -> str:
    """Strip directory components and reject suspicious names."""
    sanitized = Path(filename).name.strip()
    
    if sanitized in {"", ".", ".."}:
        raise ValueError("Geçersiz dosya adı")
    
    # Prevent hidden files like .env being uploaded without confirmation
    sanitized = sanitized.lstrip(".")
    if not sanitized:
        raise ValueError("Geçersiz dosya adı")
    
    return sanitized


def ensure_within_raw(dest_path: Path) -> None:
    """Ensure destination path stays inside RAW_PATH."""
    raw_root = RAW_PATH.resolve()
    resolved_dest = dest_path.resolve()
    if not resolved_dest.is_relative_to(raw_root):
        logger.warning("Path traversal engellendi: %s -> %s", dest_path, resolved_dest)
        raise ValueError("Geçersiz dosya yolu")


def save_to_raw_organized(file_content: bytes, filename: str, bank_name: str, file_date: datetime = None) -> Path:
    """
    Save uploaded file to data/raw/ organized by bank/month.
    
    Structure: data/raw/BANKA/YYYY-MM/filename.xlsx
    """
    # Banka klasörü
    bank_folder = bank_name.replace(" ", "_").upper() if bank_name else "UNKNOWN"
    
    # Ay klasörü (dosya tarihi veya bugün)
    if file_date:
        month_folder = file_date.strftime("%Y-%m")
    else:
        month_folder = datetime.now().strftime("%Y-%m")
    
    # Hedef klasör oluştur
    dest_folder = RAW_PATH / bank_folder / month_folder
    dest_folder.mkdir(parents=True, exist_ok=True)
    
    sanitized_name = sanitize_filename(filename)
    dest_path = dest_folder / sanitized_name
    
    # Dosya varsa timestamp ekle
    if dest_path.exists():
        stem = dest_path.stem
        suffix = dest_path.suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = dest_folder / f"{stem}_{timestamp}{suffix}"
    
    with open(dest_path, "wb") as f:
        f.write(file_content)
    
    return dest_path


def save_to_raw(file_content: bytes, filename: str) -> Path:
    """Save uploaded file to data/raw/ directory (legacy - flat structure)."""
    RAW_PATH.mkdir(parents=True, exist_ok=True)
    sanitized_name = sanitize_filename(filename)
    dest_path = RAW_PATH / sanitized_name
    ensure_within_raw(dest_path)
    
    # If file exists, add timestamp
    if dest_path.exists():
        stem = dest_path.stem
        suffix = dest_path.suffix
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest_path = RAW_PATH / f"{stem}_{timestamp}{suffix}"
        ensure_within_raw(dest_path)
    
    with open(dest_path, "wb") as f:
        f.write(file_content)
    
    return dest_path


def render_upload_section():
    """Render file upload section with drag-and-drop."""
    # Session state başlat
    init_upload_state()
    
    st.header("📤 Dosya Yükle")
    
    st.markdown("""
    ### 🏦 Banka Ekstreleri Yükleme
    
    CSV veya Excel dosyalarınızı sürükleyip bırakın veya seçin.
    Desteklenen bankalar: **Vakıfbank, Akbank, Garanti, Halkbank, Ziraat, YKB, QNB, İşbankası**
    
    ---
    """)
    
    # File uploader with dynamic key (değişen key ile uploader sıfırlanır)
    uploaded_files = st.file_uploader(
        "📁 Dosya Seçin",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        key=f"file_uploader_{st.session_state.uploader_key}",
        help="CSV veya Excel formatında banka ekstre dosyaları (max 100MB)"
    )
    
    if uploaded_files:
        st.markdown("---")
        st.subheader("📊 Yüklenen Dosyalar")
        
        for uploaded_file in uploaded_files:
            file_content = uploaded_file.read()
            
            # Duplicate kontrolü
            is_duplicate, existing_path = check_duplicate(file_content)
            
            with st.expander(f"📄 {uploaded_file.name}", expanded=True):
                # Duplicate uyarısı
                if is_duplicate:
                    st.warning(f"⚠️ **DUPLIKE DOSYA!** Bu dosya zaten mevcut: `{existing_path.relative_to(RAW_PATH)}`")
                    
                    col_dup1, col_dup2 = st.columns(2)
                    with col_dup1:
                        skip_duplicate = st.checkbox(
                            "Bu dosyayı atla",
                            value=True,
                            key=f"skip_{uploaded_file.name}"
                        )
                    with col_dup2:
                        if st.button("🗑️ Mevcut dosyayı sil", key=f"del_existing_{uploaded_file.name}"):
                            try:
                                existing_path.unlink()
                                # Boş kalan klasörleri temizle
                                parent = existing_path.parent
                                if parent != RAW_PATH and parent.exists() and not any(parent.iterdir()):
                                    parent.rmdir()
                                    # Banka klasörü de boşsa onu da sil
                                    bank_parent = parent.parent
                                    if bank_parent != RAW_PATH and bank_parent.exists() and not any(bank_parent.iterdir()):
                                        bank_parent.rmdir()
                                
                                st.success("✅ Mevcut dosya silindi.")
                                clear_all_data_caches()
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Silme hatası: {e}")
                    
                    if skip_duplicate:
                        st.info("ℹ️ Bu dosya atlanacak.")
                        continue
                
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    with st.spinner("Dosya analiz ediliyor..."):
                        analysis = analyze_uploaded_file(file_content, uploaded_file.name)
                    
                    if not analysis.get("success"):
                        st.error(f"❌ Hata: {analysis.get('error')}")
                        continue
                    
                    # Display analysis results
                    bank_name = analysis.get("bank_name", "Bilinmiyor")
                    st.markdown(f"**Banka:** {bank_name}")
                    st.markdown(f"**Satır Sayısı:** {analysis['row_count']:,}")
                    st.markdown(f"**Filtrelenmiş:** {analysis['filtered_count']:,} işlem")
                    
                    # Control summary
                    control = analysis.get("control_summary", {})
                    if control:
                        match_pct = control.get("match_percentage", 0)
                        if match_pct == 100:
                            st.success(f"✅ Komisyon kontrolü: {control.get('status', 'OK')}")
                        else:
                            st.warning(f"⚠️ {control.get('status', 'Fark var')}")
                
                with col2:
                    # Totals
                    totals = analysis.get("totals", {})
                    if totals:
                        gross = totals.get('total_gross', 0)
                        commission = totals.get('total_commission', 0)
                        net = gross - commission
                        st.metric("Brüt Tutar", tl(gross))
                        st.metric("Komisyon", tl(commission))
                        st.metric("Net", tl(net))
                
                # Tarih ve Kaydetme Seçenekleri
                st.markdown("---")
                st.markdown("**📅 Dosya Bilgileri**")
                
                raw_bank_name = analysis.get("bank_name", "Bilinmiyor")
                normalized_bank = normalize_bank_name(raw_bank_name)
                bank_recognized = normalized_bank is not None
                
                col_bank, col_date = st.columns(2)
                with col_bank:
                    # Eğer banka tanındıysa, doğru index'i bul
                    if bank_recognized and normalized_bank in BANK_OPTIONS:
                        default_index = BANK_OPTIONS.index(normalized_bank)
                    else:
                        default_index = 0
                    
                    selected_bank = st.selectbox(
                        "Banka",
                        options=BANK_OPTIONS,
                        index=default_index,
                        key=f"bank_{uploaded_file.name}",
                        disabled=bank_recognized,  # Tanındıysa değiştirmeye gerek yok
                        help=f"Otomatik tanınan: {raw_bank_name}" if bank_recognized else "Banka seçin"
                    )
                
                with col_date:
                    selected_date = st.date_input(
                        "Ekstre Dönemi",
                        value=datetime.now(),
                        key=f"date_{uploaded_file.name}",
                        help="Ekstre ayı (dosya bu aya kaydedilir)"
                    )
                
                # Kaydet butonu
                # Eğer banka tanındıysa yeşil başarı mesajı göster
                if bank_recognized:
                    st.success(f"✅ Banka otomatik tanındı: **{normalized_bank}**")
                
                col1, col2, col3 = st.columns([1, 1, 2])
                
                with col1:
                    save_label = "💾 Kaydet" if not bank_recognized else "💾 Onayla ve Kaydet"
                    if st.button(save_label, key=f"save_{uploaded_file.name}", type="primary" if bank_recognized else "secondary"):
                        # Dosya hash'ini kaydet (duplike kontrolünde atlanması için)
                        file_hash = calculate_file_hash(file_content)
                        mark_file_as_saved(file_hash)
                        
                        # Organize kaydet: BANKA/YYYY-MM/dosya.xlsx
                        file_datetime = datetime.combine(selected_date, datetime.min.time())
                        saved_path = save_to_raw_organized(
                            file_content, 
                            uploaded_file.name, 
                            selected_bank,
                            file_datetime
                        )
                        st.success(f"✅ Kaydedildi: {selected_bank}/{selected_date.strftime('%Y-%m')}/{saved_path.name}")
                        
                        # Azure backup (otomatik)
                        if is_azure_configured():
                            if upload_file_to_azure(saved_path):
                                st.info("☁️ Azure'a yedeklendi")
                        
                        # Clear ALL data caches - data resets on new import
                        clear_all_data_caches()
                        invalidate_data()
                        
                        # File uploader'ı sıfırla (aynı dosyayı tekrar göstermesin)
                        reset_uploader()
                        
                        st.info("🔄 Dosya kaydedildi. Sayfa yenileniyor...")
                        st.rerun()
                
                with col2:
                    if st.button(f"👁️ Önizle", key=f"preview_{uploaded_file.name}"):
                        st.session_state[f"show_preview_{uploaded_file.name}"] = True
                
                # Preview data
                if st.session_state.get(f"show_preview_{uploaded_file.name}"):
                    df = analysis.get("df")
                    if df is not None:
                        st.markdown("**Veri Önizleme (ilk 20 satır):**")
                        display_cols = ["transaction_date", "gross_amount", "commission_amount", 
                                       "net_amount", "installment_count", "commission_rate",
                                       "rate_expected", "rate_match"]
                        display_cols = [c for c in display_cols if c in df.columns]
                        st.dataframe(df[display_cols].head(20), width="stretch")


def render_existing_files():
    """Show files already in data/raw/ organized by bank and month."""
    st.header("📂 Dosya Yönetimi")
    
    if not RAW_PATH.exists():
        st.info("📁 Henüz dosya yüklenmedi")
        return
    
    # Tüm dosyaları topla (hem düz hem organize yapı)
    all_files = []
    
    # Düz yapıdaki dosyalar
    for f in RAW_PATH.glob("*"):
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in [".csv", ".xlsx", ".xls"]:
            all_files.append({
                "path": f,
                "bank": detect_bank_from_filename(f.name) or "Diğer",
                "month": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m"),
                "name": f.name,
                "size": f.stat().st_size,
                "mtime": datetime.fromtimestamp(f.stat().st_mtime)
            })
    
    # Organize yapıdaki dosyalar (BANKA/YYYY-MM/dosya.xlsx)
    for bank_dir in RAW_PATH.iterdir():
        if bank_dir.is_dir() and not bank_dir.name.startswith("."):
            for month_dir in bank_dir.iterdir():
                if month_dir.is_dir():
                    for f in month_dir.glob("*"):
                        if f.is_file() and f.suffix.lower() in [".csv", ".xlsx", ".xls"]:
                            all_files.append({
                                "path": f,
                                "bank": bank_dir.name.replace("_", " ").title(),
                                "month": month_dir.name,
                                "name": f.name,
                                "size": f.stat().st_size,
                                "mtime": datetime.fromtimestamp(f.stat().st_mtime)
                            })
    
    if not all_files:
        st.info("📁 Henüz dosya yüklenmedi")
        return
    
    # Özet istatistikler
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📄 Toplam Dosya", len(all_files))
    with col2:
        unique_banks = len(set(f["bank"] for f in all_files))
        st.metric("🏦 Banka", unique_banks)
    with col3:
        unique_months = len(set(f["month"] for f in all_files))
        st.metric("📅 Ay", unique_months)
    
    st.markdown("---")
    
    # Görünüm seçimi
    view_mode = st.radio(
        "Görünüm",
        ["🏦 Banka Bazlı", "📅 Ay Bazlı", "📋 Liste"],
        horizontal=True,
        key="file_view_mode"
    )
    
    if view_mode == "🏦 Banka Bazlı":
        # Bankaya göre grupla
        banks = {}
        for f in all_files:
            bank = f["bank"]
            if bank not in banks:
                banks[bank] = []
            banks[bank].append(f)
        
        for bank, files in sorted(banks.items()):
            with st.expander(f"🏦 {bank} ({len(files)} dosya)", expanded=False):
                for f in sorted(files, key=lambda x: x["month"], reverse=True):
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    with col1:
                        st.markdown(f"📄 {f['name']}")
                    with col2:
                        st.markdown(f"📅 {f['month']}")
                    with col3:
                        st.markdown(f"{f['size']/1024:.1f} KB")
                    with col4:
                        if st.button("🗑️", key=f"del_{f['path']}", help="Sil"):
                            f['path'].unlink()
                            clear_all_data_caches()
                            invalidate_data()
                            st.rerun()
    
    elif view_mode == "📅 Ay Bazlı":
        # Aya göre grupla
        months = {}
        for f in all_files:
            month = f["month"]
            if month not in months:
                months[month] = []
            months[month].append(f)
        
        for month, files in sorted(months.items(), reverse=True):
            with st.expander(f"📅 {month} ({len(files)} dosya)", expanded=False):
                for f in sorted(files, key=lambda x: x["bank"]):
                    col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
                    with col1:
                        st.markdown(f"📄 {f['name']}")
                    with col2:
                        st.markdown(f"🏦 {f['bank']}")
                    with col3:
                        st.markdown(f"{f['size']/1024:.1f} KB")
                    with col4:
                        if st.button("🗑️", key=f"del_{f['path']}", help="Sil"):
                            f['path'].unlink()
                            clear_all_data_caches()
                            invalidate_data()
                            st.rerun()
    
    else:  # Liste görünümü
        # Toplu silme
        col_info, col_clear = st.columns([3, 1])
        with col_info:
            st.markdown(f"**{len(all_files)} dosya mevcut**")
        with col_clear:
            if st.button("🗑️ Tümünü Sil", type="secondary"):
                for f in all_files:
                    try:
                        f['path'].unlink()
                    except Exception:
                        pass
                clear_all_data_caches()
                invalidate_data()
                st.success("Tüm dosyalar silindi!")
                st.rerun()
        
        st.markdown("---")
        
        for f in sorted(all_files, key=lambda x: x["mtime"], reverse=True):
            col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 0.5])
            with col1:
                st.markdown(f"📄 **{f['name']}**")
            with col2:
                st.markdown(f"🏦 {f['bank']}")
            with col3:
                st.markdown(f"📅 {f['month']}")
            with col4:
                st.markdown(f"{f['size']/1024:.1f} KB")
            with col5:
                if st.button("🗑️", key=f"del_list_{f['path']}"):
                    f['path'].unlink()
                    clear_all_data_caches()
                    invalidate_data()
                    st.rerun()
                invalidate_data()
                st.rerun()


# Page config
st.set_page_config(
    page_title="Dosya Yükle - Nakit Akış Paneli",
    page_icon="📤",
    layout="wide"
)

# Require authentication
if not check_password():
    st.stop()

st.title("📤 Dosya Yükle")
st.markdown("Banka ekstre dosyalarını yükleyin ve analiz edin.")
st.markdown("---")

# Azure Backup/Restore Section
if is_azure_configured():
    with st.sidebar:
        st.subheader("☁️ Azure Backup")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📤 Backup", help="Tüm dosyaları Azure'a yedekle"):
                with st.spinner("Yedekleniyor..."):
                    result = backup_all_raw_files()
                if result.get("success"):
                    st.success(f"✅ {len(result['success'])} dosya yedeklendi")
                if result.get("failed"):
                    st.warning(f"⚠️ {len(result['failed'])} dosya başarısız")
        
        with col2:
            if st.button("📥 Restore", help="Azure'dan dosyaları geri yükle"):
                with st.spinner("Geri yükleniyor..."):
                    result = restore_from_azure()
                if result.get("restored"):
                    st.success(f"✅ {len(result['restored'])} dosya yüklendi")
                    clear_all_data_caches()
                    invalidate_data()
                    st.rerun()
                elif result.get("error"):
                    st.error(result["error"])
else:
    with st.sidebar:
        st.info("☁️ Azure Backup yapılandırılmamış")

# Initialize managers
init_managers()

# Tabs
tab1, tab2 = st.tabs(["📤 Yeni Yükle", "📂 Mevcut Dosyalar"])

with tab1:
    render_upload_section()

with tab2:
    render_existing_files()
