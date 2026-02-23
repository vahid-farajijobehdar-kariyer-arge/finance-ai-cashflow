"""
📊 Konsolide Rapor - Tüm bankaların toplam özeti

Yüklenen tüm banka verilerinin konsolide brüt, komisyon ve net toplamları.

© 2026 Kariyer.net Finans Ekibi
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import sys
from pathlib import Path
from datetime import datetime
from calendar import monthrange

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control
from processing.calculator import filter_successful_transactions

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password

# Data path
RAW_PATH = PROJECT_ROOT.parent / "data" / "raw"


def format_currency(value: float) -> str:
    """Türk Lirası formatı — okunabilir K/M kısaltmalı."""
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


st.set_page_config(
    page_title="Konsolide Rapor - POS Komisyon",
    page_icon="📊",
    layout="wide"
)

# Authentication
if not check_password():
    st.stop()

st.title("📊 Konsolide Rapor")
st.markdown("**Tüm bankaların toplam brüt, komisyon ve net özeti**")
st.markdown("---")


@st.cache_data(ttl=60)
def load_data():
    """Veri yükle ve işle."""
    if not RAW_PATH.exists():
        return None
    
    reader = BankFileReader()
    try:
        df = reader.read_all_files(RAW_PATH)
    except Exception:
        return None
    
    if df.empty:
        return None
    
    df = df.reset_index(drop=True)
    df = df.loc[:, ~df.columns.duplicated()]
    
    df = filter_successful_transactions(df)
    df = add_commission_control(df)
    
    return df


def display_no_data_message():
    """Veri yok mesajı göster."""
    st.warning("""
    ⚠️ **Veri Bulunamadı**
    
    Henüz banka ekstre dosyası yüklenmemiş.
    
    **Nasıl yüklenir?**
    1. Sol menüden **"📤 Dosya Yükle"** sayfasına gidin
    2. Banka ekstre dosyalarınızı (Excel/CSV) yükleyin
    3. Bu sayfaya geri dönün
    
    ---
    📖 Detaylı bilgi için **"📖 Nasıl Kullanılır"** sayfasına bakın.
    """)


def display_grand_totals(df: pd.DataFrame):
    """Tüm bankaların genel toplamlarını göster."""
    st.subheader("💰 Genel Toplam")
    
    total_gross = df["gross_amount"].sum() if "gross_amount" in df.columns else 0
    total_commission = df["commission_amount"].sum() if "commission_amount" in df.columns else 0
    total_net = total_gross - total_commission
    avg_rate = (total_commission / total_gross * 100) if total_gross != 0 else 0
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("📊 Toplam İşlem", f"{len(df):,}")
    with col2:
        st.metric("💵 Toplam Brüt", format_currency(total_gross))
    with col3:
        st.metric("💳 Toplam Komisyon", format_currency(total_commission))
    with col4:
        st.metric("💰 Toplam Net", format_currency(total_net))
    with col5:
        st.metric("📈 Ort. Komisyon Oranı", f"%{avg_rate:.2f}")
    
    # Formül açıklaması
    st.caption(
        f"NET = Brüt ({format_currency_full(total_gross)}) "
        f"− Komisyon ({format_currency_full(total_commission)}) "
        f"= **{format_currency_full(total_net)}**"
    )


def display_bank_breakdown(df: pd.DataFrame):
    """Banka bazlı kırılım tablosu."""
    st.subheader("🏦 Banka Bazlı Kırılım")
    
    banks = sorted(df["bank_name"].unique())
    
    rows = []
    for bank in banks:
        bank_df = df[df["bank_name"] == bank]
        gross = bank_df["gross_amount"].sum() if "gross_amount" in bank_df.columns else 0
        commission = bank_df["commission_amount"].sum() if "commission_amount" in bank_df.columns else 0
        net = gross - commission
        rate = (commission / gross * 100) if gross != 0 else 0
        rows.append({
            "Banka": bank,
            "İşlem Sayısı": len(bank_df),
            "Brüt Tutar (₺)": gross,
            "Komisyon (₺)": commission,
            "Net Tutar (₺)": net,
            "Komisyon Oranı (%)": rate,
        })
    
    summary_df = pd.DataFrame(rows)
    
    # Toplam satırı ekle
    total_row = {
        "Banka": "TOPLAM",
        "İşlem Sayısı": summary_df["İşlem Sayısı"].sum(),
        "Brüt Tutar (₺)": summary_df["Brüt Tutar (₺)"].sum(),
        "Komisyon (₺)": summary_df["Komisyon (₺)"].sum(),
        "Net Tutar (₺)": summary_df["Net Tutar (₺)"].sum(),
        "Komisyon Oranı (%)": (
            summary_df["Komisyon (₺)"].sum() / summary_df["Brüt Tutar (₺)"].sum() * 100
            if summary_df["Brüt Tutar (₺)"].sum() != 0 else 0
        ),
    }
    summary_df = pd.concat([summary_df, pd.DataFrame([total_row])], ignore_index=True)
    
    # Koşullu stil: TOPLAM satırını kalın göster
    def highlight_total(row):
        if row["Banka"] == "TOPLAM":
            return ["font-weight: bold; background-color: #f0f2f6"] * len(row)
        return [""] * len(row)
    
    st.dataframe(
        summary_df.style.apply(highlight_total, axis=1).format({
            "İşlem Sayısı": "{:,}",
            "Brüt Tutar (₺)": "₺{:,.2f}",
            "Komisyon (₺)": "₺{:,.2f}",
            "Net Tutar (₺)": "₺{:,.2f}",
            "Komisyon Oranı (%)": "%{:.2f}",
        }),
        use_container_width=True,
        hide_index=True
    )


def display_bank_charts(df: pd.DataFrame):
    """Banka bazlı grafikler."""
    st.subheader("📈 Banka Karşılaştırma Grafikleri")
    
    banks = sorted(df["bank_name"].unique())
    
    chart_data = []
    for bank in banks:
        bank_df = df[df["bank_name"] == bank]
        gross = bank_df["gross_amount"].sum()
        commission = bank_df["commission_amount"].sum()
        net = gross - commission
        chart_data.append({
            "Banka": bank,
            "Brüt Tutar": gross,
            "Komisyon": commission,
            "Net Tutar": net,
            "Komisyon Oranı (%)": (commission / gross * 100) if gross != 0 else 0,
        })
    
    chart_df = pd.DataFrame(chart_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Brüt tutar pasta grafiği
        fig = px.pie(
            chart_df,
            values="Brüt Tutar",
            names="Banka",
            title="Banka Bazlı Brüt Tutar Dağılımı",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Komisyon pasta grafiği
        fig = px.pie(
            chart_df,
            values="Komisyon",
            names="Banka",
            title="Banka Bazlı Komisyon Dağılımı",
            hole=0.4
        )
        st.plotly_chart(fig, use_container_width=True)
    
    # Karşılaştırma bar grafiği
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=chart_df["Banka"],
        y=chart_df["Brüt Tutar"],
        name="Brüt Tutar",
        marker_color="#1f77b4",
        text=chart_df["Brüt Tutar"].apply(lambda x: format_currency(x)),
        textposition="outside"
    ))
    fig.add_trace(go.Bar(
        x=chart_df["Banka"],
        y=chart_df["Komisyon"],
        name="Komisyon",
        marker_color="#ff7f0e",
        text=chart_df["Komisyon"].apply(lambda x: format_currency(x)),
        textposition="outside"
    ))
    fig.add_trace(go.Bar(
        x=chart_df["Banka"],
        y=chart_df["Net Tutar"],
        name="Net Tutar",
        marker_color="#2ca02c",
        text=chart_df["Net Tutar"].apply(lambda x: format_currency(x)),
        textposition="outside"
    ))
    fig.update_layout(
        title="Banka Bazlı Brüt / Komisyon / Net Karşılaştırma",
        barmode="group",
        xaxis_title="Banka",
        yaxis_title="Tutar (₺)",
        legend=dict(x=0.01, y=0.99),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Komisyon oranı karşılaştırma
    fig2 = px.bar(
        chart_df,
        x="Banka",
        y="Komisyon Oranı (%)",
        title="Banka Bazlı Ortalama Komisyon Oranı (%)",
        color="Komisyon Oranı (%)",
        color_continuous_scale="RdYlGn_r",
        text=chart_df["Komisyon Oranı (%)"].apply(lambda x: f"%{x:.2f}")
    )
    fig2.update_traces(textposition="outside")
    fig2.update_layout(yaxis_title="Oran (%)")
    st.plotly_chart(fig2, use_container_width=True)


def display_monthly_consolidated(df: pd.DataFrame):
    """Aylık konsolide trend."""
    st.subheader("📅 Aylık Konsolide Trend")
    
    date_col = None
    for col in ["settlement_date", "transaction_date"]:
        if col in df.columns:
            date_col = col
            break
    
    if date_col is None:
        st.info("Tarih bilgisi mevcut değil.")
        return
    
    df_copy = df.copy()
    df_copy["_date"] = pd.to_datetime(df_copy[date_col], errors="coerce")
    df_copy["Ay"] = df_copy["_date"].dt.to_period("M").astype(str)
    
    monthly = df_copy.groupby("Ay").agg({
        "gross_amount": "sum",
        "commission_amount": "sum"
    }).reset_index()
    monthly.columns = ["Ay", "Brüt Tutar", "Komisyon"]
    monthly["Net Tutar"] = monthly["Brüt Tutar"] - monthly["Komisyon"]
    monthly = monthly.sort_values("Ay")
    
    if monthly.empty:
        st.info("Aylık veri bulunamadı.")
        return
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=monthly["Ay"], y=monthly["Brüt Tutar"],
        name="Brüt Tutar", marker_color="#1f77b4"
    ))
    fig.add_trace(go.Bar(
        x=monthly["Ay"], y=monthly["Komisyon"],
        name="Komisyon", marker_color="#ff7f0e"
    ))
    fig.add_trace(go.Scatter(
        x=monthly["Ay"], y=monthly["Net Tutar"],
        mode="lines+markers", name="Net Tutar",
        line=dict(color="#2ca02c", width=3)
    ))
    fig.update_layout(
        title="Aylık Konsolide Brüt, Komisyon ve Net Tutar",
        barmode="group",
        xaxis_title="Ay",
        yaxis_title="Tutar (₺)",
        legend=dict(x=0.01, y=0.99),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Aylık tablo
    st.dataframe(
        monthly.style.format({
            "Brüt Tutar": "₺{:,.2f}",
            "Komisyon": "₺{:,.2f}",
            "Net Tutar": "₺{:,.2f}",
        }),
        use_container_width=True,
        hide_index=True
    )


def display_commission_control_summary(df: pd.DataFrame):
    """Konsolide komisyon kontrol özeti."""
    st.subheader("🔍 Komisyon Kontrol Özeti")
    
    if "rate_match" not in df.columns:
        st.info("Komisyon kontrol verisi mevcut değil.")
        return
    
    matched = df["rate_match"].sum()
    total = len(df)
    mismatch = total - matched
    
    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Eşleşen", f"{matched:,}")
    col2.metric("❌ Eşleşmeyen", f"{mismatch:,}")
    col3.metric("📊 Eşleşme Oranı", f"%{(matched/total*100):.1f}" if total > 0 else "-")
    
    if mismatch > 0 and "commission_diff" in df.columns:
        total_diff = df[df["rate_match"] == False]["commission_diff"].sum()
        st.warning(
            f"⚠️ Toplam {mismatch:,} işlemde oran farkı tespit edildi. "
            f"Toplam komisyon farkı: {format_currency_full(total_diff)}"
        )


def main():
    # Veri yükle
    df = load_data()
    
    if df is None or df.empty:
        display_no_data_message()
        return
    
    banks = sorted(df["bank_name"].unique())
    
    if len(banks) == 0:
        display_no_data_message()
        return
    
    # Yüklü banka bilgisi
    st.info(f"📋 **{len(banks)} banka** yüklenmiş: {', '.join(banks)}")
    
    # ── Ay Seçici (valor / settlement_date bazlı) ──
    now = datetime.now()
    date_col = None
    for _c in ["settlement_date", "transaction_date"]:
        if _c in df.columns:
            date_col = _c
            break
    
    available_months = []
    if date_col:
        _dates = pd.to_datetime(df[date_col], errors="coerce").dropna()
        if len(_dates) > 0:
            available_months = sorted(_dates.dt.to_period("M").unique())
    
    current_period = pd.Period(now, freq="M")
    
    # Ay seçme seçeneği
    filter_by_month = st.checkbox("📅 Belirli bir ay seç", value=True)
    
    if filter_by_month and available_months:
        month_labels = [str(m) for m in available_months]
        if str(current_period) in month_labels:
            default_idx = month_labels.index(str(current_period))
        else:
            default_idx = len(month_labels) - 1
        
        selected_label = st.selectbox(
            "📅 Ay Seçimi (Valor / Hesaba Geçiş Tarihine Göre)",
            options=month_labels,
            index=default_idx,
            help="Sadece seçilen aydaki işlemler gösterilir."
        )
        period = pd.Period(selected_label, freq="M")
        sel_year, sel_month = period.year, period.month
        
        # Seçilen aya filtrele
        if date_col:
            _dates = pd.to_datetime(df[date_col], errors="coerce")
            first_day = pd.Timestamp(sel_year, sel_month, 1)
            last_day = pd.Timestamp(sel_year, sel_month, monthrange(sel_year, sel_month)[1], 23, 59, 59)
            df = df[(_dates >= first_day) & (_dates <= last_day)].copy()
        
        if df.empty:
            st.warning("⚠️ Seçilen ayda veri bulunamadı.")
            return
    
    st.markdown("---")
    
    # Genel toplamlar
    display_grand_totals(df)
    
    st.markdown("---")
    
    # Banka bazlı kırılım tablosu
    display_bank_breakdown(df)
    
    st.markdown("---")
    
    # Grafikler
    display_bank_charts(df)
    
    st.markdown("---")
    
    # Aylık konsolide trend
    display_monthly_consolidated(df)
    
    st.markdown("---")
    
    # Komisyon kontrol özeti
    display_commission_control_summary(df)
    
    # Footer
    st.markdown("---")
    st.caption("© 2026 Kariyer.net Finans Ekibi")


if __name__ == "__main__":
    main()
