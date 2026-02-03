"""
📊 Detay Rapor - Aylık banka komisyon raporu (Excel formatında)

Excel formatına uygun detaylı aylık rapor:
- Toplam Çekim Tutarı
- Toplam Ödenen Komisyon
- Tek Çekim Tutarı
- Kendi Bankasının Komisyonu
- Net Gelir
"""

import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
from io import BytesIO

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control, get_commission_rates

sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password

# Data path
RAW_PATH = PROJECT_ROOT.parent / "data" / "raw"

# Ay isimleri Türkçe
AY_ISIMLERI = {
    1: "OCAK", 2: "ŞUBAT", 3: "MART", 4: "NİSAN",
    5: "MAYIS", 6: "HAZİRAN", 7: "TEMMUZ", 8: "AĞUSTOS",
    9: "EYLÜL", 10: "EKİM", 11: "KASIM", 12: "ARALIK"
}


st.set_page_config(
    page_title="Detay Rapor - POS Komisyon",
    page_icon="📊",
    layout="wide"
)

# Authentication
if not check_password():
    st.stop()

st.title("📊 Detay Rapor")
st.markdown("**Aylık banka komisyon analizi - Excel formatı**")
st.markdown("---")


@st.cache_data
def load_data():
    """Veri yükle."""
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
    
    # İade filtrele
    if "transaction_type" in df.columns:
        refund_patterns = ["İADE", "IAD", "IADE", "REFUND"]
        mask = ~df["transaction_type"].astype(str).str.upper().str.contains("|".join(refund_patterns), na=False)
        df = df[mask]
    
    df = add_commission_control(df)
    return df


def get_pesin_oran(bank_name: str) -> float:
    """Banka için peşin oranı al."""
    rates = get_commission_rates()
    for alias, bank_rates in rates.items():
        if bank_name.upper() in alias.upper() or alias.upper() in bank_name.upper():
            return bank_rates.get("Peşin", bank_rates.get("1", 0.0))
    return 0.0


