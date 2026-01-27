"""Cash Flow Dashboard - Streamlit Application.

Interactive dashboard for analyzing bank POS commission data with control mechanisms.
Recreates the manual Excel workflow with automated calculations and validations.

Run with: streamlit run src/dashboard/app.py
"""

from pathlib import Path
from typing import Dict, Tuple

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Data paths
RAW_PATH = Path(__file__).parent.parent.parent / "data" / "raw"
RAW_FILE = RAW_PATH / "Ziraat Bankası- Aralık Tek Çekim İşlemler Raporu-Bank-raw.xlsx"
RAW_SHEET = "Ziraat Ekstre-31.12"

# Commission rates by bank and installment (from Oranlar sheet)
COMMISSION_RATES = {
    "ZİRAAT BANKASI": {
        "Peşin": 0.023, "2": 0.045, "3": 0.062, "4": 0.079, "5": 0.093,
        "6": 0.11, "7": 0.126, "8": 0.142, "9": 0.16, "10": 0.2055
    },
    "AKBANK T.A.S.": {
        "Peşin": 0.034, "2": 0.0586, "3": 0.0773, "4": 0.096, "5": 0.1146,
        "6": 0.1333, "7": 0.15202, "8": 0.1707, "9": 0.1894, "10": 0.2081
    },
    "T. GARANTI BANKASI A.S.": {
        "Peşin": 0.0356, "2": 0.0559, "3": 0.0742, "4": 0.093, "5": 0.1108,
        "6": 0.1294, "7": 0.1473, "8": 0.1651, "9": 0.1829, "10": 0.2006
    },
    "T. HALK BANKASI A.S.": {
        "Peşin": 0.0374, "2": 0.0527, "3": 0.0715, "4": 0.0903, "5": 0.1091,
        "6": 0.1279, "7": 0.1467, "8": 0.1656, "9": 0.1844, "10": 0.2032
    },
    "FINANSBANK A.S.": {
        "Peşin": 0.0374, "2": 0.0561, "3": 0.0748, "4": 0.0935, "5": 0.1121,
        "6": 0.1308, "7": 0.1495, "8": 0.1682, "9": 0.1869, "10": 0.2056
    },
    "T. VAKIFLAR BANKASI T.A.O.": {
        "Peşin": 0.0336, "2": 0.0561, "3": 0.0748, "4": 0.0935, "5": 0.1121,
        "6": 0.1308, "7": 0.1495, "8": 0.1682, "9": 0.1869, "10": 0.2056
    },
    "YAPI VE KREDI BANKASI A.S.": {
        "Peşin": 0.0362, "2": 0.0525, "3": 0.07, "4": 0.0875, "5": 0.105,
        "6": 0.1225, "7": 0.14, "8": 0.1575, "9": 0.175, "10": 0.1925
    },
    "T. IS BANKASI A.S.": {
        "Peşin": 0.03738
    },
}


def setup_page():
    """Configure Streamlit page settings."""
    st.set_page_config(
        page_title="Cash Flow Dashboard / Nakit Akış Paneli",
        page_icon="💰",
        layout="wide",
    )
    st.title("💰 Cash Flow Dashboard / Nakit Akış Paneli")
    st.markdown("**Ziraat Ekstre Raw Data - Control & Summary Analysis**")
    st.markdown("---")


def get_expected_rate(bank: str, taksit: str) -> float:
    """Get expected commission rate for bank and installment."""
    bank_rates = COMMISSION_RATES.get(bank, {})
    return bank_rates.get(taksit, bank_rates.get("Peşin", 0.03))


