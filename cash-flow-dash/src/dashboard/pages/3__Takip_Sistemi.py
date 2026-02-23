"""
💰 POS Komisyon Takip Sistemi - Ana analiz sayfası

Özet metrikleri, banka dağılımları ve komisyon analizleri.

© 2026 Kariyer.net Finans Ekibi
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password
from cache_utils import auto_refresh_if_changed
from format_utils import _tl

from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control
from processing.calculator import filter_successful_transactions

# Data path
RAW_PATH = PROJECT_ROOT.parent / "data" / "raw"


st.set_page_config(
    page_title="Takip Sistemi - POS Komisyon",
    page_icon="💰",
    layout="wide"
)

# Authentication
if not check_password():
    st.stop()

# Auto refresh if data changed
auto_refresh_if_changed()

st.title("💰 POS Komisyon Takip Sistemi")
st.markdown("**Kariyer.net Finans - 8 Banka Komisyon Analizi**")
st.markdown("---")


def format_currency(value: float) -> str:
    """Format currency values in Turkish format with K/M suffixes.
    
    Turkish format: dot as thousands separator, comma as decimal.
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
        formatted = f"{value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    if is_negative:
        formatted = "-" + formatted
    
    return f"₺{formatted}"


@st.cache_data(show_spinner="Veriler yükleniyor...", ttl=60)
def load_data() -> pd.DataFrame | None:
    """Load and process bank data."""
    if not RAW_PATH.exists():
        return None
    
    reader = BankFileReader()
    
    try:
        df = reader.read_all_files(RAW_PATH)
    except Exception as e:
        st.error(f"Dosya okuma hatası: {e}")
        return None
    
    if df.empty:
        return None
    
    df = df.reset_index(drop=True)
    df = df.loc[:, ~df.columns.duplicated()]
    df = filter_successful_transactions(df)
    df = add_commission_control(df)
    
    # Add derived columns
    if "installment_count" in df.columns:
        df["installment_count"] = df["installment_count"].fillna(1)
        df["Taksit Sayısı"] = df["installment_count"].apply(
            lambda x: "Peşin" if pd.isna(x) or x in (0, 1) else str(int(x))
        )
    
    if "transaction_date" in df.columns:
        df["Tarih"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        month_map = {
            1: "Ocak", 2: "Şubat", 3: "Mart", 4: "Nisan", 5: "Mayıs", 6: "Haziran",
            7: "Temmuz", 8: "Ağustos", 9: "Eylül", 10: "Ekim", 11: "Kasım", 12: "Aralık"
        }
        df["Ay"] = df["Tarih"].dt.month.map(month_map)
    
    # Rename columns
    column_renames = {
        "gross_amount": "Tutar",
        "commission_amount": "Komisyon",
        "net_amount": "Net Tutar",
        "commission_rate": "Oran",
        "bank_name": "Banka Adı",
        "commission_expected": "Beklenen Komisyon",
        "rate_expected": "Beklenen Oran",
        "commission_diff": "Komisyon Farkı",
    }
    rename_map = {k: v for k, v in column_renames.items() if k in df.columns and v not in df.columns}
    df = df.rename(columns=rename_map)
    df = df.loc[:, ~df.columns.duplicated()]
    
    # Calculate expected net
    if "Tutar" in df.columns and "Beklenen Komisyon" in df.columns:
        df["Beklenen Net"] = df["Tutar"] - df["Beklenen Komisyon"]
    
    return df


# Load data
df = load_data()

if df is None or df.empty:
    st.warning("⚠️ Henüz veri yüklenmemiş.")
    st.markdown("Lütfen **📤 Dosya Yükle** sayfasından banka dosyalarını yükleyin.")
    st.stop()

# Summary Metrics
st.subheader("📊 Özet Metrikler")

# Split by Peşin and Taksitli
pesin_df = df[df["Taksit Sayısı"] == "Peşin"]
taksitli_df = df[df["Taksit Sayısı"] != "Peşin"]

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

# Charts
st.markdown("---")
st.subheader("📈 Banka Dağılımı")

col1, col2 = st.columns(2, gap="large")

with col1:
    # Bank distribution pie chart
    bank_summary = df.groupby("Banka Adı").agg({"Tutar": "sum"}).reset_index()
    bank_summary = bank_summary.sort_values("Tutar", ascending=False)
    
    fig_pie = px.pie(
        bank_summary,
        values="Tutar",
        names="Banka Adı",
        title="Banka Bazında Tutar Dağılımı",
        hole=0.4
    )
    fig_pie.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig_pie, width="stretch")

with col2:
    # Bank bar chart
    fig_bar = px.bar(
        bank_summary,
        x="Banka Adı",
        y="Tutar",
        title="Banka Bazında Çekim Tutarları",
        color="Banka Adı",
        text_auto=".2s"
    )
    fig_bar.update_layout(showlegend=False, xaxis_tickangle=-45)
    st.plotly_chart(fig_bar, width="stretch")

# Installment distribution
st.markdown("---")
st.subheader("📊 Taksit Dağılımı")

taksit_summary = df.groupby("Taksit Sayısı").agg({
    "Tutar": "sum",
    "Beklenen Komisyon": "sum"
}).reset_index()

# Sort properly (Peşin first, then numeric)
def sort_taksit(x):
    if x == "Peşin":
        return 0
    try:
        return int(x)
    except:
        return 999

taksit_summary["sort_key"] = taksit_summary["Taksit Sayısı"].apply(sort_taksit)
taksit_summary = taksit_summary.sort_values("sort_key")

fig_taksit = px.bar(
    taksit_summary,
    x="Taksit Sayısı",
    y="Tutar",
    title="Taksit Bazında Dağılım",
    color="Beklenen Komisyon",
    color_continuous_scale="RdYlGn_r",
    text_auto=".2s"
)
fig_taksit.update_layout(xaxis_tickangle=0)
st.plotly_chart(fig_taksit, width="stretch")

# Data table
st.markdown("---")
st.subheader("📋 Detaylı Veri")

with st.expander("Veri Tablosunu Göster", expanded=False):
    display_cols = ["Banka Adı", "Tarih", "Tutar", "Beklenen Komisyon", "Beklenen Net", "Taksit Sayısı"]
    available_cols = [c for c in display_cols if c in df.columns]
    
    st.dataframe(
        df[available_cols].style.format({
            "Tutar": _tl,
            "Beklenen Komisyon": _tl,
            "Beklenen Net": _tl
        }),
        width="stretch",
        hide_index=True
    )

# Footer
st.markdown("---")
st.caption("© 2026 Kariyer.net Finans Ekibi")
