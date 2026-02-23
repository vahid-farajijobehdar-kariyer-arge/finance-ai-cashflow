"""Kariyer.net Finans - POS Komisyon Takip Sistemi

Banka POS komisyon verilerini analiz eden interaktif dashboard.
Ham banka dosyalarını yükler, komisyon oranlarını doğrular ve analiz görünümleri sunar.

Çalıştırma: streamlit run src/dashboard/app.py

© 2026 Kariyer.net Finans Ekibi
"""

from pathlib import Path
from typing import Dict, Tuple
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control, get_control_summary, COMMISSION_RATES
from processing.calculator import (
    filter_successful_transactions,
    aggregate_by_bank,
    aggregate_by_installment,
    calculate_ground_totals
)

# Dashboard path for format imports
sys.path.insert(0, str(Path(__file__).parent))
from format_utils import tl, _tl

# Import cache utilities for auto-refresh
try:
    from cache_utils import auto_refresh_if_changed
except ImportError:
    def auto_refresh_if_changed():
        pass  # Fallback if not available

# Data paths
RAW_PATH = Path(__file__).parent.parent.parent / "data" / "raw"

# Commission rates by bank and installment (GÜNCELLENEN ORANLAR-v3 - January 2026)
COMMISSION_RATES = {
    "ZİRAAT BANKASI": {
        "Peşin": 0.0295, "2": 0.0489, "3": 0.0680, "4": 0.0865, "5": 0.1050,
        "6": 0.1210, "7": 0.1425, "8": 0.1612, "9": 0.1809, "10": 0.1999
    },
    "AKBANK T.A.S.": {
        "Peşin": 0.0360, "2": 0.0586, "3": 0.0773, "4": 0.0960, "5": 0.1146,
        "6": 0.1333, "7": 0.1467, "8": 0.1707, "9": 0.1891, "10": 0.2081,
        "11": 0.2268, "12": 0.2455
    },
    "T. GARANTI BANKASI A.S.": {
        "Peşin": 0.0365, "2": 0.0566, "3": 0.0753, "4": 0.0940, "5": 0.1126,
        "6": 0.1313, "7": 0.1500, "8": 0.1687, "9": 0.1874, "10": 0.2061,
        "11": 0.2248, "12": 0.2435
    },
    "T. HALK BANKASI A.S.": {
        "Peşin": 0.0374, "2": 0.0527, "3": 0.0715, "4": 0.0903, "5": 0.1091,
        "6": 0.1279, "7": 0.1467, "8": 0.1656, "9": 0.1840, "10": 0.2032,
        "11": 0.2220, "12": 0.2408
    },
    "FINANSBANK A.S.": {
        "Peşin": 0.0374, "2": 0.0561, "3": 0.0748, "4": 0.0935, "5": 0.1121,
        "6": 0.1308, "7": 0.1495, "8": 0.1682, "9": 0.1869, "10": 0.2056,
        "11": 0.2243, "12": 0.2430
    },
    "T. VAKIFLAR BANKASI T.A.O.": {
        "Peşin": 0.0336, "2": 0.0499, "3": 0.0690, "4": 0.0875, "5": 0.1060,
        "6": 0.1220, "7": 0.1435, "8": 0.1622, "9": 0.1819, "10": 0.2009,
        "12": 0.2395
    },
    "YAPI VE KREDI BANKASI A.S.": {
        "Peşin": 0.0373, "2": 0.0525, "3": 0.0700, "4": 0.0874, "5": 0.1050,
        "6": 0.1225, "7": 0.1399, "8": 0.1575, "9": 0.1750, "10": 0.1924,
        "11": 0.2100, "12": 0.2275
    },
    "T. IS BANKASI A.S.": {
        "Peşin": 0.0374
    },
}


def format_currency(value: float) -> str:
    """Format currency values for display in Turkish format with K/M suffixes.
    
    Turkish format: dot as thousands separator, comma as decimal.
    Examples: 1.234.567,89 TL, 1,23M ₺, 456,78K ₺
    """
    if value is None:
        return "-"
    
    is_negative = value < 0
    value = abs(value)
    
    if value >= 1_000_000:
        formatted = f"{value/1_000_000:.2f}".replace(".", ",") + "M"
    elif value >= 10_000:
        formatted = f"{value/1_000:.1f}".replace(".", ",") + "K"
    else:
        # Full Turkish format for smaller numbers
        formatted = f"{value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    if is_negative:
        formatted = "-" + formatted
    
    return f"₺{formatted}"


def format_currency_full(value: float) -> str:
    """Format currency in full Turkish format (no abbreviations).
    
    Example: 1.234.567,89 ₺
    """
    if value is None:
        return "-"
    
    is_negative = value < 0
    value = abs(value)
    
    formatted = f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    if is_negative:
        formatted = "-" + formatted
    
    return f"{formatted} ₺"