@st.cache_data
def load_raw_data() -> pd.DataFrame | None:
    """Load the raw transaction data from Ziraat Ekstre-31.12 sheet."""
    if not RAW_FILE.exists():
        return None
    
    df = pd.read_excel(RAW_FILE, sheet_name=RAW_SHEET)
    
    # Keep only meaningful columns (first 16)
    df = df.iloc[:, :16]
    
    # Rename columns to standard names
    df = df.rename(columns={
        "İşlem Tipi": "İşlem Tipi",
        "İşlem Durumu": "İşlem Durumu",
        "Ay": "Ay",
        "İşlem Tarihi": "Tarih",
        "Kartın Bankası": "Kartın Bankası",
        "Banka adı": "Banka Adı",
        "Tutar": "Tutar",
        "Para Birimi": "Para Birimi",
        "Taksit": "Taksit Sayısı",
        "TÜR": "Tip",
        "Kart Markası": "Kart Markası",
    })
    
    # Ensure numeric
    df["Tutar"] = pd.to_numeric(df["Tutar"], errors="coerce")
    
    # Convert Taksit Sayısı to string (mixed types: "Peşin" and integers)
    df["Taksit Sayısı"] = df["Taksit Sayısı"].astype(str)
    
    # Get expected commission rate based on bank and installment
    df["Beklenen Oran"] = df.apply(
        lambda row: get_expected_rate(row["Banka Adı"], row["Taksit Sayısı"]), axis=1
    )
    
    # Calculate expected commission
    df["Beklenen Komisyon"] = df["Tutar"] * df["Beklenen Oran"]
    df["Beklenen Net"] = df["Tutar"] - df["Beklenen Komisyon"]
    
    # Parse date
    df["Tarih"] = pd.to_datetime(df["Tarih"], errors="coerce")
    
    # Clean nulls
    df = df.dropna(subset=["Tutar", "Banka Adı"])
    
    # Filter only successful transactions (Başarılı)
    df = df[df["İşlem Durumu"] == "Başarılı"]
    
    return df


def display_summary_metrics(df: pd.DataFrame):
    """Display key summary metrics like the Özet sheet."""
    st.subheader("📊 Özet Metrikler / Summary Metrics")
    
    # Split into Tek Çekim (Peşin) and Taksitli
    pesin_df = df[df["Taksit Sayısı"] == "Peşin"]
    taksitli_df = df[df["Taksit Sayısı"] != "Peşin"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 💵 Tek Çekim (Peşin)")
        total_pesin = pesin_df["Tutar"].sum()
        komisyon_pesin = pesin_df["Beklenen Komisyon"].sum()
        net_pesin = pesin_df["Beklenen Net"].sum()
        rate_pesin = (komisyon_pesin / total_pesin * 100) if total_pesin > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Çekim Tutarı", f"₺{total_pesin:,.2f}")
        c2.metric("Komisyon", f"₺{komisyon_pesin:,.2f}")
        c3.metric("Net Tutar", f"₺{net_pesin:,.2f}")
        c4.metric("Oran", f"%{rate_pesin:.2f}")
    
    with col2:
        st.markdown("### 💳 Taksitli")
        total_taksit = taksitli_df["Tutar"].sum()
        komisyon_taksit = taksitli_df["Beklenen Komisyon"].sum()
        net_taksit = taksitli_df["Beklenen Net"].sum()
        rate_taksit = (komisyon_taksit / total_taksit * 100) if total_taksit > 0 else 0
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Çekim Tutarı", f"₺{total_taksit:,.2f}")
        c2.metric("Komisyon", f"₺{komisyon_taksit:,.2f}")
        c3.metric("Net Tutar", f"₺{net_taksit:,.2f}")
        c4.metric("Oran", f"%{rate_taksit:.2f}")
    
    # Total summary
    st.markdown("---")
    total = df["Tutar"].sum()
    komisyon = df["Beklenen Komisyon"].sum()
    net = df["Beklenen Net"].sum()
    avg_rate = (komisyon / total * 100) if total > 0 else 0
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("📊 TOPLAM ÇEKİM", f"₺{total:,.2f}")
    c2.metric("💸 TOPLAM KOMİSYON", f"₺{komisyon:,.2f}")
    c3.metric("✅ TOPLAM NET", f"₺{net:,.2f}")
    c4.metric("📈 ORT. ORAN", f"%{avg_rate:.2f}")
    c5.metric("🔢 İŞLEM SAYISI", f"{len(df):,}")


def display_bank_summary(df: pd.DataFrame, prefix: str = ""):
    """Display bank-level summary split by Tek Çekim and Taksitli."""
    st.subheader("🏦 Banka Bazında Özet / Bank Summary")
    
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
                "Çekim Tutarı": "₺{:,.2f}",
                "Komisyon": "₺{:,.2f}",
                "Oran": "{:.4f}"
            }),
            hide_index=True
        )
    
    with col2:
        st.markdown("#### 💳 Taksitli - Banka Bazında")
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
                "Çekim Tutarı": "₺{:,.2f}",
                "Komisyon": "₺{:,.2f}",
                "Oran": "{:.4f}",
                "Dağılım %": "{:.2f}%"
            }),
            hide_index=True
        )


