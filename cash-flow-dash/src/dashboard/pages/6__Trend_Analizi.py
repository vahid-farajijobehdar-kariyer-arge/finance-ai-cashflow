"""
📈 Trend Analizi - Kariyer.net Finans

Aylık ve banka bazlı trend analizi dashboard.

© 2026 Kariyer.net Finans Ekibi
"""

from datetime import datetime
from pathlib import Path
import sys

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control
from processing.calculator import filter_successful_transactions, calculate_ground_totals

# Import auth module
sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password
from format_utils import tl, _tl0

# Data paths
RAW_PATH = PROJECT_ROOT.parent / "data" / "raw"


def get_all_files_with_metadata() -> list:
    """Tüm dosyaları metadata ile birlikte döndür."""
    all_files = []
    
    if not RAW_PATH.exists():
        return all_files
    
    # Düz yapıdaki dosyalar
    for f in RAW_PATH.glob("*"):
        if f.is_file() and not f.name.startswith(".") and f.suffix.lower() in [".csv", ".xlsx", ".xls"]:
            all_files.append({
                "path": f,
                "bank": detect_bank_from_filename(f.name) or "Diğer",
                "month": datetime.fromtimestamp(f.stat().st_mtime).strftime("%Y-%m"),
                "name": f.name,
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
                            })
    
    return all_files


def detect_bank_from_filename(filename: str) -> str | None:
    """Detect bank name from filename."""
    bank_patterns = {
        "vakıf": "Vakıfbank", "vakif": "Vakıfbank",
        "akbank": "Akbank",
        "garanti": "Garanti",
        "halkbank": "Halkbank", "halk": "Halkbank",
        "ziraat": "Ziraat",
        "ykb": "YKB", "yapı kredi": "YKB",
        "iş bankası": "İşbankası", "isbank": "İşbankası",
        "qnb": "QNB", "finans": "QNB",
    }
    
    filename_lower = filename.lower()
    for pattern, bank_name in bank_patterns.items():
        if pattern in filename_lower:
            return bank_name
    return None


@st.cache_data(ttl=300)
def load_all_data() -> pd.DataFrame:
    """Tüm dosyaları yükle ve birleştir."""
    all_files = get_all_files_with_metadata()
    
    if not all_files:
        return pd.DataFrame()
    
    reader = BankFileReader()
    all_dfs = []
    
    for file_info in all_files:
        try:
            df = reader.read_file(file_info["path"])
            df["_source_bank"] = file_info["bank"]
            df["_source_month"] = file_info["month"]
            df["_source_file"] = file_info["name"]
            
            # Komisyon kontrolü ekle
            df = filter_successful_transactions(df)
            df = add_commission_control(df, file_info["bank"])
            
            all_dfs.append(df)
        except Exception as e:
            st.warning(f"⚠️ {file_info['name']} okunamadı: {e}")
    
    if not all_dfs:
        return pd.DataFrame()
    
    return pd.concat(all_dfs, ignore_index=True)


def render_summary_metrics(df: pd.DataFrame):
    """Özet metrikleri göster."""
    st.header("📊 Genel Özet")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_gross = df["gross_amount"].sum() if "gross_amount" in df.columns else 0
        st.metric("💰 Toplam Brüt", tl(total_gross, decimals=0))
    
    with col2:
        total_commission = df["commission_amount"].sum() if "commission_amount" in df.columns else 0
        st.metric("🏦 Toplam Komisyon", tl(total_commission, decimals=0))
    
    with col3:
        total_net = df["net_amount"].sum() if "net_amount" in df.columns else 0
        st.metric("✅ Toplam Net", tl(total_net, decimals=0))
    
    with col4:
        tx_count = len(df)
        st.metric("📊 İşlem Sayısı", f"{tx_count:,}")


