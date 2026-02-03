"""
📤 Dosya Yükle

Banka CSV/Excel dosyalarını yükleyin, analiz edin ve komisyon kontrolü yapın.
"""

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
from storage.metadata import MetadataManager, FileMetadata
from storage.cache import FileCache

# Data paths
RAW_PATH = PROJECT_ROOT.parent / "data" / "raw"
logger = logging.getLogger(__name__)


def init_managers():
    """Initialize storage managers."""
    if "metadata_manager" not in st.session_state:
        st.session_state.metadata_manager = MetadataManager()
    if "file_cache" not in st.session_state:
        st.session_state.file_cache = FileCache()
    if "bank_reader" not in st.session_state:
        st.session_state.bank_reader = BankFileReader()
    return st.session_state.metadata_manager, st.session_state.file_cache


def detect_bank_from_filename(filename: str) -> str:
    """Detect bank name from filename."""
    bank_patterns = {
        "vakıf": "Vakıfbank",
        "vakif": "Vakıfbank", 
        "akbank": "Akbank",
        "garanti": "Garanti",
        "halkbank": "Halkbank",
        "halk": "Halkbank",
        "ziraat": "Ziraat",
        "ykb": "YKB",
        "yapı kredi": "YKB",
        "yapıkredi": "YKB",
        "iş bankası": "İşbankası",
        "isbank": "İşbankası",
        "işbank": "İşbankası",
        "qnb": "QNB",
        "finans": "QNB",
    }
    
    filename_lower = filename.lower()
    for pattern, bank_name in bank_patterns.items():
        if pattern in filename_lower:
            return bank_name
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


def save_to_raw(file_content: bytes, filename: str) -> Path:
    """Save uploaded file to data/raw/ directory."""
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
    st.header("📤 Dosya Yükle")
    
    st.markdown("""
    ### 🏦 Banka Ekstreleri Yükleme
    
    CSV veya Excel dosyalarınızı sürükleyip bırakın veya seçin.
    Desteklenen bankalar: **Vakıfbank, Akbank, Garanti, Halkbank, Ziraat, YKB, QNB, İşbankası**
    
    ---
    """)
    
    # File uploader with drag-and-drop
    uploaded_files = st.file_uploader(
        "📁 Dosya Seçin",
        type=["xlsx", "xls", "csv"],
        accept_multiple_files=True,
        key="file_uploader",
        help="CSV veya Excel formatında banka ekstre dosyaları"
    )
    
    if uploaded_files:
        st.markdown("---")
        st.subheader("📊 Yüklenen Dosyalar")
        
        for uploaded_file in uploaded_files:
            file_content = uploaded_file.read()
            
            with st.expander(f"📄 {uploaded_file.name}", expanded=True):
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
                        st.metric("Brüt Tutar", f"₺{totals.get('total_gross', 0):,.2f}")
                        st.metric("Komisyon", f"₺{totals.get('total_commission', 0):,.2f}")
                        st.metric("Net", f"₺{totals.get('total_net', 0):,.2f}")
                
                # Save button
                col1, col2, col3 = st.columns([1, 1, 2])
                with col1:
                    if st.button(f"💾 Kaydet", key=f"save_{uploaded_file.name}"):
                        saved_path = save_to_raw(file_content, uploaded_file.name)
                        st.success(f"✅ Kaydedildi: {saved_path.name}")
                        st.cache_data.clear()  # Clear cache to reload data
                
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
                        st.dataframe(df[display_cols].head(20), use_container_width=True)


def render_existing_files():
    """Show files already in data/raw/."""
    st.header("📂 Mevcut Dosyalar")
    
    if not RAW_PATH.exists():
        st.info("📁 Henüz dosya yüklenmedi")
        return
    
    files = list(RAW_PATH.glob("*.csv")) + list(RAW_PATH.glob("*.xlsx")) + list(RAW_PATH.glob("*.xls"))
    files = [f for f in files if not f.name.startswith(".")]
    
    if not files:
        st.info("📁 Henüz dosya yüklenmedi")
        return
    
    st.markdown(f"**{len(files)} dosya mevcut:**")
    
    for f in sorted(files, key=lambda x: x.stat().st_mtime, reverse=True):
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            bank = detect_bank_from_filename(f.name) or "?"
            st.markdown(f"📄 **{f.name}** ({bank})")
        
        with col2:
            size_kb = f.stat().st_size / 1024
            st.markdown(f"{size_kb:.1f} KB")
        
        with col3:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            st.markdown(mtime.strftime("%d/%m/%Y"))
        
        with col4:
            if st.button("🗑️", key=f"delete_{f.name}", help="Dosyayı sil"):
                f.unlink()
                st.success(f"Silindi: {f.name}")
                st.cache_data.clear()
                st.rerun()


# Page config
st.set_page_config(
    page_title="Dosya Yükle - Nakit Akış Paneli",
    page_icon="📤",
    layout="wide"
)

st.title("📤 Dosya Yükle")
st.markdown("Banka ekstre dosyalarını yükleyin ve analiz edin.")
st.markdown("---")

# Initialize managers
init_managers()

# Tabs
tab1, tab2 = st.tabs(["📤 Yeni Yükle", "📂 Mevcut Dosyalar"])

with tab1:
    render_upload_section()

with tab2:
    render_existing_files()
