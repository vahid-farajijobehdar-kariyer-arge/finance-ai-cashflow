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

# Import auth module
sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password


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


def detect_card_issuer_bank(card_info: str) -> str:
    """Kart bilgisinden kartı veren bankayı tespit et.
    
    Args:
        card_info: Kart tipi, kart numarası veya kart açıklaması
        
    Returns:
        Banka adı veya 'Ziraat' (varsayılan)
    """
    if pd.isna(card_info):
        return "Ziraat (Varsayılan)"
    
    card_str = str(card_info).upper()
    
    # Banka tanımlama kuralları
    bank_patterns = {
        "Akbank": ["AKBANK", "AXS", "AXESS"],
        "Garanti": ["GARANTİ", "GARANTI", "BONUS", "MILES"],
        "Yapı Kredi": ["YAPI KREDİ", "YAPI KREDI", "YKB", "WORLD"],
        "İş Bankası": ["İŞ BANK", "IS BANK", "ISBANK", "MAXIMUM"],
        "Halkbank": ["HALK", "PARAF"],
        "Vakıfbank": ["VAKIF", "WORLD"],
        "QNB": ["QNB", "FİNANS", "FINANS", "CARDFINANS"],
        "Denizbank": ["DENİZ", "DENIZ", "BONUS"],
        "TEB": ["TEB", "ENPARA"],
        "ING": ["ING", "TURUNCU"],
        "HSBC": ["HSBC"],
        "Ziraat": ["ZİRAAT", "ZIRAAT", "BANKKART"],
    }
    
    for bank, patterns in bank_patterns.items():
        for pattern in patterns:
            if pattern in card_str:
                return bank
    
    # Kart numarasından BIN analizi (ilk 6 hane)
    # Bazı yaygın BIN aralıkları
    if card_str.replace(" ", "").isdigit() and len(card_str.replace(" ", "")) >= 6:
        bin_code = card_str.replace(" ", "")[:6]
        # Bu genellikle kart numarası maskeli gelir, BIN kullanılamaz
        pass
    
    return "Ziraat (Varsayılan)"


