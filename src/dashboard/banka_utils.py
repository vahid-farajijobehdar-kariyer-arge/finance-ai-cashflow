"""
Banka Detay Sayfaları Ortak Fonksiyonlar

Tüm banka detay sayfaları için paylaşılan yardımcı fonksiyonlar.
Türkçe hata mesajları ve veri kontrolü.
"""

import pandas as pd
import streamlit as st
from pathlib import Path
import sys

# Proje kök dizinini yola ekle
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.ingestion.reader import BankFileReader
from src.processing.commission_control import add_commission_control
from src.processing.calculator import filter_successful_transactions

# Veri yolları
RAW_PATH = PROJECT_ROOT.parent / "data" / "raw"


def yukle_tum_veri():
    """Tüm banka verilerini yükle - hata durumunda None döndürür."""
    if not RAW_PATH.exists():
        return None
    
    reader = BankFileReader()
    
    try:
        df = reader.read_all_files(RAW_PATH)
    except Exception:
        return None
    
    if df is None or df.empty:
        return None
    
    # Gerekli sütun kontrolü
    if "bank_name" not in df.columns:
        return None
    
    # Temizle ve işle
    df = df.reset_index(drop=True)
    df = df.loc[:, ~df.columns.duplicated()]
    df = filter_successful_transactions(df)
    df = add_commission_control(df)
    
    return df


def filtrele_banka_verisi(df: pd.DataFrame, banka_pattern: str) -> pd.DataFrame:
    """Belirli bir bankaya ait verileri filtrele."""
    if df is None or df.empty:
        return pd.DataFrame()
    
    if "bank_name" not in df.columns:
        return pd.DataFrame()
    
    mask = df['bank_name'].str.lower().str.contains(banka_pattern, na=False, regex=True)
    return df[mask].copy()


def goster_veri_yok_uyarisi(banka_adi: str):
    """Veri olmadığında Türkçe uyarı göster."""
    st.warning(f"""
    ⚠️ **{banka_adi} Verisi Bulunamadı**
    
    Bu banka için henüz veri yüklenmemiş.
    """)
    
    st.info("""
    📤 **Veri Yüklemek İçin:**
    
    1. Sol menüden **"📤 Dosya Yükle"** sayfasına gidin
    2. Banka Excel/CSV dosyanızı yükleyin
    3. Dosya isminde banka adı bulunmalıdır (örn: "Akbank_2025.xlsx")
    
    ✅ Desteklenen formatlar: `.xlsx`, `.xls`, `.csv`
    """)


def goster_genel_veri_yok_uyarisi():
    """Hiç veri olmadığında Türkçe uyarı göster."""
    st.warning("""
    ⚠️ **Veri Bulunamadı**
    
    Henüz hiçbir banka dosyası yüklenmemiş.
    """)
    
    st.info("""
    📤 **Başlamak İçin:**
    
    1. Sol menüden **"📤 Dosya Yükle"** sayfasına gidin
    2. Banka Excel/CSV dosyalarınızı yükleyin
    3. Sistem dosyaları otomatik olarak tanıyacaktır
    
    🏦 **Desteklenen Bankalar:**
    - Akbank, Garanti BBVA, Halkbank
    - QNB Finansbank, Vakıfbank, YKB
    - Ziraat Bankası, İş Bankası
    """)


def goster_ozet_metrikler(df: pd.DataFrame):
    """Özet metrikleri göster."""
    if df is None or df.empty:
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Toplam İşlem", f"{len(df):,}")
    
    with col2:
        toplam = df['gross_amount'].sum() if 'gross_amount' in df.columns else 0
        st.metric("Toplam Tutar", f"₺{toplam:,.2f}")
    
    with col3:
        komisyon = df['commission_amount'].sum() if 'commission_amount' in df.columns else 0
        st.metric("Toplam Komisyon", f"₺{komisyon:,.2f}")
    
    with col4:
        if 'commission_rate' in df.columns and df['commission_rate'].notna().any():
            oran = df['commission_rate'].mean() * 100
        else:
            oran = 0
        st.metric("Ortalama Oran", f"%{oran:.2f}")


