"""Ziraat Bankası Detay Sayfası.

Ziraat Bankası işlemlerinin detaylı analizi.
Özellikle peşin işlemlerde kart tipi dağılımı.
"""

import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control

st.set_page_config(page_title="Ziraat Bankası Detay", page_icon="🏦", layout="wide")


@st.cache_data
def load_ziraat_data():
    """Load only Ziraat bank data."""
    reader = BankFileReader()
    df = reader.read_all_files()
    
    # Filter for Ziraat
    ziraat_keywords = ['ziraat', 'ZİRAAT']
    mask = df['bank_name'].str.lower().str.contains('ziraat', na=False)
    ziraat_df = df[mask].copy()
    
    if len(ziraat_df) > 0:
        ziraat_df = add_commission_control(ziraat_df)
    
    return ziraat_df


def display_summary_metrics(df: pd.DataFrame):
    """Display summary metrics for Ziraat."""
    st.subheader("📊 Özet Metrikler")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Toplam İşlem", f"{len(df):,}")
    
    with col2:
        total_amount = df['gross_amount'].sum() if 'gross_amount' in df.columns else 0
        st.metric("Toplam Tutar", f"₺{total_amount:,.2f}")
    
    with col3:
        total_commission = df['commission_amount'].sum() if 'commission_amount' in df.columns else 0
        st.metric("Toplam Komisyon", f"₺{total_commission:,.2f}")
    
    with col4:
        avg_rate = df['commission_rate'].mean() * 100 if 'commission_rate' in df.columns and df['commission_rate'].notna().any() else 0
        st.metric("Ortalama Oran", f"%{avg_rate:.2f}")