def render_monthly_trend(df: pd.DataFrame):
    """Aylık trend grafiği."""
    st.header("📈 Aylık Trend")
    
    if "_source_month" not in df.columns:
        st.info("Trend verisi için dosyaları aylık organize edin.")
        return
    
    # Aylık toplam
    monthly = df.groupby("_source_month").agg({
        "gross_amount": "sum",
        "commission_amount": "sum",
        "net_amount": "sum"
    }).reset_index()
    monthly = monthly.sort_values("_source_month")
    
    # Grafik türü seçimi
    chart_type = st.radio(
        "Grafik Türü",
        ["Çizgi", "Bar", "Alan"],
        horizontal=True,
        key="monthly_chart_type"
    )
    
    if chart_type == "Çizgi":
        fig = px.line(
            monthly,
            x="_source_month",
            y=["gross_amount", "commission_amount", "net_amount"],
            labels={"_source_month": "Ay", "value": "Tutar (₺)", "variable": "Tür"},
            title="Aylık Brüt/Komisyon/Net Trend"
        )
    elif chart_type == "Bar":
        fig = px.bar(
            monthly,
            x="_source_month",
            y=["gross_amount", "net_amount"],
            labels={"_source_month": "Ay", "value": "Tutar (₺)", "variable": "Tür"},
            title="Aylık Brüt vs Net",
            barmode="group"
        )
    else:
        fig = px.area(
            monthly,
            x="_source_month",
            y=["gross_amount", "net_amount"],
            labels={"_source_month": "Ay", "value": "Tutar (₺)", "variable": "Tür"},
            title="Aylık Brüt/Net Alan Grafiği"
        )
    
    fig.update_layout(height=400)
    st.plotly_chart(fig, width="stretch")
    
    # Tablo
    with st.expander("📋 Aylık Detay Tablosu"):
        monthly_display = monthly.copy()
        monthly_display.columns = ["Ay", "Brüt Tutar", "Komisyon", "Net Tutar"]
        monthly_display["Brüt Tutar"] = monthly_display["Brüt Tutar"].apply(lambda x: tl(x))
        monthly_display["Komisyon"] = monthly_display["Komisyon"].apply(lambda x: tl(x))
        monthly_display["Net Tutar"] = monthly_display["Net Tutar"].apply(lambda x: tl(x))
        st.dataframe(monthly_display, width="stretch")


def render_bank_comparison(df: pd.DataFrame):
    """Banka karşılaştırma grafiği."""
    st.header("🏦 Banka Karşılaştırması")
    
    if "_source_bank" not in df.columns:
        st.info("Banka karşılaştırması için veri yükleyin.")
        return
    
    # Banka bazlı toplam
    by_bank = df.groupby("_source_bank").agg({
        "gross_amount": "sum",
        "commission_amount": "sum",
        "net_amount": "sum"
    }).reset_index()
    by_bank = by_bank.sort_values("gross_amount", ascending=False)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pasta grafiği - Brüt dağılım
        fig_pie = px.pie(
            by_bank,
            values="gross_amount",
            names="_source_bank",
            title="Brüt Tutar Dağılımı"
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, width="stretch")
    
    with col2:
        # Bar grafiği - Komisyon oranları
        by_bank["commission_rate"] = (by_bank["commission_amount"] / by_bank["gross_amount"] * 100).round(2)
        fig_bar = px.bar(
            by_bank,
            x="_source_bank",
            y="commission_rate",
            title="Ortalama Komisyon Oranı (%)",
            labels={"_source_bank": "Banka", "commission_rate": "Oran (%)"},
            color="commission_rate",
            color_continuous_scale="RdYlGn_r"
        )
        st.plotly_chart(fig_bar, width="stretch")
    
    # Detay tablo
    with st.expander("📋 Banka Detay Tablosu"):
        bank_display = by_bank.copy()
        bank_display.columns = ["Banka", "Brüt Tutar", "Komisyon", "Net Tutar", "Oran (%)"]
        bank_display["Brüt Tutar"] = bank_display["Brüt Tutar"].apply(lambda x: tl(x))
        bank_display["Komisyon"] = bank_display["Komisyon"].apply(lambda x: tl(x))
        bank_display["Net Tutar"] = bank_display["Net Tutar"].apply(lambda x: tl(x))
        st.dataframe(bank_display, width="stretch")