def goster_taksit_dagilimi(df: pd.DataFrame, grafik_key: str = "taksit_chart"):
    """Taksit dağılımı grafiği göster."""
    if df is None or df.empty:
        st.info("ℹ️ Taksit dağılımı için veri bulunamadı.")
        return
    
    if "installment_count" not in df.columns:
        st.info("ℹ️ Taksit bilgisi mevcut değil.")
        return
    
    df_copy = df.copy()
    df_copy["Taksit"] = df_copy["installment_count"].fillna(1).astype(int)
    df_copy["Taksit"] = df_copy["Taksit"].apply(lambda x: "Peşin" if x in (0, 1) else f"{x} Taksit")
    
    taksit_df = df_copy.groupby("Taksit").agg({
        "gross_amount": "sum",
        "commission_amount": "sum"
    }).reset_index()
    
    taksit_df.columns = ["Taksit", "Tutar", "Komisyon"]
    
    import plotly.express as px
    
    fig = px.bar(
        taksit_df,
        x="Taksit",
        y="Tutar",
        title="Taksit Bazlı Tutar Dağılımı",
        labels={"Tutar": "Tutar (₺)", "Taksit": "Taksit Sayısı"},
        color="Komisyon",
        color_continuous_scale="Reds"
    )
    
    st.plotly_chart(fig, width="stretch", key=grafik_key)


def goster_aylik_trend(df: pd.DataFrame, grafik_key: str = "aylik_chart"):
    """Aylık trend grafiği göster."""
    if df is None or df.empty:
        st.info("ℹ️ Aylık trend için veri bulunamadı.")
        return
    
    if "transaction_date" not in df.columns:
        st.info("ℹ️ Tarih bilgisi mevcut değil.")
        return
    
    df_copy = df.copy()
    df_copy["_tarih"] = pd.to_datetime(df_copy["transaction_date"], errors="coerce")
    df_copy["Ay"] = df_copy["_tarih"].dt.to_period("M").astype(str)
    
    aylik = df_copy.groupby("Ay").agg({
        "gross_amount": "sum",
        "commission_amount": "sum"
    }).reset_index()
    
    aylik.columns = ["Ay", "Tutar", "Komisyon"]
    
    import plotly.express as px
    
    fig = px.line(
        aylik,
        x="Ay",
        y=["Tutar", "Komisyon"],
        title="Aylık Tutar ve Komisyon Trendi",
        labels={"value": "Tutar (₺)", "Ay": "Ay", "variable": "Metrik"}
    )
    
    st.plotly_chart(fig, width="stretch", key=grafik_key)


def goster_veri_tablosu(df: pd.DataFrame, max_satir: int = 100):
    """Veri tablosu göster."""
    if df is None or df.empty:
        st.info("ℹ️ Gösterilecek veri yok.")
        return
    
    # Gösterilecek sütunlar
    goster_sutunlar = [
        "transaction_date", "gross_amount", "commission_amount", 
        "net_amount", "installment_count", "commission_rate"
    ]
    
    mevcut_sutunlar = [c for c in goster_sutunlar if c in df.columns]
    
    if not mevcut_sutunlar:
        st.info("ℹ️ Gösterilecek sütun bulunamadı.")
        return
    
    # Türkçe sütun isimleri
    sutun_isimleri = {
        "transaction_date": "İşlem Tarihi",
        "gross_amount": "Brüt Tutar",
        "commission_amount": "Komisyon",
        "net_amount": "Net Tutar",
        "installment_count": "Taksit",
        "commission_rate": "Oran"
    }
    
    goster_df = df[mevcut_sutunlar].head(max_satir).rename(columns=sutun_isimleri)
    
    st.dataframe(goster_df, width="stretch", hide_index=True)
    
    if len(df) > max_satir:
        st.caption(f"ℹ️ İlk {max_satir} satır gösteriliyor. Toplam: {len(df):,} satır")