import os

def check_password() -> bool:
    """Returns True if the user has entered the correct password."""
    
    # Get password from secrets or environment variable
    def get_password():
        try:
            return st.secrets["passwords"]["dashboard_password"]
        except (KeyError, FileNotFoundError):
            # Fallback to environment variable or default
            return os.environ.get("DASHBOARD_PASSWORD", "kariyer2026")
    
    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if st.session_state["password"] == get_password():
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False
    
    # First run or password not correct
    if "password_correct" not in st.session_state:
        st.set_page_config(page_title="Giriş - Kariyer.net Finans", page_icon="🔐", layout="centered")
        st.title("🔐 POS Komisyon Takip Sistemi")
        st.markdown("**Kariyer.net Finans Ekibi**")
        st.markdown("---")
        st.text_input(
            "Şifre", 
            type="password", 
            key="password",
            placeholder="Şifrenizi girin..."
        )
        # Giriş butonu
        if st.button("🔑 Giriş Yap", type="primary", use_container_width=True):
            password_entered()
        st.markdown("---")
        st.caption("© 2026 Kariyer.net Finans Ekibi")
        return False
    
    # Password incorrect
    if not st.session_state["password_correct"]:
        st.set_page_config(page_title="Giriş - Kariyer.net Finans", page_icon="🔐", layout="centered")
        st.title("🔐 POS Komisyon Takip Sistemi")
        st.markdown("**Kariyer.net Finans Ekibi**")
        st.markdown("---")
        st.text_input(
            "Şifre", 
            type="password", 
            key="password",
            placeholder="Şifrenizi girin..."
        )
        # Giriş butonu
        if st.button("🔑 Giriş Yap", type="primary", use_container_width=True):
            password_entered()
        st.error("❌ Hatalı şifre")
        st.markdown("---")
        st.caption("© 2026 Kariyer.net Finans Ekibi")
        return False
    
    # Password correct
    return True


def setup_page():
    """Configure Streamlit page settings with Streamlit 1.53.0+ features."""
    st.set_page_config(
        page_title="POS Komisyon Takip Sistemi",
        page_icon="💰",
        layout="wide",
        initial_sidebar_state="expanded",
        # Streamlit 1.53.0+ sidebar width configuration
        # menu_items provides help/bug/about links
        menu_items={
            "Get Help": "https://github.com/vahid-farajijobehdar-kariyer-arge/finance-ai-cashflow",
            "Report a Bug": "https://github.com/vahid-farajijobehdar-kariyer-arge/finance-ai-cashflow/issues",
            "About": "## 💰 POS Komisyon Takip Sistemi\n© 2026 Kariyer.net Finans Ekibi"
        }
    )
    st.title("💰 POS Komisyon Takip Sistemi")
    st.markdown("**Kariyer.net Finans - 8 Banka Komisyon Analizi**")
    st.markdown("---")


def get_expected_rate(bank: str, taksit: str) -> float:
    """Get expected commission rate for bank and installment."""
    bank_rates = COMMISSION_RATES.get(bank, {})
    return bank_rates.get(taksit, bank_rates.get("Peşin", 0.03))