def display_installment_breakdown(df: pd.DataFrame):
    """Display breakdown by installment count (Taksit Sayısı)."""
    st.subheader("💳 Taksit Sayısına Göre Dağılım / By Installment Count")
    
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
            "Çekim Tutarı": "₺{:,.2f}",
            "Komisyon": "₺{:,.2f}",
            "Oran": "{:.4f}",
            "Tutar %": "{:.2f}%",
            "Adet": "{:,}",
            "Adet %": "{:.2f}%"
        }),
        hide_index=True
    )


def display_monthly_summary(df: pd.DataFrame):
    """Display monthly breakdown like the Özet sheet."""
    st.subheader("📅 Aylar İtibariyle / Monthly Breakdown")
    
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
                "Çekim Tutarı": "₺{:,.2f}",
                "Komisyon": "₺{:,.2f}",
                "Oran": "{:.4f}"
            }),
            hide_index=True
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
                "Çekim Tutarı": "₺{:,.2f}",
                "Komisyon": "₺{:,.2f}",
                "Oran": "{:.4f}"
            }),
            hide_index=True
        )


def display_commission_rates_lookup(df: pd.DataFrame):
    """Display commission rates lookup table like Oranlar sheet."""
    st.subheader("📊 Komisyon Oranları / Commission Rates Lookup")
    
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
    """Display control/validation checks - comparing expected vs calculated."""
    st.subheader("🔍 Kontrol Mekanizması / Control Validation")
    
    st.markdown("""
    Bu bölüm, banka komisyon hesaplamalarının doğruluğunu kontrol eder.
    Beklenen oranlar ile gerçek oranlar karşılaştırılır.
    """)
    
    # Summary by bank - comparing expected rates
    control_summary = df.groupby("Banka Adı").agg({
        "Tutar": "sum",
        "Beklenen Komisyon": "sum",
        "Beklenen Oran": "mean"
    }).reset_index()
    control_summary.columns = ["Banka", "Toplam Tutar", "Hesaplanan Komisyon", "Ort. Oran"]
    
    # Calculate effective rate
    control_summary["Efektif Oran"] = (
        control_summary["Hesaplanan Komisyon"] / control_summary["Toplam Tutar"]
    )
    
    # Net amount
    control_summary["Net Tutar"] = control_summary["Toplam Tutar"] - control_summary["Hesaplanan Komisyon"]
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Banka Bazında Kontrol Özeti")
        st.dataframe(
            control_summary.style.format({
                "Toplam Tutar": "₺{:,.2f}",
                "Hesaplanan Komisyon": "₺{:,.2f}",
                "Ort. Oran": "{:.4f}",
                "Efektif Oran": "{:.4f}",
                "Net Tutar": "₺{:,.2f}"
            }),
            hide_index=True
        )
    
    with col2:
        st.markdown("#### Komisyon Dağılımı")
        fig = px.pie(
            control_summary,
            values="Hesaplanan Komisyon",
            names="Banka",
            title="Komisyon Dağılımı (Banka Bazında)",
            hole=0.4
        )
        st.plotly_chart(fig, key="commission_pie")
    
    # Grand totals
    st.markdown("---")
    st.markdown("### 📊 Toplam Kontrol / Grand Totals")
    
    total_tutar = control_summary["Toplam Tutar"].sum()
    total_komisyon = control_summary["Hesaplanan Komisyon"].sum()
    total_net = control_summary["Net Tutar"].sum()
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Toplam Çekim", f"₺{total_tutar:,.2f}")
    c2.metric("Toplam Komisyon (Hesaplanan)", f"₺{total_komisyon:,.2f}")
    c3.metric("Toplam Net", f"₺{total_net:,.2f}")
    
    # Comparison box
    st.info(f"""
    **Kontrol Sonucu:**
    - Toplam Çekim: ₺{total_tutar:,.2f}
    - Hesaplanan Komisyon: ₺{total_komisyon:,.2f}
    - Efektif Komisyon Oranı: %{(total_komisyon/total_tutar*100):.2f}
    - Net Tutar: ₺{total_net:,.2f}
    """)


