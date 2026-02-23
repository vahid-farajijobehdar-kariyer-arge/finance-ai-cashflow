"""
Banka Detay Sayfası Temel Şablonu

Tüm banka detay sayfaları bu şablonu kullanır.
DRY prensibi: Ortak kod tek yerde.

© 2026 Kariyer.net Finans Ekibi
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from io import BytesIO
from datetime import datetime
import sys
import yaml

# Proje yolunu ekle
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.reader import BankFileReader
from src.processing.commission_control import add_commission_control
from src.processing.calculator import filter_successful_transactions
from calendar import monthrange

# Dashboard yolunu ekle
sys.path.insert(0, str(Path(__file__).parent.parent))
from format_utils import _tl


# Sabitler
RAW_PATH = PROJECT_ROOT / "data" / "raw"
CONFIG_PATH = PROJECT_ROOT / "config" / "commission_rates.yaml"

# YAML bank key → base.py bank key eşleştirmesi
YAML_KEY_MAP = {
    "akbank": "akbank",
    "garanti": "garanti",
    "halkbank": "halkbank",
    "isbank": "isbank",
    "qnb": "qnb",
    "vakifbank": "vakifbank",
    "yapikredi": "ykb",
    "ziraat": "ziraat",
}
# Tersini de oluştur: base key → yaml key
BASE_TO_YAML_KEY = {v: k for k, v in YAML_KEY_MAP.items()}


def load_yaml_rates(bank_key: str) -> dict:
    """YAML'dan belirli banka için sözleşme oranlarını yükle.
    
    Returns:
        dict: {installment_count: rate} — örn. {1: 0.0360, 2: 0.0586, ...}
    """
    yaml_key = BASE_TO_YAML_KEY.get(bank_key, bank_key)
    
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
    except Exception:
        return {}
    
    bank_data = config.get("banks", {}).get(yaml_key, {})
    return bank_data.get("rates", {})


# Banka tanımları
BANK_DEFINITIONS = {
    "akbank": {
        "name": "Akbank",
        "display_name": "AKBANK T.A.Ş.",
        "icon": "🏦",
        "color": "#E30613",
        "patterns": ["akbank", "AKBANK"]
    },
    "garanti": {
        "name": "Garanti BBVA",
        "display_name": "T. GARANTİ BANKASI A.Ş.",
        "icon": "🏦",
        "color": "#00A651",
        "patterns": ["garanti", "GARANTI", "GARANTİ"]
    },
    "halkbank": {
        "name": "Halkbank",
        "display_name": "TÜRKİYE HALK BANKASI A.Ş.",
        "icon": "🏦",
        "color": "#0066B3",
        "patterns": ["halkbank", "HALKBANK", "halk"]
    },
    "isbank": {
        "name": "İşbank",
        "display_name": "TÜRKİYE İŞ BANKASI A.Ş.",
        "icon": "🏦",
        "color": "#003366",
        "patterns": ["isbank", "ISBANK", "İŞBANK", "işbank"]
    },
    "qnb": {
        "name": "QNB Finansbank",
        "display_name": "QNB FİNANSBANK A.Ş.",
        "icon": "🏦",
        "color": "#7B2D8E",
        "patterns": ["qnb", "QNB", "finansbank", "FINANSBANK"]
    },
    "vakifbank": {
        "name": "Vakıfbank",
        "display_name": "T. VAKIFLAR BANKASI T.A.O.",
        "icon": "🏦",
        "color": "#FFCC00",
        "patterns": ["vakif", "VAKIF", "vakıf", "VAKIFBANK"]
    },
    "ykb": {
        "name": "Yapı Kredi",
        "display_name": "YAPI VE KREDİ BANKASI A.Ş.",
        "icon": "🏦",
        "color": "#0033A0",
        "patterns": ["ykb", "YKB", "yapikredi", "yapıkredi", "YAPI"]
    },
    "ziraat": {
        "name": "Ziraat Bankası",
        "display_name": "T.C. ZİRAAT BANKASI A.Ş.",
        "icon": "🏦",
        "color": "#009639",
        "patterns": ["ziraat", "ZIRAAT", "ZİRAAT"]
    }
}


def format_currency(value: float) -> str:
    """Türk Lirası formatı - okunabilir K/M kısaltmalı."""
    if pd.isna(value):
        return "-"
    is_negative = value < 0
    abs_val = abs(value)
    if abs_val >= 1_000_000:
        formatted = f"{abs_val/1_000_000:.2f}".replace(".", ",") + "M"
    elif abs_val >= 10_000:
        formatted = f"{abs_val/1_000:.1f}".replace(".", ",") + "K"
    else:
        formatted = f"{abs_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    if is_negative:
        formatted = "-" + formatted
    return f"₺{formatted}"


def format_currency_full(value: float) -> str:
    """Türk Lirası tam format (kısaltmasız)."""
    if pd.isna(value):
        return "-"
    return f"₺{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value: float) -> str:
    """Yüzde formatı."""
    if pd.isna(value):
        return "-"
    return f"%{value*100:.2f}".replace(".", ",")


def load_all_data() -> pd.DataFrame:
    """Tüm banka verilerini yükle."""
    if not RAW_PATH.exists():
        return pd.DataFrame()
    
    reader = BankFileReader()
    
    try:
        df = reader.read_all_files(RAW_PATH)
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        return pd.DataFrame()
    
    if df is None or df.empty:
        return pd.DataFrame()
    
    # Temizle ve işle
    df = df.reset_index(drop=True)
    df = df.loc[:, ~df.columns.duplicated()]
    df = filter_successful_transactions(df)
    df = add_commission_control(df)
    
    return df


def filter_bank_data(df: pd.DataFrame, bank_key: str) -> pd.DataFrame:
    """Belirtilen banka verilerini filtrele."""
    if df.empty:
        return pd.DataFrame()
    
    bank_def = BANK_DEFINITIONS.get(bank_key, {})
    patterns = bank_def.get("patterns", [bank_key])
    
    # bank_name veya _source_bank sütununda ara
    mask = pd.Series([False] * len(df))
    
    for col in ["bank_name", "_source_bank"]:
        if col in df.columns:
            for pattern in patterns:
                mask = mask | df[col].astype(str).str.contains(pattern, case=False, na=False)
    
    return df[mask].copy()


def filter_by_month(df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    """Valor (settlement_date) tarihine göre sadece seçilen ayı filtrele.
    
    Excel dosyasında önceki veya sonraki aya ait satırlar olsa bile
    bunları hariç tutar — yalnızca seçilen aydaki işlemleri döner.
    
    Öncelik: settlement_date > transaction_date
    """
    if df.empty:
        return df
    
    # Hangi tarih sütunu kullanılacak
    date_col = None
    for col in ["settlement_date", "transaction_date"]:
        if col in df.columns:
            date_col = col
            break
    
    if date_col is None:
        return df
    
    dates = pd.to_datetime(df[date_col], errors="coerce")
    first_day = pd.Timestamp(year, month, 1)
    last_day = pd.Timestamp(year, month, monthrange(year, month)[1], 23, 59, 59)
    
    mask = (dates >= first_day) & (dates <= last_day)
    return df[mask].copy()


class BankDetailPage:
    """Banka detay sayfası şablonu."""
    
    def __init__(self, bank_key: str):
        self.bank_key = bank_key
        self.bank_def = BANK_DEFINITIONS.get(bank_key, {})
        self.name = self.bank_def.get("name", bank_key.title())
        self.display_name = self.bank_def.get("display_name", self.name)
        self.icon = self.bank_def.get("icon", "🏦")
        self.color = self.bank_def.get("color", "#1f77b4")
    
    def render(self):
        """Ana sayfa render."""
        # Sayfa başlığı
        st.title(f"{self.icon} {self.name} Detay")
        st.markdown(f"**{self.display_name}** için detaylı komisyon analizi")
        st.markdown("---")
        
        # Veri yükle
        all_df = load_all_data()
        
        if all_df.empty:
            self._render_no_data()
            return
        
        # Banka verilerini filtrele
        df = filter_bank_data(all_df, self.bank_key)
        
        if df.empty:
            self._render_no_bank_data()
            return
        
        # ── Ay Seçici (valor / settlement_date bazlı) ──
        now = datetime.now()
        selected_month = self._render_month_selector(df, now)
        selected_year = selected_month.year
        selected_mon = selected_month.month
        
        # Sadece seçilen aya ait satırları tut
        df = filter_by_month(df, selected_year, selected_mon)
        
        if df.empty:
            st.warning(f"⚠️ {self.name} için {selected_month.strftime('%B %Y')} ayında veri bulunamadı.")
            return
        
        # Sayfa bölümleri
        self._render_detail_table(df)
        self._render_summary_metrics(df)
        self._render_pesin_taksitli(df)
        self._render_commission_diff_analysis(df)
        self._render_monthly_trend(df)
        self._render_installment_distribution(df)
        self._render_export(df)
        
        # Footer
        st.markdown("---")
        st.caption("© 2026 Kariyer.net Finans Ekibi")
    
    def _render_month_selector(self, df: pd.DataFrame, now: datetime) -> datetime:
        """Ay seçici widget — varsayılan olarak Excel verisindeki son ay."""
        # Mevcut ayları keşfet (settlement_date > transaction_date)
        date_col = None
        for col in ["settlement_date", "transaction_date"]:
            if col in df.columns:
                date_col = col
                break
        
        available_months = []
        if date_col:
            dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
            if len(dates) > 0:
                available_months = sorted(dates.dt.to_period("M").unique())
        
        if available_months:
            month_labels = [str(m) for m in available_months]
            # Her zaman Excel verisindeki son ayı varsayılan seç
            default_idx = len(month_labels) - 1
            
            selected_label = st.selectbox(
                "📅 Ay Seçimi (Valor / Hesaba Geçiş Tarihine Göre)",
                options=month_labels,
                index=default_idx,
                help="Sadece seçilen aydaki işlemler gösterilir. "
                     "Excel dosyasında önceki/sonraki aya ait satırlar otomatik olarak hariç tutulur."
            )
            period = pd.Period(selected_label, freq="M")
            return datetime(period.year, period.month, 1)
        else:
            return datetime(now.year, now.month, 1)
    
    def _render_no_data(self):
        """Veri yok mesajı."""
        st.warning("""
        ⚠️ **Veri Bulunamadı**
        
        Henüz yüklenmiş dosya yok.
        
        1. **📤 Dosya Yükle** sayfasına gidin
        2. Banka ekstre dosyalarını yükleyin
        3. Bu sayfaya geri dönün
        """)
    
    def _render_no_bank_data(self):
        """Banka verisi yok mesajı."""
        st.info(f"""
        ℹ️ **{self.name} Verisi Bulunamadı**
        
        {self.name} için yüklenmiş dosya yok.
        
        Dosya yüklediyseniz, dosya adının banka adını içerdiğinden emin olun.
        """)
    
    def _render_summary_metrics(self, df: pd.DataFrame):
        """Özet metrikler."""
        st.subheader("📊 Özet Metrikler")
        
        # Grand total: tüm değerler dahil (pozitif + negatif)
        total_gross = df["gross_amount"].sum() if "gross_amount" in df.columns else 0
        total_commission = df["commission_amount"].sum() if "commission_amount" in df.columns else 0
        total_net = total_gross - total_commission
        avg_rate = (total_commission / total_gross * 100) if total_gross != 0 else 0
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📊 İşlem Sayısı", f"{len(df):,}")
        c2.metric("💵 Brüt Tutar", format_currency(total_gross))
        c3.metric("💳 Komisyon", format_currency(total_commission))
        c4.metric("💰 Net Tutar", format_currency(total_net))
        c5.metric("📈 Ort. Oran", f"%{avg_rate:.2f}")
        
        # NET formül açıklaması
        st.caption(
            f"NET = Brüt ({format_currency_full(total_gross)}) "
            f"- Komisyon ({format_currency_full(total_commission)}) "
            f"= **{format_currency_full(total_net)}**"
        )
        
        # Ek kesintiler varsa ayrıca göster
        reward_total = df["reward_deduction"].sum() if "reward_deduction" in df.columns else 0
        service_total = df["service_deduction"].sum() if "service_deduction" in df.columns else 0
        if abs(reward_total) > 0 or abs(service_total) > 0:
            st.caption(
                f"ℹ️ Ek Kesintiler (NET'e dahil değil): "
                f"Ödül Kes. ({format_currency_full(reward_total)}), "
                f"Servis Kes. ({format_currency_full(service_total)})"
            )
        
        # ── Garanti: Ödül/Servis Kesintisi ve Kategori Dağılımı ──
        has_deductions = (
            ("reward_deduction" in df.columns and df["reward_deduction"].abs().sum() > 0) or
            ("service_deduction" in df.columns and df["service_deduction"].abs().sum() > 0)
        )
        has_categories = "transaction_category" in df.columns and df["transaction_category"].nunique() > 1
        
        if has_deductions or has_categories:
            st.markdown("#### 📂 İşlem Kategori Dağılımı")
            
            if has_categories:
                cat_rows = []
                for cat, grp in df.groupby("transaction_category", sort=False):
                    g = grp["gross_amount"].sum() if "gross_amount" in grp.columns else 0
                    comm = grp["commission_amount"].sum() if "commission_amount" in grp.columns else 0
                    n = g - comm
                    reward = grp["reward_deduction"].sum() if "reward_deduction" in grp.columns else 0
                    service = grp["service_deduction"].sum() if "service_deduction" in grp.columns else 0
                    cat_rows.append({
                        "Kategori": cat,
                        "İşlem Sayısı": len(grp),
                        "Brüt (₺)": g,
                        "Komisyon (₺)": comm,
                        "Ödül Kesintisi (₺)": reward,
                        "Servis Kesintisi (₺)": service,
                        "Net (₺)": n,
                    })
                cat_df = pd.DataFrame(cat_rows)
                
                # Format
                fmt = {
                    "İşlem Sayısı": "{:,}",
                    "Brüt (₺)": _tl,
                    "Komisyon (₺)": _tl,
                    "Ödül Kesintisi (₺)": _tl,
                    "Servis Kesintisi (₺)": _tl,
                    "Net (₺)": _tl,
                }
                # Ödül/Servis sıfırsa sütunu kaldır
                if cat_df["Ödül Kesintisi (₺)"].abs().sum() == 0:
                    cat_df = cat_df.drop(columns=["Ödül Kesintisi (₺)"])
                    fmt.pop("Ödül Kesintisi (₺)", None)
                if cat_df["Servis Kesintisi (₺)"].abs().sum() == 0:
                    cat_df = cat_df.drop(columns=["Servis Kesintisi (₺)"])
                    fmt.pop("Servis Kesintisi (₺)", None)
                
                st.dataframe(
                    cat_df.style.format(fmt),
                    use_container_width=True,
                    hide_index=True
                )
            
            # Özet: Toplam kesintiler
            if has_deductions:
                d1, d2, d3 = st.columns(3)
                reward_total = df["reward_deduction"].sum() if "reward_deduction" in df.columns else 0
                service_total = df["service_deduction"].sum() if "service_deduction" in df.columns else 0
                net_deduction = reward_total + service_total
                d1.metric("🏷️ Ödül Kesintisi", format_currency(reward_total))
                d2.metric("🔧 Servis Kesintisi", format_currency(service_total))
                d3.metric("📊 Toplam Ek Kesinti", format_currency(net_deduction))
    
    def _render_pesin_taksitli(self, df: pd.DataFrame):
        """Peşin vs Taksitli karşılaştırma — sadece POS işlemleri."""
        st.markdown("---")
        st.subheader("💵 Peşin vs Taksitli")
        
        # Sadece POS işlemlerini kullan (PNLT/PUCRT hariç)
        pos_df = df[df["transaction_category"] == "POS İşlemi"].copy() if "transaction_category" in df.columns else df.copy()
        
        # Taksit sayısına göre ayır
        inst_col = "installment_count" if "installment_count" in pos_df.columns else None
        
        if inst_col is None:
            st.info("Taksit bilgisi bulunamadı.")
            return
        
        pesin_mask = pos_df[inst_col].isin([0, 1, "0", "1", "Peşin", "peşin", "PESIN", "TEK"])
        pesin_df = pos_df[pesin_mask]
        taksitli_df = pos_df[~pesin_mask]
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💵 Tek Çekim / Peşin")
            if len(pesin_df) > 0:
                p_gross = pesin_df["gross_amount"].sum()
                p_comm = pesin_df["commission_amount"].sum()
                p_net = p_gross - p_comm
                p_rate = (p_comm / p_gross * 100) if p_gross > 0 else 0
                
                st.metric("İşlem Sayısı", f"{len(pesin_df):,}")
                st.metric("Brüt Tutar", format_currency(p_gross))
                st.metric("Komisyon", format_currency(p_comm))
                st.metric("Net Tutar", format_currency(p_net))
                st.metric("Ortalama Oran", f"%{p_rate:.2f}")
            else:
                st.info("Tek çekim işlemi yok.")
        
        with col2:
            st.markdown("#### 💳 Taksitli")
            if len(taksitli_df) > 0:
                t_gross = taksitli_df["gross_amount"].sum()
                t_comm = taksitli_df["commission_amount"].sum()
                t_net = t_gross - t_comm
                t_rate = (t_comm / t_gross * 100) if t_gross > 0 else 0
                
                st.metric("İşlem Sayısı", f"{len(taksitli_df):,}")
                st.metric("Brüt Tutar", format_currency(t_gross))
                st.metric("Komisyon", format_currency(t_comm))
                st.metric("Net Tutar", format_currency(t_net))
                st.metric("Ortalama Oran", f"%{t_rate:.2f}")
            else:
                st.info("Taksitli işlem yok.")
        
        # ── Kart Tipi Bazında Oran Dağılımı ──
        if "card_type" in pos_df.columns and pos_df["card_type"].nunique() > 1:
            st.markdown("#### 🃏 Kart Tipi Bazında Oran Dağılımı")
            card_rows = []
            for ct, grp in pos_df.groupby("card_type", sort=False):
                g = grp["gross_amount"].sum()
                c = grp["commission_amount"].sum()
                n_total = g - c
                r = (c / g * 100) if g != 0 else 0
                is_pesin = grp["installment_count"].isin([0, 1]).all()
                card_rows.append({
                    "Kart Tipi": ct,
                    "İşlem Sayısı": len(grp),
                    "Brüt (₺)": g,
                    "Komisyon (₺)": c,
                    "Net (₺)": n_total,
                    "Efektif Oran %": round(r, 4),
                    "Tür": "Peşin" if is_pesin else "Peşin+Taksitli",
                })
            card_df = pd.DataFrame(card_rows)
            st.dataframe(
                card_df.style.format({
                    "İşlem Sayısı": "{:,}",
                    "Brüt (₺)": _tl,
                    "Komisyon (₺)": _tl,
                    "Net (₺)": _tl,
                    "Efektif Oran %": "{:.4f}%",
                }),
                use_container_width=True,
                hide_index=True
            )
    
    def _render_commission_diff_analysis(self, df: pd.DataFrame):
        """Sözleşme vs Uygulanan oran karşılaştırması — sadece POS işlemleri."""
        st.markdown("---")
        st.subheader("📋 Sözleşme vs Uygulanan Oranlar")
        
        # YAML'dan sözleşme oranlarını yükle
        yaml_rates = load_yaml_rates(self.bank_key)
        
        if not yaml_rates:
            st.warning(f"{self.name} için sözleşme oranları tanımlanmamış (commission_rates.yaml).")
            return
        
        # Sadece POS işlemlerini kullan (PNLT/PUCRT hariç)
        pos_df = df[df["transaction_category"] == "POS İşlemi"].copy() if "transaction_category" in df.columns else df.copy()
        
        inst_col = "installment_count"
        has_data = inst_col in pos_df.columns
        has_control = "rate_match" in df.columns and "commission_diff" in df.columns
        
        # ────── ORAN KARŞILAŞTIRMA TABLOSU ──────
        rows = []
        all_installments = sorted(set(list(yaml_rates.keys()) + 
                                      ([int(x) for x in pos_df[inst_col].dropna().unique()] if has_data else [])))
        
        for inst in all_installments:
            inst_int = int(inst)
            offered_rate = yaml_rates.get(inst_int, None)
            
            # Gerçek veriden taksit filtrele
            if has_data:
                inst_df = pos_df[pos_df[inst_col] == inst_int]
            else:
                inst_df = pd.DataFrame()
            
            txn_count = len(inst_df)
            # Grand total: tüm işlemler (pozitif + negatif) dahil
            gross = inst_df["gross_amount"].sum() if txn_count > 0 else 0
            actual_comm = inst_df["commission_amount"].sum() if txn_count > 0 else 0
            
            # Oran hesabı: sadece pozitif (satış) işlemlerden
            # Negatif (iade) dahil edilirse ortalama oran bozulur
            if txn_count > 0 and "gross_amount" in inst_df.columns:
                pos_inst = inst_df[inst_df["gross_amount"] > 0]
                pos_gross = pos_inst["gross_amount"].sum()
                pos_comm = pos_inst["commission_amount"].sum()
                actual_rate = (pos_comm / pos_gross) if pos_gross > 0 else None
            else:
                actual_rate = None
            
            expected_comm = gross * offered_rate if (offered_rate and gross != 0) else 0
            comm_diff = actual_comm - expected_comm if (offered_rate and txn_count > 0) else 0
            
            # Oran farkı
            if offered_rate and actual_rate is not None:
                rate_diff = actual_rate - offered_rate
                rate_diff_bps = rate_diff * 10000  # basis points
                if abs(rate_diff) < 0.005:
                    status = "✅ Uyumlu"
                elif rate_diff > 0:
                    status = "🔴 Fazla"
                else:
                    status = "🟢 Az"
            elif txn_count == 0:
                rate_diff = None
                rate_diff_bps = None
                status = "⚪ Veri Yok"
            else:
                rate_diff = None
                rate_diff_bps = None
                status = "⚠️ Oran Tanımsız"
            
            label = "Peşin" if inst_int in (0, 1) else f"{inst_int} Taksit"
            
            rows.append({
                "Taksit": label,
                "_sort": inst_int,
                "Sözleşme Oranı": offered_rate,
                "Uygulanan Oran": actual_rate,
                "Oran Farkı (bps)": rate_diff_bps,
                "İşlem Sayısı": txn_count,
                "Brüt Tutar (₺)": gross,
                "Beklenen Komisyon (₺)": expected_comm,
                "Gerçek Komisyon (₺)": actual_comm,
                "Komisyon Farkı (₺)": comm_diff,
                "Durum": status,
            })
        
        compare_df = pd.DataFrame(rows).sort_values("_sort").drop(columns=["_sort"])
        
        # ────── ÖZET METRİKLER ──────
        has_txn = compare_df["İşlem Sayısı"] > 0
        total_gross = compare_df.loc[has_txn, "Brüt Tutar (₺)"].sum()
        total_actual = compare_df.loc[has_txn, "Gerçek Komisyon (₺)"].sum()
        total_expected = compare_df.loc[has_txn, "Beklenen Komisyon (₺)"].sum()
        total_diff = compare_df.loc[has_txn, "Komisyon Farkı (₺)"].sum()
        match_count = (compare_df["Durum"] == "✅ Uyumlu").sum()
        mismatch_count = compare_df["Durum"].isin(["🔴 Fazla", "🟢 Az"]).sum()
        
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("Beklenen Komisyon", format_currency(total_expected))
        c2.metric("Gerçek Komisyon", format_currency(total_actual))
        c3.metric(
            "Toplam Fark",
            format_currency(total_diff),
            delta="Fazla kesim" if total_diff > 0 else ("Az kesim" if total_diff < 0 else "Tam eşleşme"),
            delta_color="inverse" if total_diff > 0 else "normal"
        )
        c4.metric("Uyumlu Taksit", f"{match_count}/{match_count + mismatch_count}")
        c5.metric(
            "Uyum Oranı",
            f"%{(match_count / max(match_count + mismatch_count, 1) * 100):.0f}",
            delta="✓" if mismatch_count == 0 else f"{mismatch_count} farklı",
            delta_color="off"
        )
        
        # ────── KARŞILAŞTIRMA TABLOSU ──────
        st.markdown("#### 📊 Taksit Bazında Sözleşme vs Uygulanan")
        
        format_dict = {
            "Sözleşme Oranı": "{:.4f}",
            "Uygulanan Oran": "{:.4f}",
            "Oran Farkı (bps)": "{:+.1f}",
            "İşlem Sayısı": "{:,}",
            "Brüt Tutar (₺)": _tl,
            "Beklenen Komisyon (₺)": _tl,
            "Gerçek Komisyon (₺)": _tl,
            "Komisyon Farkı (₺)": lambda x: _tl(x, signed=True),
        }
        
        def highlight_status(val):
            if "Fazla" in str(val):
                return "background-color: #f8d7da; color: #721c24"
            elif "Az" in str(val) and "Veri" not in str(val):
                return "background-color: #d4edda; color: #155724"
            elif "Uyumlu" in str(val):
                return "background-color: #d1ecf1; color: #0c5460"
            return ""
        
        styled = compare_df.style.format(format_dict, na_rep="-").applymap(
            highlight_status, subset=["Durum"]
        )
        st.dataframe(styled, use_container_width=True, hide_index=True)
        
        # ────── ORAN KARŞILAŞTIRMA GRAFİĞİ ──────
        chart_df = compare_df[compare_df["İşlem Sayısı"] > 0].copy()
        
        if len(chart_df) > 0:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=chart_df["Taksit"],
                y=chart_df["Sözleşme Oranı"].apply(lambda x: x * 100 if pd.notna(x) else 0),
                name="Sözleşme Oranı (%)",
                marker_color="#2196F3",
                text=chart_df["Sözleşme Oranı"].apply(lambda x: f"%{x*100:.2f}" if pd.notna(x) else "-"),
                textposition="outside",
            ))
            
            fig.add_trace(go.Bar(
                x=chart_df["Taksit"],
                y=chart_df["Uygulanan Oran"].apply(lambda x: x * 100 if pd.notna(x) else 0),
                name="Uygulanan Oran (%)",
                marker_color=self.color,
                text=chart_df["Uygulanan Oran"].apply(lambda x: f"%{x*100:.2f}" if pd.notna(x) else "-"),
                textposition="outside",
            ))
            
            fig.update_layout(
                title=f"{self.name} — Sözleşme vs Uygulanan Komisyon Oranı",
                barmode="group",
                yaxis_title="Oran (%)",
                xaxis_title="Taksit",
                legend=dict(x=0.01, y=0.99),
                hovermode="x unified"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Komisyon tutarı karşılaştırma grafiği
            fig2 = go.Figure()
            fig2.add_trace(go.Bar(
                x=chart_df["Taksit"],
                y=chart_df["Beklenen Komisyon (₺)"],
                name="Beklenen Komisyon (₺)",
                marker_color="#2196F3",
            ))
            fig2.add_trace(go.Bar(
                x=chart_df["Taksit"],
                y=chart_df["Gerçek Komisyon (₺)"],
                name="Gerçek Komisyon (₺)",
                marker_color=self.color,
            ))
            fig2.update_layout(
                title=f"{self.name} — Beklenen vs Gerçek Komisyon Tutarı",
                barmode="group",
                yaxis_title="Tutar (₺)",
                xaxis_title="Taksit",
                legend=dict(x=0.01, y=0.99),
                hovermode="x unified"
            )
            st.plotly_chart(fig2, use_container_width=True)
        
        # ────── FARK OLAN İŞLEMLER ──────
        if has_control:
            diff_count = (df["rate_match"] == False).sum()
            if diff_count > 0:
                with st.expander(f"📋 Tolerans Dışı İşlemler ({diff_count:,} adet)", expanded=False):
                    diff_df = df[df["rate_match"] == False].copy()
                    
                    display_cols = ["transaction_date", "installment_count", "gross_amount", 
                                  "commission_rate", "rate_expected", "rate_diff",
                                  "commission_amount", "commission_expected", "commission_diff"]
                    display_cols = [c for c in display_cols if c in diff_df.columns]
                    
                    col_labels = {
                        "transaction_date": "Tarih", "installment_count": "Taksit",
                        "gross_amount": "Brüt Tutar", "commission_rate": "Uygulanan Oran",
                        "rate_expected": "Sözleşme Oranı", "rate_diff": "Oran Farkı",
                        "commission_amount": "Gerçek Komisyon", "commission_expected": "Beklenen Komisyon",
                        "commission_diff": "Fark (₺)"
                    }
                    
                    st.dataframe(
                        diff_df[display_cols].head(200).rename(columns=col_labels).style.format({
                            "Brüt Tutar": _tl,
                            "Uygulanan Oran": "{:.4f}",
                            "Sözleşme Oranı": "{:.4f}",
                            "Oran Farkı": "{:.4f}",
                            "Gerçek Komisyon": _tl,
                            "Beklenen Komisyon": _tl,
                            "Fark (₺)": lambda x: _tl(x, signed=True)
                        }, na_rep="-"),
                        use_container_width=True,
                        hide_index=True
                    )
    
    def _render_monthly_trend(self, df: pd.DataFrame):
        """Aylık trend grafiği."""
        st.markdown("---")
        st.subheader("📅 Aylık Trend")
        
        date_col = "transaction_date"
        if date_col not in df.columns:
            st.info("Tarih bilgisi bulunamadı.")
            return
        
        df_copy = df.copy()
        df_copy["_date"] = pd.to_datetime(df_copy[date_col], errors="coerce")
        df_copy["_month"] = df_copy["_date"].dt.to_period("M").astype(str)
        
        monthly = df_copy.groupby("_month").agg({
            "gross_amount": "sum",
            "commission_amount": "sum"
        }).reset_index()
        monthly.columns = ["Ay", "Brüt Tutar", "Komisyon"]
        monthly = monthly.sort_values("Ay")
        
        if len(monthly) == 0:
            st.info("Aylık veri bulunamadı.")
            return
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            x=monthly["Ay"],
            y=monthly["Brüt Tutar"],
            name="Brüt Tutar",
            marker_color=self.color
        ))
        
        fig.add_trace(go.Scatter(
            x=monthly["Ay"],
            y=monthly["Komisyon"],
            mode="lines+markers",
            name="Komisyon",
            yaxis="y2",
            line=dict(color="red", width=2)
        ))
        
        fig.update_layout(
            title=f"{self.name} - Aylık Çekim ve Komisyon Trendi",
            xaxis_title="Ay",
            yaxis=dict(title="Brüt Tutar (₺)", side="left"),
            yaxis2=dict(title="Komisyon (₺)", side="right", overlaying="y"),
            legend=dict(x=0.01, y=0.99),
            hovermode="x unified"
        )
        
        st.plotly_chart(fig, width="stretch")
    
    def _render_installment_distribution(self, df: pd.DataFrame):
        """Taksit dağılımı — sadece POS işlemleri."""
        st.markdown("---")
        st.subheader("📊 Taksit Dağılımı")
        
        # Sadece POS işlemlerini kullan
        pos_df = df[df["transaction_category"] == "POS İşlemi"].copy() if "transaction_category" in df.columns else df.copy()
        
        inst_col = "installment_count"
        if inst_col not in pos_df.columns:
            st.info("Taksit bilgisi bulunamadı.")
            return
        
        taksit_summary = pos_df.groupby(inst_col).agg({
            "gross_amount": "sum",
            "commission_amount": "sum"
        }).reset_index()
        taksit_summary.columns = ["Taksit", "Tutar", "Komisyon"]
        
        # Oran hesapla
        taksit_summary["Oran %"] = taksit_summary.apply(
            lambda r: round(r["Komisyon"] / r["Tutar"] * 100, 2) if r["Tutar"] != 0 else 0, axis=1
        )
        taksit_summary["İşlem Sayısı"] = pos_df.groupby(inst_col).size().values
        
        col1, col2 = st.columns(2)
        
        with col1:
            fig = px.bar(
                taksit_summary,
                x="Taksit",
                y="Tutar",
                title="Taksit Bazında Tutar",
                color="Oran %",
                color_continuous_scale="RdYlGn_r",
                text_auto=".2s"
            )
            st.plotly_chart(fig, width="stretch")
        
        with col2:
            fig = px.pie(
                taksit_summary,
                values="Tutar",
                names="Taksit",
                title="Taksit Dağılımı",
                hole=0.4
            )
            st.plotly_chart(fig, width="stretch")
        
        st.dataframe(
            taksit_summary.style.format({
                "Tutar": _tl,
                "Komisyon": _tl,
                "Oran %": "{:.2f}%",
                "İşlem Sayısı": "{:,}"
            }),
            width="stretch",
            hide_index=True
        )
    
    def _render_detail_table(self, df: pd.DataFrame):
        """Detay tablosu."""
        st.markdown("---")
        st.subheader("📋 İşlem Detayları")
        
        with st.expander("Detay Tablosunu Göster", expanded=False):
            display_cols = [
                "transaction_date", "transaction_category", "gross_amount", "commission_amount",
                "reward_deduction", "service_deduction",
                "net_amount", "installment_count", "commission_rate",
                "rate_expected", "commission_diff", "rate_match"
            ]
            available_cols = [c for c in display_cols if c in df.columns]
            
            # Türkçe isimler
            col_names = {
                "transaction_date": "Tarih",
                "transaction_category": "Kategori",
                "gross_amount": "Brüt Tutar",
                "commission_amount": "Komisyon",
                "reward_deduction": "Ödül Kesintisi",
                "service_deduction": "Servis Kesintisi",
                "net_amount": "Net Tutar",
                "installment_count": "Taksit",
                "commission_rate": "Oran",
                "rate_expected": "Beklenen Oran",
                "commission_diff": "Fark",
                "rate_match": "Eşleşme"
            }
            
            display_df = df[available_cols].head(500).copy()
            display_df = display_df.rename(columns=col_names)
            
            st.dataframe(display_df, width="stretch", hide_index=True)
            
            if len(df) > 500:
                st.caption(f"İlk 500 satır gösteriliyor. Toplam: {len(df):,} işlem")
    
    def _render_export(self, df: pd.DataFrame):
        """Export butonu."""
        st.markdown("---")
        st.subheader("📥 Dışa Aktar")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # CSV
            csv = df.to_csv(index=False)
            st.download_button(
                label="📥 CSV İndir",
                data=csv,
                file_name=f"{self.bank_key}_detay_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        with col2:
            # Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name=self.name, index=False)
            
            st.download_button(
                label="📥 Excel İndir",
                data=output.getvalue(),
                file_name=f"{self.bank_key}_detay_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )


def render_bank_page(bank_key: str):
    """Banka sayfası render yardımcı fonksiyonu."""
    page = BankDetailPage(bank_key)
    page.render()