@st.cache_data(show_spinner="Veriler yükleniyor...", ttl=60)
def load_raw_data() -> pd.DataFrame | None:
    """Load all raw bank files from data/raw/ directory.
    
    Uses BankFileReader to auto-detect bank, parse files, and normalize columns.
    Then applies commission control to verify rates.
    
    Note: Streamlit 1.53.0+ supports scope="session" for user-isolated caching,
    but we use app-scoped cache here since all users share the same data files.
    """
    if not RAW_PATH.exists():
        return None
    
    # Initialize reader
    reader = BankFileReader()
    
    # Load all files from raw directory
    try:
        df = reader.read_all_files(RAW_PATH)
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return None
    
    if df.empty:
        return None
    
    # Reset index to avoid duplicate labels
    df = df.reset_index(drop=True)
    
    # Remove any duplicate columns (keep first)
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Filter successful transactions (exclude refunds)
    df = filter_successful_transactions(df)
    
    # Apply commission control - verify rates against expected
    df = add_commission_control(df)
    
    # Add derived columns for analysis
    if "installment_count" in df.columns:
        df["installment_count"] = df["installment_count"].fillna(1)
        df["Taksit Sayısı"] = df["installment_count"].apply(
            lambda x: "Peşin" if pd.isna(x) or x == 1 else str(int(x))
        )
    
    if "transaction_type" in df.columns:
        df["Tip"] = df["transaction_type"]
    
    if "transaction_date" in df.columns:
        df["Tarih"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        # Add month name (Turkish)
        month_map = {
            1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
            7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
        }
        df["Ay"] = df["Tarih"].dt.month.map(month_map)
    
    # Rename for backward compatibility with existing views
    # Only rename if target column doesn't already exist
    column_renames = {
        "gross_amount": "Tutar",
        "commission_amount": "Komisyon",
        "net_amount": "Net Tutar",
        "commission_rate": "Oran",
        "bank_name": "Banka Adı",
        "commission_expected": "Beklenen Komisyon",
        "rate_expected": "Beklenen Oran",
        "commission_diff": "Komisyon Farkı",
        "card_brand": "Kart Markası"
    }
    # Only rename if source exists and target doesn't exist
    rename_map = {k: v for k, v in column_renames.items() if k in df.columns and v not in df.columns}
    df = df.rename(columns=rename_map)
    
    # Remove duplicate columns after rename (keep first)
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Calculate expected net using .values to avoid index alignment issues
    if "Tutar" in df.columns and "Beklenen Komisyon" in df.columns:
        tutar_col = df["Tutar"]
        beklenen_col = df["Beklenen Komisyon"]
        # Handle case where columns might still be DataFrames (multiple columns with same name)
        if isinstance(tutar_col, pd.DataFrame):
            tutar_col = tutar_col.iloc[:, 0]
        if isinstance(beklenen_col, pd.DataFrame):
            beklenen_col = beklenen_col.iloc[:, 0]
        df["Beklenen Net"] = tutar_col.values - beklenen_col.values
    
    return df


def display_summary_metrics(df: pd.DataFrame):
    """Display key summary metrics like the Özet sheet."""
    st.subheader("📊 Özet Metrikler")
    
    # Split into Tek Çekim (Peşin) and Taksitli
    pesin_df = df[df["Taksit Sayısı"] == "Peşin"]
    taksitli_df = df[df["Taksit Sayısı"] != "Peşin"]
    
    # Use 'larger' gap for better visual separation (Streamlit 1.53.0+)
    col1, col2 = st.columns(2, gap="large")
    
    with col1:
        st.markdown("### 💵 Tek Çekim (Peşin)")
        total_pesin = pesin_df["Tutar"].sum()
        komisyon_pesin = pesin_df["Beklenen Komisyon"].sum()
        net_pesin = pesin_df["Beklenen Net"].sum()
        rate_pesin = (komisyon_pesin / total_pesin * 100) if total_pesin > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4, gap="small")
        c1.metric("Çekim", format_currency(total_pesin))
        c2.metric("Komisyon", format_currency(komisyon_pesin))
        c3.metric("Net", format_currency(net_pesin))
        c4.metric("Oran", f"%{rate_pesin:.2f}")
    
    with col2:
        st.markdown("### 💳 Taksitli")
        total_taksit = taksitli_df["Tutar"].sum()
        komisyon_taksit = taksitli_df["Beklenen Komisyon"].sum()
        net_taksit = taksitli_df["Beklenen Net"].sum()
        rate_taksit = (komisyon_taksit / total_taksit * 100) if total_taksit > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4, gap="small")
        c1.metric("Çekim", format_currency(total_taksit))
        c2.metric("Komisyon", format_currency(komisyon_taksit))
        c3.metric("Net", format_currency(net_taksit))
        c4.metric("Oran", f"%{rate_taksit:.2f}")
    
    # Total summary
    st.markdown("---")
    total = df["Tutar"].sum()
    komisyon = df["Beklenen Komisyon"].sum()
    net = df["Beklenen Net"].sum()
    avg_rate = (komisyon / total * 100) if total > 0 else 0
    
    c1, c2, c3, c4, c5 = st.columns(5, gap="medium")
    c1.metric("TOPLAM", format_currency(total))
    c2.metric("KOMİSYON", format_currency(komisyon))
    c3.metric("NET", format_currency(net))
    c4.metric("ORT. ORAN", f"%{avg_rate:.2f}")
    c5.metric("İŞLEM", f"{len(df):,}")


