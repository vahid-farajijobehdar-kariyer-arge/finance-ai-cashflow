"""
📊 Rapor Oluşturucu

Komisyon analizi raporlarını Excel ve CSV formatında dışa aktarın.
"""

import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO

import pandas as pd
import streamlit as st

# Add project root to path for imports
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control, COMMISSION_RATES
from processing.calculator import filter_successful_transactions, calculate_ground_totals

# Data paths
RAW_PATH = PROJECT_ROOT.parent / "data" / "raw"
OUTPUT_PATH = PROJECT_ROOT.parent / "data" / "output"

st.set_page_config(page_title="Rapor Oluştur", page_icon="📊", layout="wide")


@st.cache_data
def load_data():
    """Load and process all data."""
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
    
    return df


def create_summary_report(df: pd.DataFrame) -> pd.DataFrame:
    """Create summary report by bank."""
    summary = df.groupby("bank_name").agg({
        "gross_amount": ["sum", "count", "mean"],
        "commission_amount": "sum",
        "net_amount": "sum",
        "commission_rate": "mean"
    }).round(2)
    
    summary.columns = [
        "Toplam Tutar", "İşlem Sayısı", "Ortalama İşlem",
        "Toplam Komisyon", "Toplam Net", "Ortalama Oran"
    ]
    summary = summary.reset_index()
    summary = summary.rename(columns={"bank_name": "Banka"})
    
    # Add totals row
    totals = pd.DataFrame([{
        "Banka": "TOPLAM",
        "Toplam Tutar": summary["Toplam Tutar"].sum(),
        "İşlem Sayısı": summary["İşlem Sayısı"].sum(),
        "Ortalama İşlem": summary["Toplam Tutar"].sum() / summary["İşlem Sayısı"].sum(),
        "Toplam Komisyon": summary["Toplam Komisyon"].sum(),
        "Toplam Net": summary["Toplam Net"].sum(),
        "Ortalama Oran": summary["Toplam Komisyon"].sum() / summary["Toplam Tutar"].sum()
    }])
    
    summary = pd.concat([summary, totals], ignore_index=True)
    
    return summary


def create_installment_report(df: pd.DataFrame) -> pd.DataFrame:
    """Create report by installment count."""
    # Create installment label
    df = df.copy()
    df["Taksit"] = df["installment_count"].apply(
        lambda x: "Peşin" if pd.isna(x) or x == 1 else str(int(x))
    )
    
    summary = df.groupby("Taksit").agg({
        "gross_amount": ["sum", "count"],
        "commission_amount": "sum",
        "commission_rate": "mean"
    }).round(4)
    
    summary.columns = ["Toplam Tutar", "İşlem Sayısı", "Toplam Komisyon", "Ortalama Oran"]
    summary = summary.reset_index()
    
    # Sort by installment
    order = ["Peşin"] + [str(i) for i in range(2, 13)]
    summary["Taksit"] = pd.Categorical(summary["Taksit"], categories=order, ordered=True)
    summary = summary.sort_values("Taksit")
    
    return summary