def display_pesin_card_analysis(df: pd.DataFrame):
    """Peşin işlemlerde kart tipi ve kartı veren banka analizi."""
    st.subheader("💳 Peşin İşlemler - Kart Analizi")
    
    # Peşin işlemleri filtrele (taksit = 1 veya 0)
    pesin_df = df[df['installment_count'].isin([0, 1])].copy()
    
    if len(pesin_df) == 0:
        st.warning("Peşin işlem bulunamadı.")
        return
    
    # Özet metrikler
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Peşin İşlem Sayısı", f"{len(pesin_df):,}")
    with col2:
        pesin_toplam = pesin_df['gross_amount'].sum() if 'gross_amount' in pesin_df.columns else 0
        st.metric("Peşin Toplam Tutar", f"₺{pesin_toplam:,.2f}")
    with col3:
        pesin_komisyon = pesin_df['commission_amount'].sum() if 'commission_amount' in pesin_df.columns else 0
        st.metric("Peşin Komisyon", f"₺{pesin_komisyon:,.2f}")
    
    st.markdown("---")
    
    # Kart sütunlarını bul
    card_columns = []
    for col in pesin_df.columns:
        col_lower = col.lower()
        if any(x in col_lower for x in ['kart', 'card', 'brand', 'issuer', 'bin']):
            card_columns.append(col)
    
    # Kartı veren banka analizi
    st.subheader("🏦 Kartı Veren Banka Analizi")
    st.markdown("""
    **Açıklama:** Ziraat POS'undan geçen işlemlerde hangi bankaların kartları kullanılıyor?
    Varsayılan olarak Ziraat kabul edilir, diğer bankalar kart bilgisinden tespit edilir.
    """)
    
    # Kart bilgisinden banka tespit et
    if card_columns:
        # En uygun kart sütununu seç
        card_col = card_columns[0]
        for col in card_columns:
            if 'tipi' in col.lower() or 'type' in col.lower():
                card_col = col
                break
        
        pesin_df['kart_bankasi'] = pesin_df[card_col].apply(detect_card_issuer_bank)
        
        st.info(f"Kullanılan sütun: **{card_col}**")
    else:
        # Kart sütunu yoksa tüm işlemleri Ziraat say
        st.warning("Kart tipi sütunu bulunamadı. Tüm işlemler Ziraat kartı olarak varsayılıyor.")
        pesin_df['kart_bankasi'] = "Ziraat (Varsayılan)"
    
    # Banka bazlı özet
    bank_summary = pesin_df.groupby('kart_bankasi').agg({
        'gross_amount': ['count', 'sum'],
        'commission_amount': 'sum'
    }).round(2)
    bank_summary.columns = ['İşlem Sayısı', 'Toplam Tutar (₺)', 'Komisyon (₺)']
    bank_summary = bank_summary.sort_values('Toplam Tutar (₺)', ascending=False)
    
    # Yüzde hesapla
    bank_summary['Tutar %'] = (bank_summary['Toplam Tutar (₺)'] / bank_summary['Toplam Tutar (₺)'].sum() * 100).round(1)
    bank_summary['İşlem %'] = (bank_summary['İşlem Sayısı'] / bank_summary['İşlem Sayısı'].sum() * 100).round(1)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pasta grafik - tutar bazlı
        fig = px.pie(
            values=bank_summary['Toplam Tutar (₺)'].values,
            names=bank_summary.index.tolist(),
            title="Kartı Veren Banka - Tutar Dağılımı",
            hole=0.4
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True, key="pie_bank_amount")
    
    with col2:
        # Bar grafik - işlem sayısı
        chart_df = pd.DataFrame({
            'Banka': bank_summary.index,
            'İşlem Sayısı': bank_summary['İşlem Sayısı'].values
        })
        fig = px.bar(
            chart_df,
            x='Banka',
            y='İşlem Sayısı',
            title="Kartı Veren Banka - İşlem Sayısı",
            color='İşlem Sayısı',
            color_continuous_scale='Blues'
        )
        st.plotly_chart(fig, use_container_width=True, key="bar_bank_count")
    
    # Detaylı tablo
    st.markdown("### 📋 Detaylı Tablo")
    
    # Formatla
    display_df = bank_summary.reset_index()
    display_df.columns = ['Kartı Veren Banka', 'İşlem Sayısı', 'Toplam Tutar (₺)', 'Komisyon (₺)', 'Tutar %', 'İşlem %']
    
    st.dataframe(
        display_df.style.format({
            'Toplam Tutar (₺)': '₺{:,.2f}',
            'Komisyon (₺)': '₺{:,.2f}',
            'Tutar %': '%{:.1f}',
            'İşlem %': '%{:.1f}',
            'İşlem Sayısı': '{:,}'
        }),
        use_container_width=True,
        hide_index=True
    )
    
    # Ziraat dışı kartlar uyarısı
    non_ziraat = bank_summary[~bank_summary.index.str.contains('Ziraat', case=False)]
    if len(non_ziraat) > 0:
        non_ziraat_total = non_ziraat['Toplam Tutar (₺)'].sum()
        non_ziraat_pct = non_ziraat['Tutar %'].sum()
        st.warning(f"""
        ⚠️ **Diğer Banka Kartları Analizi:**
        
        Ziraat dışı banka kartlarıyla yapılan peşin işlemler:
        - **Tutar:** ₺{non_ziraat_total:,.2f} ({non_ziraat_pct:.1f}%)
        - **Banka Sayısı:** {len(non_ziraat)}
        
        Bu işlemlerde farklı komisyon oranları uygulanabilir.
        """)
    
    st.markdown("---")
    
    # Ham kart verileri (genişletilebilir)
    with st.expander("🔍 Ham Kart Verileri"):
        if card_columns:
            st.markdown(f"**Bulunan kart sütunları:** {card_columns}")
            for col in card_columns[:3]:
                st.markdown(f"**{col} değerleri:**")
                value_counts = pesin_df[col].value_counts().head(15)
                st.dataframe(value_counts, use_container_width=True)


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
    st.set_page_config(page_title="Ziraat Bankası Detay", page_icon="🏦", layout="wide")
    
    # Require authentication
    if not check_password():
        return
    
    st.title("🏦 Ziraat Bankası Detay Analizi")
    st.markdown("---")
    
    # Load data
    with st.spinner("Ziraat verisi yükleniyor..."):
        df = load_ziraat_data()
    
    if len(df) == 0:
        st.error("Ziraat Bankası verisi bulunamadı!")
        st.info("Lütfen Dosya Yükle sayfasından Ziraat dosyası yükleyin.")
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