def create_monthly_detail(df: pd.DataFrame, month: int, year: int) -> pd.DataFrame:
    """Aylık detay raporu oluştur."""
    df = df.copy()
    df["_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["_month"] = df["_date"].dt.month
    df["_year"] = df["_date"].dt.year
    
    month_df = df[(df["_month"] == month) & (df["_year"] == year)]
    
    if month_df.empty:
        return pd.DataFrame()
    
    results = []
    for bank_name in month_df["bank_name"].unique():
        bank_df = month_df[month_df["bank_name"] == bank_name]
        
        toplam_cekim = bank_df["gross_amount"].sum()
        toplam_komisyon = bank_df["commission_amount"].sum()
        
        tek_cekim_mask = bank_df["installment_count"].fillna(1) == 1
        tek_cekim_tutar = bank_df.loc[tek_cekim_mask, "gross_amount"].sum()
        
        pesin_oran = get_pesin_oran(bank_name)
        oran_komisyon = tek_cekim_tutar * pesin_oran
        kendi_komisyon = bank_df.loc[tek_cekim_mask, "commission_amount"].sum()
        kar = kendi_komisyon - oran_komisyon
        
        net_gelir = toplam_cekim - toplam_komisyon
        
        results.append({
            "Banka Adı": bank_name,
            "Toplam Çekim Tutarı": toplam_cekim,
            "Toplam Ödenen Komisyon": toplam_komisyon,
            "Tek Çekim Tutarı": tek_cekim_tutar,
            "Oran/Komisyon": oran_komisyon,
            "Kendi Bankasının Komisyonu": kendi_komisyon,
            "Kar": kar,
            "Net Gelir": net_gelir
        })
    
    result_df = pd.DataFrame(results)
    
    if not result_df.empty:
        totals = {
            "Banka Adı": "TOPLAM",
            "Toplam Çekim Tutarı": result_df["Toplam Çekim Tutarı"].sum(),
            "Toplam Ödenen Komisyon": result_df["Toplam Ödenen Komisyon"].sum(),
            "Tek Çekim Tutarı": result_df["Tek Çekim Tutarı"].sum(),
            "Oran/Komisyon": result_df["Oran/Komisyon"].sum(),
            "Kendi Bankasının Komisyonu": result_df["Kendi Bankasının Komisyonu"].sum(),
            "Kar": result_df["Kar"].sum(),
            "Net Gelir": result_df["Net Gelir"].sum()
        }
        result_df = pd.concat([result_df, pd.DataFrame([totals])], ignore_index=True)
    
    return result_df


def create_genel_toplam(df: pd.DataFrame) -> pd.DataFrame:
    """Genel toplam raporu oluştur."""
    df = df.copy()
    df["_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["_ym"] = df["_date"].dt.to_period("M")
    
    results = []
    for ym in sorted(df["_ym"].dropna().unique()):
        month_df = df[df["_ym"] == ym]
        month_name = AY_ISIMLERI.get(ym.month, str(ym.month))
        
        toplam_cekim = month_df["gross_amount"].sum()
        toplam_komisyon = month_df["commission_amount"].sum()
        
        tek_cekim_mask = month_df["installment_count"].fillna(1) == 1
        tek_cekim_tutar = month_df.loc[tek_cekim_mask, "gross_amount"].sum()
        kendi_komisyon = month_df.loc[tek_cekim_mask, "commission_amount"].sum()
        
        net_gelir = toplam_cekim - toplam_komisyon
        
        results.append({
            "Ay": month_name,
            "Toplam Çekim Tutarı": toplam_cekim,
            "Toplam Ödenen Komisyon": toplam_komisyon,
            "Tek Çekim Tutarı": tek_cekim_tutar,
            "Kendi Bankasının Komisyonu": kendi_komisyon,
            "Net Gelir": net_gelir
        })
    
    result_df = pd.DataFrame(results)
    
    if not result_df.empty:
        totals = {col: result_df[col].sum() if col != "Ay" else "TOPLAM" for col in result_df.columns}
        result_df = pd.concat([result_df, pd.DataFrame([totals])], ignore_index=True)
    
    return result_df


def create_pesin_oranlar() -> pd.DataFrame:
    """Peşin oranlar tablosu."""
    rates = get_commission_rates()
    
    bank_mapping = [
        ("Garanti", "T. GARANTI BANKASI A.S."),
        ("YKB", "YAPI VE KREDI BANKASI A.S."),
        ("İşbankası", "T. IS BANKASI A.S."),
        ("Akbank", "AKBANK T.A.S."),
        ("Finansbank", "FINANSBANK A.S."),
        ("Halkbank", "T. HALK BANKASI A.S."),
        ("Vakıfbank", "T. VAKIFLAR BANKASI T.A.O."),
        ("Ziraat", "ZİRAAT BANKASI")
    ]
    
    results = []
    for display_name, full_name in bank_mapping:
        pesin_rate = 0
        for alias, bank_rates in rates.items():
            if full_name.upper() in alias.upper() or alias.upper() in full_name.upper():
                pesin_rate = bank_rates.get("Peşin", bank_rates.get("1", 0))
                break
        
        results.append({
            "Banka Adı": display_name,
            "Peşin Oranı": f"%{pesin_rate*100:.2f}"
        })
    
    return pd.DataFrame(results)


def create_excel_report(df: pd.DataFrame) -> BytesIO:
    """Excel raporu oluştur."""
    output = BytesIO()
    
    df = df.copy()
    df["_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["_month"] = df["_date"].dt.month
    df["_year"] = df["_date"].dt.year
    
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        unique_months = df.dropna(subset=["_date"]).groupby(["_year", "_month"]).size().reset_index()
        
        for _, row in unique_months.iterrows():
            year, month = int(row["_year"]), int(row["_month"])
            month_name = AY_ISIMLERI.get(month, str(month))
            
            monthly_report = create_monthly_detail(df, month, year)
            if not monthly_report.empty:
                sheet_name = f"{month_name} {year}"[:31]
                monthly_report.to_excel(writer, sheet_name=sheet_name, index=False)
        
        genel_toplam = create_genel_toplam(df)
        genel_toplam.to_excel(writer, sheet_name="Genel Toplam", index=False)
        
        pesin_rates = create_pesin_oranlar()
        pesin_rates.to_excel(writer, sheet_name="Peşin Oranları", index=False)
    
    output.seek(0)
    return output


def display_no_data():
    """Veri yok mesajı."""
    st.warning("""
    ⚠️ **Veri Bulunamadı**
    
    Rapor oluşturmak için önce veri yüklemeniz gerekmektedir.
    
    **Adımlar:**
    1. Sol menüden **"📤 Dosya Yükle"** sayfasına gidin
    2. Banka ekstre dosyalarınızı yükleyin
    3. Bu sayfaya geri dönün
    """)


def format_table(df: pd.DataFrame) -> pd.DataFrame:
    """Tabloyu formatla."""
    numeric_cols = [c for c in df.columns if c not in ["Banka Adı", "Ay"]]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: f"₺{x:,.2f}" if isinstance(x, (int, float)) else x)
    return df


def main():
    df = load_data()
    
    if df is None or df.empty:
        display_no_data()
        return
    
    # Tarih bilgisi kontrol
    df_temp = df.copy()
    df_temp["_date"] = pd.to_datetime(df_temp["transaction_date"], errors="coerce")
    df_temp = df_temp.dropna(subset=["_date"])
    
    if df_temp.empty:
        st.error("❌ Tarih bilgisi olan işlem bulunamadı.")
        return
    
    df_temp["_month"] = df_temp["_date"].dt.month
    df_temp["_year"] = df_temp["_date"].dt.year
    available_months = df_temp.groupby(["_year", "_month"]).size().reset_index()
    
    # Özet metrikler
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("💰 Toplam Tutar", f"₺{df['gross_amount'].sum():,.2f}")
    col2.metric("💳 Komisyon", f"₺{df['commission_amount'].sum():,.2f}")
    col3.metric("📈 Net Tutar", f"₺{df['net_amount'].sum():,.2f}")
    col4.metric("📅 Ay Sayısı", len(available_months))
    
    st.markdown("---")
    
    tabs = st.tabs(["📅 Aylık Detay", "📊 Genel Toplam", "💳 Peşin Oranları", "📥 Excel İndir"])
    
    with tabs[0]:
        st.subheader("📅 Aylık Banka Detay Raporu")
        
        month_options = []
        for _, row in available_months.iterrows():
            year, month = int(row["_year"]), int(row["_month"])
            month_name = AY_ISIMLERI.get(month, str(month))
            month_options.append({"label": f"{month_name} {year}", "year": year, "month": month})
        
        selected_idx = st.selectbox(
            "Ay Seçin",
            range(len(month_options)),
            format_func=lambda x: month_options[x]["label"]
        )
        
        if selected_idx is not None:
            selected = month_options[selected_idx]
            monthly_report = create_monthly_detail(df, selected["month"], selected["year"])
            
            if not monthly_report.empty:
                st.markdown(f"### {selected['label']}")
                st.dataframe(format_table(monthly_report.copy()), use_container_width=True, hide_index=True)
            else:
                st.warning("Bu ay için veri bulunamadı.")
    
    with tabs[1]:
        st.subheader("📊 Genel Toplam")
        genel_toplam = create_genel_toplam(df)
        if not genel_toplam.empty:
            st.dataframe(format_table(genel_toplam.copy()), use_container_width=True, hide_index=True)
    
    with tabs[2]:
        st.subheader("💳 Tek Çekim - Banka Oranları")
        pesin_rates = create_pesin_oranlar()
        st.dataframe(pesin_rates, use_container_width=True, hide_index=True)
        st.info("Oranları güncellemek için **'💳 Komisyon Oranları'** sayfasını kullanın.")
    
    with tabs[3]:
        st.subheader("📥 Excel Raporu İndir")
        st.markdown("""
        Excel raporu şunları içerir:
        - Her ay için ayrı detay sayfası
        - Genel Toplam özet sayfası
        - Peşin Oranları referans sayfası
        """)
        
        excel_data = create_excel_report(df)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        st.download_button(
            label="📥 Excel Raporu İndir",
            data=excel_data,
            file_name=f"komisyon_raporu_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


if __name__ == "__main__":
    main()