def create_monthly_report(df: pd.DataFrame) -> pd.DataFrame:
    """Create monthly report."""
    df = df.copy()
    df["Tarih"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["Ay"] = df["Tarih"].dt.strftime("%Y-%m")
    
    summary = df.groupby("Ay").agg({
        "gross_amount": ["sum", "count"],
        "commission_amount": "sum",
        "net_amount": "sum"
    }).round(2)
    
    summary.columns = ["Toplam Tutar", "İşlem Sayısı", "Toplam Komisyon", "Toplam Net"]
    summary = summary.reset_index()
    summary = summary.sort_values("Ay")
    
    return summary


def create_bank_month_pivot(df: pd.DataFrame) -> pd.DataFrame:
    """Create pivot table: Bank x Month."""
    df = df.copy()
    df["Tarih"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["Ay"] = df["Tarih"].dt.strftime("%Y-%m")
    
    pivot = pd.pivot_table(
        df,
        values="gross_amount",
        index="bank_name",
        columns="Ay",
        aggfunc="sum",
        fill_value=0,
        margins=True,
        margins_name="TOPLAM"
    )
    
    return pivot


def create_rates_reference(rates: dict) -> pd.DataFrame:
    """Create commission rates reference table."""
    data = []
    for bank, bank_rates in rates.items():
        row = {"Banka": bank}
        for taksit, rate in bank_rates.items():
            row[f"Taksit {taksit}"] = rate
        data.append(row)
    
    df = pd.DataFrame(data)
    return df


def create_excel_report(df: pd.DataFrame) -> BytesIO:
    """Create comprehensive Excel report with multiple sheets."""
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Summary by Bank
        summary = create_summary_report(df)
        summary.to_excel(writer, sheet_name="Banka Özet", index=False)
        
        # Sheet 2: By Installment
        installment = create_installment_report(df)
        installment.to_excel(writer, sheet_name="Taksit Dağılım", index=False)
        
        # Sheet 3: Monthly Summary
        monthly = create_monthly_report(df)
        monthly.to_excel(writer, sheet_name="Aylık Özet", index=False)
        
        # Sheet 4: Bank x Month Pivot
        pivot = create_bank_month_pivot(df)
        pivot.to_excel(writer, sheet_name="Banka-Ay Pivot")
        
        # Sheet 5: Commission Rates Reference
        rates = create_rates_reference(COMMISSION_RATES)
        rates.to_excel(writer, sheet_name="Komisyon Oranları", index=False)
        
        # Sheet 6: Raw Data (sample)
        display_cols = [
            "transaction_date", "bank_name", "gross_amount", 
            "commission_amount", "net_amount", "installment_count",
            "commission_rate", "rate_expected", "rate_match"
        ]
        available_cols = [c for c in display_cols if c in df.columns]
        df[available_cols].to_excel(writer, sheet_name="Ham Veri", index=False)
    
    output.seek(0)
    return output


def display_report_preview(df: pd.DataFrame):
    """Display report previews."""
    st.subheader("📋 Rapor Önizleme")
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "🏦 Banka Özet",
        "💳 Taksit Dağılım",
        "📅 Aylık Özet",
        "📊 Banka-Ay Pivot"
    ])
    
    with tab1:
        summary = create_summary_report(df)
        st.dataframe(
            summary.style.format({
                "Toplam Tutar": "₺{:,.2f}",
                "Ortalama İşlem": "₺{:,.2f}",
                "Toplam Komisyon": "₺{:,.2f}",
                "Toplam Net": "₺{:,.2f}",
                "Ortalama Oran": "{:.2%}",
                "İşlem Sayısı": "{:,.0f}"
            }),
            hide_index=True,
            use_container_width=True
        )
    
    with tab2:
        installment = create_installment_report(df)
        st.dataframe(
            installment.style.format({
                "Toplam Tutar": "₺{:,.2f}",
                "Toplam Komisyon": "₺{:,.2f}",
                "Ortalama Oran": "{:.2%}",
                "İşlem Sayısı": "{:,.0f}"
            }),
            hide_index=True,
            use_container_width=True
        )
    
    with tab3:
        monthly = create_monthly_report(df)
        st.dataframe(
            monthly.style.format({
                "Toplam Tutar": "₺{:,.2f}",
                "Toplam Komisyon": "₺{:,.2f}",
                "Toplam Net": "₺{:,.2f}",
                "İşlem Sayısı": "{:,.0f}"
            }),
            hide_index=True,
            use_container_width=True
        )
    
    with tab4:
        pivot = create_bank_month_pivot(df)
        st.dataframe(
            pivot.style.format("₺{:,.2f}"),
            use_container_width=True
        )


def display_export_options(df: pd.DataFrame):
    """Display export options."""
    st.subheader("📥 Dışa Aktar")
    
    col1, col2, col3 = st.columns(3)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    with col1:
        st.markdown("#### 📗 Excel Raporu")
        st.markdown("Tüm analizleri içeren kapsamlı Excel dosyası.")
        
        excel_data = create_excel_report(df)
        st.download_button(
            label="📥 Excel İndir",
            data=excel_data,
            file_name=f"komisyon_raporu_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_excel"
        )
    
    with col2:
        st.markdown("#### 📄 CSV Özet")
        st.markdown("Banka bazlı özet rapor.")
        
        summary = create_summary_report(df)
        csv_summary = summary.to_csv(index=False)
        st.download_button(
            label="📥 CSV İndir (Özet)",
            data=csv_summary,
            file_name=f"banka_ozet_{timestamp}.csv",
            mime="text/csv",
            key="download_csv_summary"
        )
    
    with col3:
        st.markdown("#### 📋 Ham Veri")
        st.markdown("Filtrelenmiş tüm işlemler.")
        
        csv_raw = df.to_csv(index=False)
        st.download_button(
            label="📥 CSV İndir (Ham)",
            data=csv_raw,
            file_name=f"islemler_{timestamp}.csv",
            mime="text/csv",
            key="download_csv_raw"
        )
    
    st.markdown("---")
    
    # Additional exports
    st.markdown("### 📊 Ek Raporlar")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        monthly = create_monthly_report(df)
        csv_monthly = monthly.to_csv(index=False)
        st.download_button(
            "📅 Aylık Rapor",
            csv_monthly,
            f"aylik_ozet_{timestamp}.csv",
            "text/csv",
            key="download_monthly"
        )
    
    with col2:
        installment = create_installment_report(df)
        csv_installment = installment.to_csv(index=False)
        st.download_button(
            "💳 Taksit Rapor",
            csv_installment,
            f"taksit_dagilim_{timestamp}.csv",
            "text/csv",
            key="download_installment"
        )
    
    with col3:
        pivot = create_bank_month_pivot(df)
        csv_pivot = pivot.to_csv()
        st.download_button(
            "📊 Pivot Tablo",
            csv_pivot,
            f"banka_ay_pivot_{timestamp}.csv",
            "text/csv",
            key="download_pivot"
        )
    
    with col4:
        rates = create_rates_reference(COMMISSION_RATES)
        csv_rates = rates.to_csv(index=False)
        st.download_button(
            "📋 Oran Tablosu",
            csv_rates,
            f"komisyon_oranlari_{timestamp}.csv",
            "text/csv",
            key="download_rates"
        )