def display_bank_summary(df: pd.DataFrame, prefix: str = ""):
    """Display bank-level summary split by Tek Çekim and Taksitli."""
    st.subheader("🏦 Banka Bazında Özet")
    
    # Create two sections: Tek Çekim and Taksitli
    pesin_df = df[df["Taksit Sayısı"] == "Peşin"]
    taksitli_df = df[df["Taksit Sayısı"] != "Peşin"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💵 Tek Çekim (Peşin) - Banka Bazında")
        pesin_summary = pesin_df.groupby("Banka Adı").agg({
            "Tutar": "sum",
            "Beklenen Komisyon": "sum",
            "Beklenen Oran": "mean"
        }).reset_index()
        pesin_summary.columns = ["Banka", "Çekim Tutarı", "Komisyon", "Oran"]
        pesin_summary = pesin_summary.sort_values("Çekim Tutarı", ascending=False)
        
        fig = px.bar(
            pesin_summary,
            x="Banka",
            y="Çekim Tutarı",
            title="Tek Çekim - Banka Dağılımı",
            color="Banka",
            text_auto=".2s"
        )
        fig.update_layout(showlegend=False, xaxis_tickangle=-45)
        st.plotly_chart(fig, key=f"{prefix}pesin_bank_chart")
        
        st.dataframe(
            pesin_summary.style.format({
                "Çekim Tutarı": _tl,
                "Komisyon": _tl,
                "Oran": "{:.2%}"
            }),
            hide_index=True,
            width="stretch"
        )
    
    with col2:
        st.markdown("#### 💳 Taksitli - Banka Bazında")
        if len(taksitli_df) == 0:
            st.info("ℹ️ Taksitli işlem verisi bulunamadı / No installment transactions found")
        else:
            taksit_summary = taksitli_df.groupby("Banka Adı").agg({
                "Tutar": "sum",
                "Beklenen Komisyon": "sum",
                "Beklenen Oran": "mean"
            }).reset_index()
            taksit_summary.columns = ["Banka", "Çekim Tutarı", "Komisyon", "Oran"]
            taksit_summary = taksit_summary.sort_values("Çekim Tutarı", ascending=False)
            
            # Calculate distribution percentage
            total_taksit = taksit_summary["Çekim Tutarı"].sum()
            taksit_summary["Dağılım %"] = (taksit_summary["Çekim Tutarı"] / total_taksit * 100).round(2)
            
            fig = px.bar(
                taksit_summary,
                x="Banka",
                y="Çekim Tutarı",
                title="Taksitli - Banka Dağılımı",
                color="Banka",
                text_auto=".2s"
            )
            fig.update_layout(showlegend=False, xaxis_tickangle=-45)
            st.plotly_chart(fig, key=f"{prefix}taksit_bank_chart")
            
            st.dataframe(
                taksit_summary.style.format({
                    "Çekim Tutarı": _tl,
                    "Komisyon": _tl,
                    "Oran": "{:.2%}",
                    "Dağılım %": "{:.2f}%"
                }),
                hide_index=True,
                width="stretch"
            )


def display_installment_breakdown(df: pd.DataFrame):
    """Display breakdown by installment count (Taksit Sayısı)."""
    st.subheader("💳 Taksit Sayısına Göre Dağılım")
    
    # Define installment order
    installment_order = ["Peşin", "2", "3", "4", "5", "6", "7", "8", "9", "10"]
    
    # Group by installment
    installment_summary = df.groupby("Taksit Sayısı").agg({
        "Tutar": "sum",
        "Beklenen Komisyon": "sum",
        "Beklenen Oran": "mean"
    }).reset_index()
    installment_summary.columns = ["Taksit Sayısı", "Çekim Tutarı", "Komisyon", "Oran"]
    
    # Calculate percentages
    total = installment_summary["Çekim Tutarı"].sum()
    installment_summary["Tutar %"] = (installment_summary["Çekim Tutarı"] / total * 100).round(2)
    installment_summary["Adet"] = df.groupby("Taksit Sayısı").size().values
    installment_summary["Adet %"] = (installment_summary["Adet"] / len(df) * 100).round(2)
    
    # Sort by installment order
    installment_summary["Taksit Sayısı"] = pd.Categorical(
        installment_summary["Taksit Sayısı"], 
        categories=installment_order, 
        ordered=True
    )
    installment_summary = installment_summary.sort_values("Taksit Sayısı")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Bar chart - Amount by installment
        fig = px.bar(
            installment_summary,
            x="Taksit Sayısı",
            y="Çekim Tutarı",
            title="Çekim Tutarı (Taksit Sayısına Göre)",
            color="Oran",
            color_continuous_scale="RdYlGn_r",
            text_auto=".2s"
        )
        st.plotly_chart(fig, key="installment_amount")
    
    with col2:
        # Commission rate by installment
        fig = px.bar(
            installment_summary,
            x="Taksit Sayısı",
            y="Oran",
            title="Komisyon Oranı (Taksit Sayısına Göre)",
            color="Oran",
            color_continuous_scale="RdYlGn_r",
            text_auto=".2%"
        )
        st.plotly_chart(fig, key="installment_rate")
    
    # Summary table
    st.markdown("**Taksit Dağılım Tablosu:**")
    st.dataframe(
        installment_summary.style.format({
            "Çekim Tutarı": _tl,
            "Komisyon": _tl,
            "Oran": "{:.2%}",
            "Tutar %": "{:.2f}%",
            "Adet": "{:,}",
            "Adet %": "{:.2f}%"
        }),
        hide_index=True,
        width="stretch"
    )


def display_monthly_summary(df: pd.DataFrame):
    """Display monthly breakdown like the Özet sheet."""
    st.subheader("📅 Aylar İtibariyle")
    
    # Define month order
    month_order = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
                   "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
    
    # Split into Tek Çekim and Taksitli
    pesin_df = df[df["Taksit Sayısı"] == "Peşin"]
    taksitli_df = df[df["Taksit Sayısı"] != "Peşin"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 💵 Tek Çekim - Aylık")
        pesin_monthly = pesin_df.groupby("Ay").agg({
            "Tutar": "sum",
            "Beklenen Komisyon": "sum",
            "Beklenen Oran": "mean"
        }).reset_index()
        pesin_monthly.columns = ["Ay", "Çekim Tutarı", "Komisyon", "Oran"]
        pesin_monthly["Ay"] = pd.Categorical(pesin_monthly["Ay"], categories=month_order, ordered=True)
        pesin_monthly = pesin_monthly.sort_values("Ay")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=pesin_monthly["Ay"],
            y=pesin_monthly["Çekim Tutarı"],
            mode="lines+markers",
            name="Çekim Tutarı",
            line=dict(color="blue", width=2)
        ))
        fig.update_layout(title="Tek Çekim - Aylık Trend", xaxis_title="Ay", yaxis_title="Tutar (₺)")
        st.plotly_chart(fig, key="pesin_monthly_trend")
        
        st.dataframe(
            pesin_monthly.style.format({
                "Çekim Tutarı": _tl,
                "Komisyon": _tl,
                "Oran": "{:.2%}"
            }),
            hide_index=True,
            width="stretch"
        )
    
    with col2:
        st.markdown("#### 💳 Taksitli - Aylık")
        taksit_monthly = taksitli_df.groupby("Ay").agg({
            "Tutar": "sum",
            "Beklenen Komisyon": "sum",
            "Beklenen Oran": "mean"
        }).reset_index()
        taksit_monthly.columns = ["Ay", "Çekim Tutarı", "Komisyon", "Oran"]
        taksit_monthly["Ay"] = pd.Categorical(taksit_monthly["Ay"], categories=month_order, ordered=True)
        taksit_monthly = taksit_monthly.sort_values("Ay")
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=taksit_monthly["Ay"],
            y=taksit_monthly["Çekim Tutarı"],
            mode="lines+markers",
            name="Çekim Tutarı",
            line=dict(color="green", width=2)
        ))
        fig.update_layout(title="Taksitli - Aylık Trend", xaxis_title="Ay", yaxis_title="Tutar (₺)")
        st.plotly_chart(fig, key="taksit_monthly_trend")
        
        st.dataframe(
            taksit_monthly.style.format({
                "Çekim Tutarı": _tl,
                "Komisyon": _tl,
                "Oran": "{:.2%}"
            }),
            hide_index=True,
            width="stretch"
        )


