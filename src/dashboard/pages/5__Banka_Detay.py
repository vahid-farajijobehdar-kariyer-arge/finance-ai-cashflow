"""
🏦 Banka Detay - Banka bazlı komisyon analizi

Tüm bankaların detaylı analizi tek sayfada.
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


st.set_page_config(
    page_title="Banka Detay - POS Komisyon",
    page_icon="🏦",
    layout="wide"
)

# Authentication
if not check_password():
    st.stop()

st.title("🏦 Banka Detay Analizi")
st.markdown("**Banka bazlı detaylı komisyon analizi**")
st.markdown("---")


@st.cache_data
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


def display_bank_metrics(bank_df: pd.DataFrame, bank_name: str):
    """Banka metriklerini göster."""
    # Grand total: tüm değerler dahil (pozitif + negatif)
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💰 Toplam Tutar", f"₺{bank_df['gross_amount'].sum():,.2f}")
    with col2:
        st.metric("💳 Komisyon", f"₺{bank_df['commission_amount'].sum():,.2f}")
    with col3:
        # NET = Brüt - Komisyon (her zaman direkt hesapla)
        net_val = bank_df["gross_amount"].sum() - bank_df["commission_amount"].sum()
        st.metric("📈 Net Tutar", f"₺{net_val:,.2f}")
    with col4:
        st.metric("📊 İşlem Sayısı", f"{len(bank_df):,}")


def display_installment_breakdown(bank_df: pd.DataFrame):
    """Taksit dağılımını göster."""
    st.subheader("💳 Taksit Dağılımı")
    
    if "installment_count" not in bank_df.columns:
        st.info("Taksit bilgisi mevcut değil.")
        return
    
    bank_df = bank_df.copy()
    bank_df["Taksit"] = bank_df["installment_count"].fillna(1).apply(
        lambda x: "Peşin" if x in (0, 1) else f"{int(x)} Taksit"
    )
    
    taksit_summary = bank_df.groupby("Taksit").agg({
        "gross_amount": ["sum", "count"],
        "commission_amount": "sum"
    }).round(2)
    taksit_summary.columns = ["Toplam Tutar", "İşlem Sayısı", "Komisyon"]
    taksit_summary = taksit_summary.reset_index()
    taksit_summary["Oran"] = (taksit_summary["Komisyon"] / taksit_summary["Toplam Tutar"] * 100).round(2)
    
    # Sıralama
    order = ["Peşin"] + [f"{i} Taksit" for i in range(2, 13)]
    taksit_summary["Taksit"] = pd.Categorical(taksit_summary["Taksit"], categories=order, ordered=True)
    taksit_summary = taksit_summary.sort_values("Taksit")
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig = px.bar(
            taksit_summary,
            x="Taksit",
            y="Toplam Tutar",
            title="Taksit Bazlı Tutar Dağılımı",
            color="Toplam Tutar",
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig, width="stretch")
    
    with col2:
        fig = px.pie(
            taksit_summary,
            values="Toplam Tutar",
            names="Taksit",
            title="Taksit Yüzde Dağılımı"
        )
        st.plotly_chart(fig, width="stretch")
    
    st.dataframe(
        taksit_summary.style.format({
            "Toplam Tutar": "₺{:,.2f}",
            "Komisyon": "₺{:,.2f}",
            "Oran": "%{:.2f}",
            "İşlem Sayısı": "{:,.0f}"
        }),
        width="stretch",
        hide_index=True
    )


def display_monthly_trend(bank_df: pd.DataFrame):
    """Aylık trend göster."""
    st.subheader("📅 Aylık Trend")
    
    if "transaction_date" not in bank_df.columns:
        st.info("Tarih bilgisi mevcut değil.")
        return
    
    bank_df = bank_df.copy()
    bank_df["Tarih"] = pd.to_datetime(bank_df["transaction_date"], errors="coerce")
    bank_df["Ay"] = bank_df["Tarih"].dt.to_period("M").astype(str)
    
    monthly = bank_df.groupby("Ay").agg({
        "gross_amount": "sum",
        "commission_amount": "sum"
    }).reset_index()
    monthly.columns = ["Ay", "Toplam Tutar", "Komisyon"]
    monthly = monthly.sort_values("Ay")
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=monthly["Ay"], y=monthly["Toplam Tutar"], name="Toplam Tutar", marker_color="#1f77b4"))
    fig.add_trace(go.Bar(x=monthly["Ay"], y=monthly["Komisyon"], name="Komisyon", marker_color="#ff7f0e"))
    fig.update_layout(title="Aylık Tutar ve Komisyon", barmode="group")
    st.plotly_chart(fig, width="stretch")


def display_commission_control(bank_df: pd.DataFrame):
    """Komisyon kontrolü göster."""
    st.subheader("🔍 Komisyon Kontrolü")
    
    if "rate_match" not in bank_df.columns:
        st.info("Komisyon kontrol verisi mevcut değil.")
        return
    
    matched = bank_df["rate_match"].sum()
    total = len(bank_df)
    mismatch = total - matched
    
    col1, col2, col3 = st.columns(3)
    col1.metric("✅ Eşleşen", f"{matched:,}")
    col2.metric("❌ Eşleşmeyen", f"{mismatch:,}")
    col3.metric("📊 Eşleşme Oranı", f"%{(matched/total*100):.1f}" if total > 0 else "-")
    
    if mismatch > 0 and "commission_diff" in bank_df.columns:
        st.warning(f"⚠️ {mismatch:,} işlemde oran farkı tespit edildi.")
        diff_df = bank_df[bank_df["rate_match"] == False][["transaction_date", "gross_amount", "commission_rate", "rate_expected", "commission_diff"]].head(10)
        if not diff_df.empty:
            st.dataframe(diff_df, width="stretch", hide_index=True)


def main():
    # Veri yükle
    df = load_data()
    
    if df is None or df.empty:
        display_no_data_message()
        return
    
    # Banka seçimi
    banks = sorted(df["bank_name"].unique())
    
    if len(banks) == 0:
        display_no_data_message()
        return
    
    selected_bank = st.selectbox(
        "🏦 Banka Seçin",
        options=banks,
        index=0
    )
    
    # Seçilen banka verisini filtrele
    bank_df = df[df["bank_name"] == selected_bank].copy()
    
    # ── Ay Seçici (valor / settlement_date bazlı) ──
    now = datetime.now()
    date_col = None
    for _c in ["settlement_date", "transaction_date"]:
        if _c in bank_df.columns:
            date_col = _c
            break
    
    available_months = []
    if date_col:
        _dates = pd.to_datetime(bank_df[date_col], errors="coerce").dropna()
        if len(_dates) > 0:
            available_months = sorted(_dates.dt.to_period("M").unique())
    
    current_period = pd.Period(now, freq="M")
    if available_months:
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
    else:
        sel_year, sel_month = now.year, now.month
    
    # Sadece seçilen aya ait verileri tut
    if date_col:
        _dates = pd.to_datetime(bank_df[date_col], errors="coerce")
        first_day = pd.Timestamp(sel_year, sel_month, 1)
        last_day = pd.Timestamp(sel_year, sel_month, monthrange(sel_year, sel_month)[1], 23, 59, 59)
        bank_df = bank_df[(_dates >= first_day) & (_dates <= last_day)].copy()
    
    if bank_df.empty:
        st.warning(f"⚠️ {selected_bank} için seçilen ayda veri bulunamadı.")
        return
    
    st.markdown(f"### {selected_bank}")
    st.markdown("---")
    
    # Metrikler
    display_bank_metrics(bank_df, selected_bank)
    
    st.markdown("---")
    
    # Sekmeler
    tab1, tab2, tab3 = st.tabs(["💳 Taksit Analizi", "📅 Aylık Trend", "🔍 Komisyon Kontrolü"])
    
    with tab1:
        display_installment_breakdown(bank_df)
    
    with tab2:
        display_monthly_trend(bank_df)
    
    with tab3:
        display_commission_control(bank_df)


if __name__ == "__main__":
    main()