def display_filter_and_export(df: pd.DataFrame):
    """Display filtered export options."""
    st.subheader("🎯 Filtreli Dışa Aktarım")
    
    st.markdown("Belirli kriterlere göre filtrelenmiş veri indirin.")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        banks = ["Tümü"] + sorted(df["bank_name"].dropna().unique().tolist())
        selected_bank = st.selectbox("Banka", banks, key="filter_bank")
    
    with col2:
        if "transaction_date" in df.columns:
            df["_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
            min_date = df["_date"].min()
            max_date = df["_date"].max()
            
            if pd.notna(min_date) and pd.notna(max_date):
                date_range = st.date_input(
                    "Tarih Aralığı",
                    value=(min_date.date(), max_date.date()),
                    min_value=min_date.date(),
                    max_value=max_date.date(),
                    key="filter_date"
                )
            else:
                date_range = None
        else:
            date_range = None
    
    with col3:
        installments = ["Tümü", "Peşin", "Taksitli"]
        selected_installment = st.selectbox("Ödeme Tipi", installments, key="filter_installment")
    
    # Apply filters
    filtered = df.copy()
    
    if selected_bank != "Tümü":
        filtered = filtered[filtered["bank_name"] == selected_bank]
    
    if date_range and len(date_range) == 2:
        start_date, end_date = date_range
        filtered = filtered[
            (filtered["_date"].dt.date >= start_date) & 
            (filtered["_date"].dt.date <= end_date)
        ]
    
    if selected_installment == "Peşin":
        filtered = filtered[filtered["installment_count"].fillna(1) == 1]
    elif selected_installment == "Taksitli":
        filtered = filtered[filtered["installment_count"].fillna(1) > 1]
    
    # Show filtered stats
    st.markdown(f"**Filtreli Sonuç:** {len(filtered):,} işlem")
    
    if len(filtered) > 0:
        col1, col2, col3 = st.columns(3)
        col1.metric("Toplam Tutar", f"₺{filtered['gross_amount'].sum():,.2f}")
        col2.metric("Toplam Komisyon", f"₺{filtered['commission_amount'].sum():,.2f}")
        col3.metric("Toplam Net", f"₺{filtered['net_amount'].sum():,.2f}")
        
        # Export filtered
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_filtered = filtered.to_csv(index=False)
        st.download_button(
            "📥 Filtrelenmiş Veriyi İndir",
            csv_filtered,
            f"filtreli_veri_{timestamp}.csv",
            "text/csv",
            key="download_filtered"
        )
    else:
        st.warning("Seçilen filtrelere uygun veri bulunamadı.")


def main():
    st.title("📊 Rapor Oluşturucu")
    st.markdown("Komisyon analizi raporlarını oluşturun ve dışa aktarın.")
    st.markdown("---")
    
    # Load data
    df = load_data()
    
    if df is None or df.empty:
        st.error(f"""
        ❌ Veri bulunamadı.
        
        Beklenen dizin: `{RAW_PATH}`
        
        Önce '📤 Dosya Yükle' sayfasından dosya yükleyin.
        """)
        return
    
    # Show data summary
    st.success(f"✅ {len(df):,} işlem yüklendi.")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Toplam Tutar", f"₺{df['gross_amount'].sum():,.2f}")
    col2.metric("Toplam Komisyon", f"₺{df['commission_amount'].sum():,.2f}")
    col3.metric("Toplam Net", f"₺{df['net_amount'].sum():,.2f}")
    col4.metric("Banka Sayısı", df["bank_name"].nunique())
    
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3 = st.tabs([
        "📋 Önizleme",
        "📥 Dışa Aktar",
        "🎯 Filtreli Export"
    ])
    
    with tab1:
        display_report_preview(df)
    
    with tab2:
        display_export_options(df)
    
    with tab3:
        display_filter_and_export(df)


if __name__ == "__main__":
    main()
