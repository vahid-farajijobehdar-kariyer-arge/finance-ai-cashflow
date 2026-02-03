"""İş Bankası Detay Sayfası."""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control

# Import auth module
sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password


@st.cache_data
def load_isbank_data():
    """İş Bankası verilerini yükle."""
    reader = BankFileReader()
    df = reader.read_all_files()
    mask = df['bank_name'].str.lower().str.contains('iş|is bank|isbank|işbank', na=False, regex=True)
    isbank_df = df[mask].copy()
    if len(isbank_df) > 0:
        isbank_df = add_commission_control(isbank_df)
    return isbank_df


def display_metrics(df: pd.DataFrame):
    """Özet metrikleri göster."""
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Toplam İşlem", f"{len(df):,}")
    with col2:
        total = df['gross_amount'].sum() if 'gross_amount' in df.columns else 0
        st.metric("Toplam Çekilen Tutar", f"₺{total:,.2f}")
    with col3:
        comm = df['commission_amount'].sum() if 'commission_amount' in df.columns else 0
        st.metric("Toplam Komisyon", f"₺{comm:,.2f}")
    with col4:
        net = df['net_amount'].sum() if 'net_amount' in df.columns else 0
        st.metric("Net Tutar", f"₺{net:,.2f}")


def display_installment_chart(df: pd.DataFrame):
    """Taksit dağılım grafiği."""
    st.subheader("📈 Taksit Dağılımı")
    if 'installment_count' not in df.columns:
        st.warning("Taksit bilgisi bulunamadı.")
        return
    
    col1, col2 = st.columns(2)
    with col1:
        counts = df['installment_count'].value_counts().sort_index()
        chart_df = pd.DataFrame({'Taksit': counts.index.astype(str), 'Adet': counts.values})
        fig = px.bar(chart_df, x='Taksit', y='Adet', title="Taksit - İşlem Sayısı")
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'gross_amount' in df.columns:
            amounts = df.groupby('installment_count')['gross_amount'].sum().sort_index()
            fig = px.pie(values=amounts.values.tolist(), names=amounts.index.astype(str).tolist(),
                         title="Taksit - Tutar Dağılımı", hole=0.4)
            st.plotly_chart(fig, use_container_width=True)


def display_commission_analysis(df: pd.DataFrame):
    """Komisyon analizi."""
    st.subheader("💰 Komisyon Analizi")
    
    if 'installment_count' not in df.columns:
        st.warning("Taksit bilgisi bulunamadı.")
        return
    
    agg_dict = {'gross_amount': ['count', 'sum']}
    if 'commission_amount' in df.columns:
        agg_dict['commission_amount'] = 'sum'
    if 'commission_rate' in df.columns:
        agg_dict['commission_rate'] = 'mean'
    if 'expected_rate' in df.columns:
        agg_dict['expected_rate'] = 'first'
    
    summary = df.groupby('installment_count').agg(agg_dict).round(4)
    summary.columns = ['_'.join(col).strip('_') for col in summary.columns.values]
    st.dataframe(summary, use_container_width=True)


def display_data(df: pd.DataFrame):
    """Ham veri görüntüle."""
    st.subheader("📋 Veriler")
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 CSV İndir", csv, "isbank_data.csv", "text/csv")
    st.dataframe(df, use_container_width=True, height=400)


def main():
    st.set_page_config(page_title="İş Bankası Detay", page_icon="🏦", layout="wide")
    
    # Kimlik doğrulama
    if not check_password():
        return
    
    st.title("🏦 İş Bankası Detay Analizi")
    st.markdown("---")
    
    with st.spinner("Yükleniyor..."):
        df = load_isbank_data()
    
    if len(df) == 0:
        st.error("İş Bankası verisi bulunamadı!")
        st.info("Lütfen Dosya Yükle sayfasından İş Bankası dosyası yükleyin.")
        return
    
    st.success(f"✅ {len(df):,} işlem yüklendi")
    
    display_metrics(df)
    st.markdown("---")
    
    tab1, tab2, tab3 = st.tabs(["📈 Taksit", "💰 Komisyon", "📋 Veri"])
    
    with tab1:
        display_installment_chart(df)
    with tab2:
        display_commission_analysis(df)
    with tab3:
        display_data(df)


if __name__ == "__main__":
    main()