def display_pesin_card_analysis(df: pd.DataFrame):
    """Display card type breakdown for Peşin transactions."""
    st.subheader("💳 Peşin İşlemler - Kart Tipi Analizi")
    
    # Filter for Peşin (installment = 1 or 0)
    pesin_df = df[df['installment_count'].isin([0, 1])].copy()
    
    if len(pesin_df) == 0:
        st.warning("Peşin işlem bulunamadı.")
        return
    
    st.info(f"Toplam Peşin İşlem: **{len(pesin_df):,}**")
    
    # Check for card_type column
    card_col = None
    possible_cols = ['card_type', 'kart_tipi', 'kart_türü', 'card_brand', 'kart_markası', 
                     'Kart Tipi', 'KART TİPİ', 'Card Type']
    
    for col in possible_cols:
        if col in df.columns:
            card_col = col
            break
    
    # Also check for card-related columns in raw data
    card_related = [c for c in df.columns if any(x in c.lower() for x in ['kart', 'card', 'visa', 'master', 'troy'])]
    
    if card_col:
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart for card types
            card_counts = pesin_df[card_col].value_counts()
            fig = px.pie(
                values=card_counts.values.tolist(),
                names=card_counts.index.tolist(),
                title="Peşin İşlemler - Kart Tipi Dağılımı",
                hole=0.4
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Bar chart for amounts by card type
            if 'gross_amount' in pesin_df.columns:
                card_amounts = pesin_df.groupby(card_col)['gross_amount'].sum().sort_values(ascending=True)
                fig = px.bar(
                    x=card_amounts.values.tolist(),
                    y=card_amounts.index.tolist(),
                    orientation='h',
                    title="Peşin İşlemler - Kart Tipine Göre Tutar",
                    labels={'x': 'Tutar (₺)', 'y': 'Kart Tipi'}
                )
                st.plotly_chart(fig, use_container_width=True)
        
        # Detailed table
        st.markdown("**Kart Tipi Detaylı Tablo:**")
        agg_dict = {}
        if 'gross_amount' in pesin_df.columns:
            agg_dict['gross_amount'] = ['count', 'sum', 'mean']
        if 'commission_amount' in pesin_df.columns:
            agg_dict['commission_amount'] = 'sum'
        if agg_dict:
            card_summary = pesin_df.groupby(card_col).agg(agg_dict).round(2)
            card_summary.columns = ['_'.join(col).strip('_') for col in card_summary.columns.values]
            st.dataframe(card_summary, use_container_width=True)
        
    elif card_related:
        st.info(f"Kart bilgisi içeren sütunlar: {card_related}")
        
        # Try to analyze card-related columns
        for col in card_related[:3]:  # First 3 columns
            if pesin_df[col].notna().sum() > 0:
                st.markdown(f"**{col} Dağılımı:**")
                value_counts = pesin_df[col].value_counts().head(10)
                st.bar_chart(value_counts)
    else:
        st.warning("Kart tipi bilgisi bulunamadı. Mevcut sütunlar aşağıda listelenmiştir.")
        st.write("Mevcut sütunlar:", list(df.columns))
        
        # Show sample of pesin data
        st.markdown("**Peşin İşlem Örnek Verisi:**")
        st.dataframe(pesin_df.head(10), use_container_width=True)


def display_installment_analysis(df: pd.DataFrame):
    """Display installment breakdown analysis."""
    st.subheader("📈 Taksit Analizi")
    
    if 'installment_count' not in df.columns:
        st.warning("Taksit bilgisi bulunamadı.")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Transaction count by installment
        inst_counts = df['installment_count'].value_counts().sort_index()
        fig = px.bar(
            x=inst_counts.index.astype(str).tolist(),
            y=inst_counts.values.tolist(),
            title="Taksit Sayısına Göre İşlem Adedi",
            labels={'x': 'Taksit', 'y': 'İşlem Sayısı'}
        )
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        # Amount by installment
        if 'gross_amount' in df.columns:
            inst_amounts = df.groupby('installment_count')['gross_amount'].sum().sort_index()
            fig = px.bar(
                x=inst_amounts.index.astype(str).tolist(),
                y=inst_amounts.values.tolist(),
                title="Taksit Sayısına Göre Toplam Tutar",
                labels={'x': 'Taksit', 'y': 'Tutar (₺)'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    # Commission rate analysis
    st.markdown("**Taksit - Komisyon Oranı Tablosu:**")
    
    agg_dict = {}
    if 'gross_amount' in df.columns:
        agg_dict['gross_amount'] = ['count', 'sum']
    if 'commission_amount' in df.columns:
        agg_dict['commission_amount'] = 'sum'
    if 'commission_rate' in df.columns:
        agg_dict['commission_rate'] = 'mean'
    if 'expected_rate' in df.columns:
        agg_dict['expected_rate'] = 'first'
    
    if agg_dict:
        inst_summary = df.groupby('installment_count').agg(agg_dict).round(4)
        inst_summary.columns = ['_'.join(col).strip('_') for col in inst_summary.columns.values]
        st.dataframe(inst_summary, use_container_width=True)


def display_monthly_trend(df: pd.DataFrame):
    """Display monthly transaction trend."""
    st.subheader("📅 Aylık Trend")
    
    if 'transaction_date' not in df.columns:
        st.warning("İşlem tarihi bulunamadı.")
        return
    
    # Convert to datetime if needed
    df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
    df['month'] = df['transaction_date'].dt.to_period('M').astype(str)
    
    monthly = df.groupby('month').agg({
        'gross_amount': ['count', 'sum'] if 'gross_amount' in df.columns else {},
        'commission_amount': 'sum' if 'commission_amount' in df.columns else {}
    }).round(2)
    if len(monthly.columns) > 0:
        monthly.columns = ['_'.join(col).strip('_') for col in monthly.columns.values]
    monthly = monthly.sort_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
        if 'gross_amount_sum' in monthly.columns:
            fig = px.line(
                x=monthly.index.tolist(),
                y=monthly['gross_amount_sum'].tolist(),
                title="Aylık Tutar Trendi",
                labels={'x': 'Ay', 'y': 'Tutar (₺)'},
                markers=True
            )
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'gross_amount_count' in monthly.columns:
            fig = px.bar(
                x=monthly.index.tolist(),
                y=monthly['gross_amount_count'].tolist(),
                title="Aylık İşlem Sayısı",
                labels={'x': 'Ay', 'y': 'İşlem Sayısı'}
            )
            st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(monthly, use_container_width=True)


def display_raw_data(df: pd.DataFrame):
    """Display raw data with filters."""
    st.subheader("📋 Ham Veri")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'installment_count' in df.columns:
            inst_options = ['Tümü'] + sorted(df['installment_count'].dropna().unique().tolist())
            selected_inst = st.selectbox("Taksit Filtresi", inst_options)
    
    with col2:
        if 'transaction_date' in df.columns:
            df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
            min_date = df['transaction_date'].min()
            max_date = df['transaction_date'].max()
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.date_input("Tarih Aralığı", [min_date, max_date])
    
    with col3:
        show_anomalies = st.checkbox("Sadece Anomalileri Göster", value=False)
    
    # Apply filters
    filtered_df = df.copy()
    
    if 'selected_inst' in dir() and selected_inst != 'Tümü':
        filtered_df = filtered_df[filtered_df['installment_count'] == selected_inst]
    
    if show_anomalies and 'is_anomaly' in filtered_df.columns:
        filtered_df = filtered_df[filtered_df['is_anomaly'] == True]
    
    st.write(f"Gösterilen kayıt: {len(filtered_df):,}")
    
    # Download button
    csv = filtered_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 CSV İndir",
        data=csv,
        file_name="ziraat_data.csv",
        mime="text/csv"
    )
    
    st.dataframe(filtered_df, use_container_width=True, height=400)


def main():
    st.title("🏦 Ziraat Bankası Detay Analizi")
    st.markdown("---")
    
    # Load data
    with st.spinner("Ziraat verisi yükleniyor..."):
        df = load_ziraat_data()
    
    if len(df) == 0:
        st.error("Ziraat Bankası verisi bulunamadı!")
        st.info("data/raw/ klasörüne Ziraat Bankası dosyası ekleyin.")
        return
    
    st.success(f"✅ {len(df):,} Ziraat işlemi yüklendi")
    
    # Summary metrics
    display_summary_metrics(df)
    
    st.markdown("---")
    
    # Tabs for different analyses
    tab1, tab2, tab3, tab4 = st.tabs([
        "💳 Peşin Kart Analizi",
        "📈 Taksit Analizi", 
        "📅 Aylık Trend",
        "📋 Ham Veri"
    ])
    
    with tab1:
        display_pesin_card_analysis(df)
    
    with tab2:
        display_installment_analysis(df)
    
    with tab3:
        display_monthly_trend(df)
    
    with tab4:
        display_raw_data(df)


if __name__ == "__main__":
    main()