def render_bank_monthly_heatmap(df: pd.DataFrame):
    """Banka x Ay heatmap."""
    st.header("🗓️ Banka-Ay Isı Haritası")
    
    if "_source_bank" not in df.columns or "_source_month" not in df.columns:
        st.info("Isı haritası için yeterli veri yok.")
        return
    
    # Pivot tablo oluştur
    metric = st.selectbox(
        "Metrik",
        ["Brüt Tutar", "Komisyon", "Net Tutar", "İşlem Sayısı"],
        key="heatmap_metric"
    )
    
    metric_col = {
        "Brüt Tutar": "gross_amount",
        "Komisyon": "commission_amount",
        "Net Tutar": "net_amount",
        "İşlem Sayısı": "gross_amount"
    }[metric]
    
    agg_func = "sum" if metric != "İşlem Sayısı" else "count"
    
    pivot = df.pivot_table(
        index="_source_bank",
        columns="_source_month",
        values=metric_col,
        aggfunc=agg_func,
        fill_value=0
    )
    
    fig = px.imshow(
        pivot,
        labels={"x": "Ay", "y": "Banka", "color": metric},
        title=f"{metric} - Banka/Ay Isı Haritası",
        color_continuous_scale="Blues"
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, width="stretch")


def render_commission_trend(df: pd.DataFrame):
    """Komisyon oranı trend analizi."""
    st.header("📉 Komisyon Oranı Trendi")
    
    if "_source_month" not in df.columns:
        return
    
    # Aylık ortalama komisyon oranı
    df_with_rate = df[df["gross_amount"] > 0].copy()
    df_with_rate["calc_rate"] = df_with_rate["commission_amount"] / df_with_rate["gross_amount"] * 100
    
    monthly_rate = df_with_rate.groupby("_source_month")["calc_rate"].mean().reset_index()
    monthly_rate = monthly_rate.sort_values("_source_month")
    
    fig = px.line(
        monthly_rate,
        x="_source_month",
        y="calc_rate",
        title="Aylık Ortalama Komisyon Oranı (%)",
        labels={"_source_month": "Ay", "calc_rate": "Oran (%)"},
        markers=True
    )
    fig.update_layout(height=300)
    st.plotly_chart(fig, width="stretch")


# Page config
st.set_page_config(
    page_title="Trend Analizi - Nakit Akış Paneli",
    page_icon="📈",
    layout="wide"
)

# Require authentication
if not check_password():
    st.stop()

st.title("📈 Trend Analizi")
st.markdown("Aylık ve banka bazlı performans trendlerini analiz edin.")
st.markdown("---")

# Veri yükle
with st.spinner("Veriler yükleniyor..."):
    df = load_all_data()

if df.empty:
    st.warning("📁 Analiz için veri bulunamadı. Lütfen önce dosya yükleyin.")
    st.page_link("pages/1__Dosya_Yukle.py", label="📤 Dosya Yükle", icon="📤")
else:
    # Filtreler
    with st.sidebar:
        st.header("🔍 Filtreler")
        
        # Banka filtresi
        all_banks = df["_source_bank"].unique().tolist() if "_source_bank" in df.columns else []
        selected_banks = st.multiselect(
            "Banka",
            options=all_banks,
            default=all_banks,
            key="filter_banks"
        )
        
        # Ay filtresi
        all_months = sorted(df["_source_month"].unique().tolist()) if "_source_month" in df.columns else []
        selected_months = st.multiselect(
            "Ay",
            options=all_months,
            default=all_months,
            key="filter_months"
        )
    
    # Filtreleri uygula
    df_filtered = df.copy()
    if selected_banks and "_source_bank" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["_source_bank"].isin(selected_banks)]
    if selected_months and "_source_month" in df_filtered.columns:
        df_filtered = df_filtered[df_filtered["_source_month"].isin(selected_months)]
    
    # Dashboard bölümleri
    render_summary_metrics(df_filtered)
    st.markdown("---")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Aylık Trend", "🏦 Banka Karşılaştırma", "🗓️ Isı Haritası", "📉 Komisyon Trendi"])
    
    with tab1:
        render_monthly_trend(df_filtered)
    
    with tab2:
        render_bank_comparison(df_filtered)
    
    with tab3:
        render_bank_monthly_heatmap(df_filtered)
    
    with tab4:
        render_commission_trend(df_filtered)