def display_data_table(df: pd.DataFrame):
    """Display filtered data table with export."""
    st.subheader("📋 İşlem Verileri / Transaction Data")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        banks = ["Tümü / All"] + sorted(df["Banka Adı"].unique().tolist())
        selected_bank = st.selectbox("Banka / Bank", banks, key="data_bank")
    
    with col2:
        months = ["Tümü / All"] + df["Ay"].dropna().unique().tolist()
        selected_month = st.selectbox("Ay / Month", months, key="data_month")
    
    with col3:
        types = ["Tümü / All"] + df["Tip"].dropna().unique().tolist()
        selected_type = st.selectbox("Tip / Type", types, key="data_type")
    
    with col4:
        taksit_options = ["Tümü / All"] + sorted(df["Taksit Sayısı"].unique().tolist())
        selected_taksit = st.selectbox("Taksit / Installment", taksit_options, key="data_taksit")
    
    # Apply filters
    filtered = df.copy()
    if selected_bank != "Tümü / All":
        filtered = filtered[filtered["Banka Adı"] == selected_bank]
    if selected_month != "Tümü / All":
        filtered = filtered[filtered["Ay"] == selected_month]
    if selected_type != "Tümü / All":
        filtered = filtered[filtered["Tip"] == selected_type]
    if selected_taksit != "Tümü / All":
        filtered = filtered[filtered["Taksit Sayısı"] == selected_taksit]
    
    # Show summary for filtered data
    st.markdown(f"**{len(filtered):,} işlem gösteriliyor / showing transactions**")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Filtreli Toplam", f"₺{filtered['Tutar'].sum():,.2f}")
    c2.metric("Filtreli Komisyon", f"₺{filtered['Beklenen Komisyon'].sum():,.2f}")
    c3.metric("Filtreli Net", f"₺{filtered['Beklenen Net'].sum():,.2f}")
    
    # Display columns
    display_cols = ["Tarih", "Ay", "Banka Adı", "Tutar", "Taksit Sayısı", "Tip", 
                    "Beklenen Oran", "Beklenen Komisyon", "Beklenen Net", "Kart Markası"]
    display_cols = [c for c in display_cols if c in filtered.columns]
    
    st.dataframe(
        filtered[display_cols].head(1000).style.format({
            "Tutar": "₺{:,.2f}",
            "Beklenen Komisyon": "₺{:,.2f}",
            "Beklenen Net": "₺{:,.2f}",
            "Beklenen Oran": "{:.4f}"
        }),
        hide_index=True
    )
    
    # Export
    csv = filtered.to_csv(index=False)
    st.download_button(
        label="📥 CSV İndir / Download CSV",
        data=csv,
        file_name="komisyon_analizi_export.csv",
        mime="text/csv"
    )


def main():
    """Main dashboard application."""
    setup_page()
    
    # Load data
    df = load_raw_data()
    
    if df is None or df.empty:
        st.error(f"""
        ❌ Veri dosyası bulunamadı / Data file not found.
        
        Beklenen dosya / Expected file:
        `{RAW_FILE}`
        
        Sheet: `{RAW_SHEET}`
        """)
        return
    
    st.success(f"✅ {len(df):,} işlem yüklendi / transactions loaded (Başarılı only)")
    
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
    
    with tab5:
        display_commission_rates_lookup(df)
    
    with tab6:
        display_control_validation(df)
        st.markdown("---")
        display_data_table(df)


if __name__ == "__main__":
    main()