def display_commission_rates_lookup(df: pd.DataFrame):
    """Display commission rates lookup table like Oranlar sheet."""
    st.subheader("📊 Komisyon Oranları")


def display_ground_totals_by_bank_date(df: pd.DataFrame):
    """Display ground totals pivot table: Bank x Date."""
    st.subheader("📊 Banka ve Tarihe Göre Toplam")
    
    # Date grouping options
    date_group = st.radio(
        "Tarih Gruplandırma:",
        ["Aylık", "Günlük"],
        horizontal=True,
        key="ground_date_group"
    )
    
    # Prepare date column
    if "Tarih" in df.columns:
        if date_group == "Aylık":
            df["Dönem"] = df["Tarih"].dt.strftime("%Y-%m")
        else:
            df["Dönem"] = df["Tarih"].dt.strftime("%Y-%m-%d")
    else:
        df["Dönem"] = "Bilinmiyor"
    
    # Create pivot table: Banka x Dönem with Tutar sum
    st.markdown("#### 💰 Brüt Tutar / Gross Amount")
    pivot_tutar = pd.pivot_table(
        df,
        values="Tutar",
        index="Banka Adı",
        columns="Dönem",
        aggfunc="sum",
        fill_value=0,
        margins=True,
        margins_name="TOPLAM"
    )
    
    st.dataframe(
        pivot_tutar.style.format(_tl).background_gradient(cmap="Blues", axis=None),
        width="stretch"
    )
    
    # Commission pivot
    st.markdown("#### 💳 Komisyon / Commission")
    pivot_komisyon = pd.pivot_table(
        df,
        values="Beklenen Komisyon",
        index="Banka Adı",
        columns="Dönem",
        aggfunc="sum",
        fill_value=0,
        margins=True,
        margins_name="TOPLAM"
    )
    
    st.dataframe(
        pivot_komisyon.style.format(_tl).background_gradient(cmap="Oranges", axis=None),
        width="stretch"
    )
    
    # Transaction count pivot
    st.markdown("#### 📈 İşlem Adedi / Transaction Count")
    pivot_adet = pd.pivot_table(
        df,
        values="Tutar",
        index="Banka Adı",
        columns="Dönem",
        aggfunc="count",
        fill_value=0,
        margins=True,
        margins_name="TOPLAM"
    )
    
    st.dataframe(
        pivot_adet.style.format("{:,.0f}").background_gradient(cmap="Greens", axis=None),
        width="stretch"
    )
    
    # Summary chart - Stacked bar by bank per period
    st.markdown("#### 📊 Banka Bazlı Dönemsel Grafik")
    summary_df = df.groupby(["Dönem", "Banka Adı"]).agg({
        "Tutar": "sum",
        "Beklenen Komisyon": "sum"
    }).reset_index()
    
    fig = px.bar(
        summary_df,
        x="Dönem",
        y="Tutar",
        color="Banka Adı",
        title="Dönemlere Göre Banka Dağılımı",
        barmode="stack",
        text_auto=".2s"
    )
    fig.update_layout(xaxis_tickangle=-45)
    st.plotly_chart(fig, width="stretch", key="bank_period_chart")
    
    # Download option
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv_tutar = pivot_tutar.to_csv()
        st.download_button(
            "📥 Tutar İndir (CSV)",
            csv_tutar,
            "tutar_by_bank_date.csv",
            "text/csv",
            key="download_tutar"
        )
    
    with col2:
        csv_komisyon = pivot_komisyon.to_csv()
        st.download_button(
            "📥 Komisyon İndir (CSV)",
            csv_komisyon,
            "komisyon_by_bank_date.csv",
            "text/csv",
            key="download_komisyon"
        )
    
    with col3:
        csv_adet = pivot_adet.to_csv()
        st.download_button(
            "📥 Adet İndir (CSV)",
            csv_adet,
            "adet_by_bank_date.csv",
            "text/csv",
            key="download_adet"
        )


