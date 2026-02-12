"""
🏦 Akbank Detay Sayfası

Akbank komisyon analizi — satır bazında beklenen vs gerçek karşılaştırma.
commission_rate = EO_KES_TUTAR / PROVIZYON_TUTAR
Tolerans: %0.5

© 2026 Kariyer.net Finans Ekibi
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from io import BytesIO
from datetime import datetime
import sys

# Proje yolunu ekle
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from auth import check_password
from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control
from processing.calculator import filter_successful_transactions

# Sabitler
RAW_PATH = PROJECT_ROOT.parent / "data" / "raw"
TOLERANCE = 0.005  # %0.5


def format_currency(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"₺{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_percent(value: float) -> str:
    if pd.isna(value):
        return "-"
    return f"%{value*100:.2f}".replace(".", ",")


@st.cache_data(ttl=300)
def load_akbank_data():
    """Akbank verisini yükle ve işle."""
    if not RAW_PATH.exists():
        return pd.DataFrame()

    reader = BankFileReader()
    dfs = []
    for f in RAW_PATH.iterdir():
        if f.name.startswith("~$") or f.name.startswith("."):
            continue
        if f.suffix.lower() not in [".xlsx", ".xls", ".csv"]:
            continue
        if "akbank" not in f.name.lower():
            continue
        try:
            df = reader.read_file(f)
            dfs.append(df)
        except Exception:
            continue

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)
    df = df.loc[:, ~df.columns.duplicated()]
    df = filter_successful_transactions(df)
    df = add_commission_control(df)
    return df


# ─── Sayfa Yapılandırması ───
st.set_page_config(page_title="Akbank Detay", page_icon="🏦", layout="wide")

# Kimlik doğrulama
if not check_password():
    st.stop()

st.title("🏦 Akbank Detay")
st.markdown("**AKBANK T.A.Ş.** — Satır bazında komisyon analizi")
st.markdown(f"Tolerans: **%{TOLERANCE*100:.1f}** | Formül: `commission_rate = EO_KES_TUTAR / PROVIZYON_TUTAR`")
st.markdown("---")

df = load_akbank_data()

if df.empty:
    st.warning("Akbank verisi bulunamadı. Lütfen Dosya Yükle sayfasından Akbank dosyasını yükleyin.")
    st.stop()


# ─── 1. ÖZET METRİKLER ───
st.subheader("📊 Özet")

total_gross = df["gross_amount"].sum()
total_comm = df["commission_amount"].sum()
total_net = df["net_amount"].sum() if "net_amount" in df.columns else total_gross - total_comm
total_expected = df["commission_expected"].sum() if "commission_expected" in df.columns else 0
total_diff = df["commission_diff"].sum() if "commission_diff" in df.columns else 0
avg_rate = total_comm / total_gross if total_gross > 0 else 0
match_count = df["rate_match"].sum() if "rate_match" in df.columns else 0
mismatch_count = len(df) - match_count

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("İşlem", f"{len(df):,}")
c2.metric("Brüt Tutar", format_currency(total_gross))
c3.metric("Gerçek Komisyon", format_currency(total_comm))
c4.metric("Beklenen Komisyon", format_currency(total_expected))
c5.metric("Toplam Fark", format_currency(total_diff))
c6.metric("Ort. Oran", f"%{avg_rate*100:.2f}")

# Eşleşme durumu
if mismatch_count == 0:
    st.success(f"✅ Tüm {len(df):,} işlem tolerans içinde (%{TOLERANCE*100:.1f}). Efektif fark = ₺0")
else:
    st.warning(f"⚠️ {mismatch_count:,} işlemde tolerans dışı fark var. Toplam fark: {format_currency(total_diff)}")


# ─── 2. TAKSİT BAZINDA BEKLENEN vs GERÇEK ───
st.markdown("---")
st.subheader("📋 Taksit Bazında Beklenen vs Gerçek Komisyon")

taksit_df = pd.DataFrame()  # fallback

if "installment_count" in df.columns:
    taksit_data = []
    for inst, grp in df.groupby("installment_count"):
        actual_rate = grp["commission_rate"].mean()
        expected_rate = grp["rate_expected"].mean() if "rate_expected" in grp.columns else 0
        rate_diff = abs(actual_rate - expected_rate)
        actual_comm = grp["commission_amount"].sum()
        expected_comm = grp["commission_expected"].sum() if "commission_expected" in grp.columns else 0
        eff_diff = grp["commission_diff"].sum() if "commission_diff" in grp.columns else 0
        gross = grp["gross_amount"].sum()
        status = "✅ KABUL" if rate_diff < TOLERANCE else "❌ FARK VAR"

        taksit_data.append({
            "Taksit": int(inst),
            "İşlem Sayısı": len(grp),
            "Brüt Tutar (₺)": gross,
            "Gerçek Oran": actual_rate,
            "Beklenen Oran": expected_rate,
            "Oran Farkı": rate_diff,
            "Gerçek Komisyon (₺)": actual_comm,
            "Beklenen Komisyon (₺)": expected_comm,
            "Fark (₺)": eff_diff,
            "Durum": status,
        })

    taksit_df = pd.DataFrame(taksit_data)

    st.dataframe(
        taksit_df.style.format({
            "Brüt Tutar (₺)": "₺{:,.2f}",
            "Gerçek Oran": "{:.4f}",
            "Beklenen Oran": "{:.4f}",
            "Oran Farkı": "{:.4f}",
            "Gerçek Komisyon (₺)": "₺{:,.2f}",
            "Beklenen Komisyon (₺)": "₺{:,.2f}",
            "Fark (₺)": "₺{:,.2f}",
        }).applymap(
            lambda v: "background-color: #d4edda" if v == "✅ KABUL" else (
                "background-color: #f8d7da" if v == "❌ FARK VAR" else ""
            ),
            subset=["Durum"]
        ),
        use_container_width=True,
        hide_index=True,
    )

    # Oran karşılaştırma grafiği
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[f"Taksit {t}" for t in taksit_df["Taksit"]],
        y=taksit_df["Gerçek Oran"] * 100,
        name="Gerçek Oran (%)",
        marker_color="#E30613",
    ))
    fig.add_trace(go.Bar(
        x=[f"Taksit {t}" for t in taksit_df["Taksit"]],
        y=taksit_df["Beklenen Oran"] * 100,
        name="Beklenen Oran (%)",
        marker_color="#999999",
    ))
    fig.update_layout(
        title="Gerçek vs Beklenen Komisyon Oranı (Taksit Bazında)",
        barmode="group",
        yaxis_title="Oran (%)",
        xaxis_title="Taksit",
        legend=dict(x=0.01, y=0.99),
    )
    st.plotly_chart(fig, use_container_width=True)


# ─── 3. SATIR BAZINDA DETAY ───
st.markdown("---")
st.subheader("📄 Satır Bazında Detay (Tüm İşlemler)")

detail_cols = [
    "transaction_date", "gross_amount", "commission_amount",
    "commission_rate", "rate_expected", "rate_diff",
    "commission_expected", "commission_diff", "installment_count",
    "net_amount", "rate_match",
]
available = [c for c in detail_cols if c in df.columns]

col_names = {
    "transaction_date": "Tarih",
    "gross_amount": "PROVIZYON_TUTAR",
    "commission_amount": "EO_KES_TUTAR",
    "commission_rate": "Gerçek Oran",
    "rate_expected": "Beklenen Oran",
    "rate_diff": "Oran Farkı",
    "commission_expected": "Beklenen Komisyon",
    "commission_diff": "Fark (₺)",
    "installment_count": "Taksit",
    "net_amount": "NET_TUTAR",
    "rate_match": "Eşleşme",
}

# Filtre
filter_col1, filter_col2 = st.columns(2)
with filter_col1:
    installments = sorted(df["installment_count"].unique()) if "installment_count" in df.columns else []
    selected_inst = st.multiselect("Taksit Filtresi", installments, default=installments)
with filter_col2:
    match_filter = st.selectbox("Eşleşme Filtresi", ["Tümü", "Eşleşen", "Eşleşmeyen"])

view_df = df.copy()
if selected_inst and "installment_count" in view_df.columns:
    view_df = view_df[view_df["installment_count"].isin(selected_inst)]
if match_filter == "Eşleşen" and "rate_match" in view_df.columns:
    view_df = view_df[view_df["rate_match"] == True]
elif match_filter == "Eşleşmeyen" and "rate_match" in view_df.columns:
    view_df = view_df[view_df["rate_match"] == False]

display_df = view_df[available].rename(columns=col_names)

format_dict = {}
for c in ["PROVIZYON_TUTAR", "EO_KES_TUTAR", "Beklenen Komisyon", "Fark (₺)", "NET_TUTAR"]:
    if c in display_df.columns:
        format_dict[c] = "₺{:,.2f}"
for c in ["Gerçek Oran", "Beklenen Oran", "Oran Farkı"]:
    if c in display_df.columns:
        format_dict[c] = "{:.4f}"

st.dataframe(
    display_df.style.format(format_dict),
    use_container_width=True,
    hide_index=True,
    height=600,
)

st.caption(f"Gösterilen: {len(view_df):,} / Toplam: {len(df):,} işlem")


# ─── 4. TOPLAMLAR ───
st.markdown("---")
st.subheader("📊 Toplamlar")

sum_gross = view_df["gross_amount"].sum()
sum_comm = view_df["commission_amount"].sum()
sum_expected = view_df["commission_expected"].sum() if "commission_expected" in view_df.columns else 0
sum_diff = view_df["commission_diff"].sum() if "commission_diff" in view_df.columns else 0

sc1, sc2, sc3, sc4 = st.columns(4)
sc1.metric("Toplam Brüt", format_currency(sum_gross))
sc2.metric("Toplam Gerçek Komisyon", format_currency(sum_comm))
sc3.metric("Toplam Beklenen Komisyon", format_currency(sum_expected))
sc4.metric("Toplam Fark (Toleranslı)", format_currency(sum_diff))


# ─── 5. EXPORT ───
st.markdown("---")
st.subheader("📥 Dışa Aktar")

col_e1, col_e2 = st.columns(2)

with col_e1:
    csv = view_df[available].to_csv(index=False)
    st.download_button(
        "📥 CSV İndir",
        data=csv,
        file_name=f"akbank_detay_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
    )

with col_e2:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        view_df[available].to_excel(writer, sheet_name="Akbank Detay", index=False)
        if not taksit_df.empty:
            taksit_df.to_excel(writer, sheet_name="Taksit Özeti", index=False)
    st.download_button(
        "📥 Excel İndir",
        data=output.getvalue(),
        file_name=f"akbank_detay_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

st.markdown("---")
st.caption("© 2026 Kariyer.net Finans Ekibi")