def _display_commission_rates_lookup(df: pd.DataFrame):
    """Display commission rates lookup table like Oranlar sheet (helper)."""
    
    # Create rates DataFrame
    rates_data = []
    for bank, rates in COMMISSION_RATES.items():
        row = {"Banka": bank}
        for taksit in ["Peşin", "2", "3", "4", "5", "6", "7", "8", "9", "10"]:
            row[taksit] = rates.get(taksit, None)
        rates_data.append(row)
    
    rates_df = pd.DataFrame(rates_data)
    rates_df = rates_df.set_index("Banka")
    
    # Display as heatmap
    fig = px.imshow(
        rates_df.values * 100,  # Convert to percentage
        x=rates_df.columns.tolist(),
        y=rates_df.index.tolist(),
        title="Komisyon Oranları (%) - Banka x Taksit",
        labels=dict(x="Taksit Sayısı", y="Banka", color="Oran (%)"),
        color_continuous_scale="RdYlGn_r",
        aspect="auto",
        text_auto=".1f"
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, key="rates_heatmap")
    
    # Display as table
    st.markdown("**Oran Tablosu (%):**")
    st.dataframe(
        rates_df.style.format("{:.2%}", na_rep="-"),
        height=350
    )


def display_control_validation(df: pd.DataFrame):
    """Display control/validation checks - comparing expected vs actual commission."""
    st.subheader("🔍 Komisyon Kontrol")
    
    st.markdown("""
    Bu bölüm, bankadan gelen **gerçek komisyon oranlarını** beklenen oranlarla karşılaştırır.
    Farklar varsa işaretlenir.
    """)
    
    # Get control summary
    has_control = "rate_match" in df.columns and "Komisyon Farkı" in df.columns
    
    if has_control:
        # Overall control status
        matched = df["rate_match"].sum()
        total = len(df)
        mismatched = total - matched
        
        # Status banner
        if mismatched == 0:
            st.success(f"✅ **Tüm oranlar doğru!** {total:,} işlemde fark yok.")
        else:
            st.warning(f"⚠️ **{mismatched:,} işlemde oran farkı tespit edildi** ({mismatched/total*100:.1f}%)")
        
        # Summary metrics
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Toplam İşlem", f"{total:,}")
        col2.metric("Eşleşen", f"{matched:,}", delta=f"{matched/total*100:.1f}%")
        col3.metric("Fark Var", f"{mismatched:,}", delta=f"-{mismatched/total*100:.1f}%" if mismatched > 0 else None)
        
        total_diff = df["Komisyon Farkı"].sum() if "Komisyon Farkı" in df.columns else 0
        col4.metric(
            "Toplam Fark", 
            tl(abs(total_diff)),
            delta="Fazla" if total_diff > 0 else "Eksik" if total_diff < 0 else None,
            delta_color="inverse" if total_diff > 0 else "normal"
        )
        
        st.markdown("---")
        
        # Show mismatched transactions
        if mismatched > 0:
            st.markdown("### ⚠️ Fark Olan İşlemler")
            mismatched_df = df[df["rate_match"] == False].copy()
            
            display_cols = ["Tarih", "Banka Adı", "Tutar", "Taksit Sayısı", 
                          "Oran", "Beklenen Oran", "Komisyon", "Beklenen Komisyon", "Komisyon Farkı"]
            display_cols = [c for c in display_cols if c in mismatched_df.columns]
            
            st.dataframe(
                mismatched_df[display_cols].head(100).style.format({
                    "Tutar": _tl,
                    "Komisyon": _tl,
                    "Beklenen Komisyon": _tl,
                    "Komisyon Farkı": _tl,
                    "Oran": "{:.4f}",
                    "Beklenen Oran": "{:.4f}"
                }),
                hide_index=True,
                width="stretch"
            )
    
    # Bank summary with control
    st.markdown("---")
    st.markdown("### 🏦 Banka Bazında Kontrol Özeti")
    
    agg_dict = {
        "Tutar": "sum",
        "Komisyon": "sum" if "Komisyon" in df.columns else "Beklenen Komisyon",
        "Beklenen Komisyon": "sum",
    }
    if "Komisyon Farkı" in df.columns:
        agg_dict["Komisyon Farkı"] = "sum"
    
    agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
    control_summary = df.groupby("Banka Adı").agg(agg_dict).reset_index()
    control_summary["İşlem Sayısı"] = df.groupby("Banka Adı").size().values
    
    if has_control:
        control_summary["Eşleşen"] = df.groupby("Banka Adı")["rate_match"].sum().values
        control_summary["Fark Var"] = control_summary["İşlem Sayısı"] - control_summary["Eşleşen"]
    
    # Calculate effective rate
    if "Komisyon" in control_summary.columns:
        control_summary["Efektif Oran %"] = (
            control_summary["Komisyon"] / control_summary["Tutar"] * 100
        ).round(2)
    
    # Net Tutar: her zaman Tutar - Komisyon direkt hesapla
    if "Komisyon" in control_summary.columns:
        control_summary["Net Tutar"] = control_summary["Tutar"] - control_summary["Komisyon"]
    else:
        control_summary["Net Tutar"] = control_summary["Tutar"] - control_summary["Beklenen Komisyon"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        format_dict = {
            "Tutar": _tl,
            "Komisyon": _tl,
            "Beklenen Komisyon": _tl,
            "Net Tutar": _tl,
            "Komisyon Farkı": _tl,
            "Efektif Oran %": "{:.2f}%"
        }
        format_dict = {k: v for k, v in format_dict.items() if k in control_summary.columns}
        
        st.dataframe(
            control_summary.style.format(format_dict),
            hide_index=True,
            width="stretch"
        )
    
    with col2:
        st.markdown("#### Komisyon Dağılımı")
        komisyon_col = "Komisyon" if "Komisyon" in control_summary.columns else "Beklenen Komisyon"
        fig = px.pie(
            control_summary,
            values=komisyon_col,
            names="Banka Adı",
            title="Komisyon Dağılımı (Banka Bazında)",
            hole=0.4
        )
        st.plotly_chart(fig, key="commission_pie")
    
    # Grand totals
    st.markdown("---")
    st.markdown("### 📊 Toplam Kontrol / Grand Totals")
    
    total_tutar = df["Tutar"].sum()
    total_komisyon = df["Komisyon"].sum() if "Komisyon" in df.columns else df["Beklenen Komisyon"].sum()
    total_komisyon_expected = df["Beklenen Komisyon"].sum() if "Beklenen Komisyon" in df.columns else total_komisyon
    total_diff = total_komisyon - total_komisyon_expected
    # Net Tutar: her zaman Tutar - Komisyon direkt hesapla
    total_net = total_tutar - total_komisyon
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Toplam Çekim", tl(total_tutar))
    c2.metric("Gerçek Komisyon", tl(total_komisyon))
    c3.metric("Beklenen Komisyon", tl(total_komisyon_expected))
    c4.metric("Toplam Net", tl(total_net))
    
    # Comparison box
    eff_rate = (total_komisyon / total_tutar * 100) if total_tutar > 0 else 0
    expected_rate = (total_komisyon_expected / total_tutar * 100) if total_tutar > 0 else 0
    
    st.info(f"""
    **Kontrol Sonucu:**
    - Toplam Çekim: {tl(total_tutar)}
    - Gerçek Komisyon: {tl(total_komisyon)} (Efektif: %{eff_rate:.2f})
    - Beklenen Komisyon: {tl(total_komisyon_expected)} (Beklenen: %{expected_rate:.2f})
    - Fark: {tl(total_diff)}
    - Net Tutar: {tl(total_net)}
    """)


def display_data_table(df: pd.DataFrame):
    """Display filtered data table with export."""
    st.subheader("📋 İşlem Verileri")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        bank_values = df["Banka Adı"].dropna().unique().tolist()
        bank_values = [str(b) for b in bank_values if pd.notna(b)]
        banks = ["Tümü"] + sorted(bank_values)
        selected_bank = st.selectbox("Banka", banks, key="data_bank")
    
    with col2:
        months = ["Tümü"] + [str(m) for m in df["Ay"].dropna().unique().tolist()]
        selected_month = st.selectbox("Ay", months, key="data_month")
    
    with col3:
        types = ["Tümü"] + [str(t) for t in df["Tip"].dropna().unique().tolist() if pd.notna(t)]
        selected_type = st.selectbox("Tip", types, key="data_type")
    
    with col4:
        taksit_values = [str(t) for t in df["Taksit Sayısı"].dropna().unique().tolist() if pd.notna(t)]
        taksit_options = ["Tümü"] + sorted(taksit_values, key=lambda x: (0, int(x)) if x.isdigit() else (1, x))
        selected_taksit = st.selectbox("Taksit", taksit_options, key="data_taksit")
    
    # Apply filters
    filtered = df.copy()
    if selected_bank != "Tümü":
        filtered = filtered[filtered["Banka Adı"] == selected_bank]
    if selected_month != "Tümü":
        filtered = filtered[filtered["Ay"] == selected_month]
    if selected_type != "Tümü":
        filtered = filtered[filtered["Tip"] == selected_type]
    if selected_taksit != "Tümü":
        filtered = filtered[filtered["Taksit Sayısı"] == selected_taksit]
    
    # Show summary for filtered data
    st.markdown(f"**{len(filtered):,} işlem gösteriliyor**")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Filtreli Toplam", tl(filtered['Tutar'].sum()))
    c2.metric("Filtreli Komisyon", tl(filtered['Beklenen Komisyon'].sum()))
    c3.metric("Filtreli Net", tl(filtered['Beklenen Net'].sum()))
    
    # Display columns
    display_cols = ["Tarih", "Ay", "Banka Adı", "Tutar", "Taksit Sayısı", "Tip", 
                    "Beklenen Oran", "Beklenen Komisyon", "Beklenen Net", "Kart Markası"]
    display_cols = [c for c in display_cols if c in filtered.columns]
    
    st.dataframe(
        filtered[display_cols].head(1000).style.format({
            "Tutar": _tl,
            "Beklenen Komisyon": _tl,
            "Beklenen Net": _tl,
            "Beklenen Oran": "{:.2%}"
        }),
        hide_index=True,
        width="stretch"
    )
    
    # Export
    csv = filtered.to_csv(index=False)
    st.download_button(
        label="📥 CSV İndir",
        data=csv,
        file_name="komisyon_analizi_export.csv",
        mime="text/csv"
    )


def main():
    """Main dashboard application."""
    # Check password first
    if not check_password():
        return
    
    setup_page()
    
    # Auto-refresh data if files have changed (data reset on import)
    auto_refresh_if_changed()
    
    # Load data from raw files
    df = load_raw_data()
    
    if df is None or df.empty:
        st.warning("""
        ⚠️ **Veri Bulunamadı**
        
        Henüz banka ekstre dosyası yüklenmemiş.
        
        **Nasıl yüklenir?**
        1. Sol menüden **"📤 Dosya Yükle"** sayfasına gidin
        2. Banka ekstre dosyalarınızı (Excel/CSV) yükleyin
        3. Ana Panel'e geri dönün
        
        ---
        📖 Detaylı bilgi için **"📖 Nasıl Kullanılır"** sayfasına bakın.
        """)
        
        # Yüklü dosyaları göster
        if RAW_PATH.exists():
            files = [f.name for f in RAW_PATH.glob("*") if not f.name.startswith('.')]
            if files:
                st.info(f"📁 Mevcut dosyalar: {files}")
        return
    
    # Yükleme başarılı mesajı
    source_files = df["source_file"].unique() if "source_file" in df.columns else []
    st.success(f"✅ {len(df):,} işlem yüklendi ({len(source_files)} dosyadan)")
    
    if source_files.any() if hasattr(source_files, 'any') else len(source_files) > 0:
        with st.expander("📁 Yüklenen dosyalar"):
            for f in source_files:
                st.write(f"• {f}")
    
    # Tabs - matching manual workflow
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "📊 Özet",
        "🏦 Banka",
        "💳 Taksit",
        "📅 Aylık",
        "📊 Oranlar",
        "🔍 Kontrol"
    ])
    
    with tab1:
        display_summary_metrics(df)
        st.markdown("---")
        display_bank_summary(df, prefix="summary_")
    
    with tab2:
        display_bank_summary(df, prefix="bank_")
    
    with tab3:
        display_installment_breakdown(df)
    
    with tab4:
        display_monthly_summary(df)
        st.markdown("---")
        display_ground_totals_by_bank_date(df)
    
    with tab5:
        display_commission_rates_lookup(df)
        _display_commission_rates_lookup(df)
    
    with tab6:
        display_control_validation(df)
        st.markdown("---")
        display_data_table(df)


if __name__ == "__main__":
    main()
