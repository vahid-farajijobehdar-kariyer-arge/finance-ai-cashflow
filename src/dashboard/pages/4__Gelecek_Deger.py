"""
💰 Gelecek Değer Hesaplayıcı

Banka faiz oranları ile mevduat gelecek değerini hesaplayın.
Yüklenen dosyalardan aylık/çeyreklik net tutarlar ile projeksiyon yapın.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import yaml
from pathlib import Path
import sys

# Proje kök dizinini yola ekle
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from processing.future_value import FutureValueCalculator, DepositRate
from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control
from processing.calculator import filter_successful_transactions

# Kimlik doğrulama modülünü ekle
sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password

# Format utilities
try:
    from format_utils import format_turkish_currency, format_turkish_number, format_turkish_percent
except ImportError:
    # Fallback
    def format_turkish_currency(v, s="₺", d=2):
        return f"{v:,.{d}f} {s}".replace(",", "X").replace(".", ",").replace("X", ".")
    def format_turkish_number(v, d=2):
        return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    def format_turkish_percent(v, d=2):
        return f"%{v*100:.{d}f}".replace(".", ",")

# Veri yolları
RAW_PATH = PROJECT_ROOT.parent / "data" / "raw"
SETTINGS_PATH = PROJECT_ROOT.parent / "config" / "settings.yaml"


def load_deposit_rates_from_settings():
    """Ayarlardan mevduat oranlarını yükle."""
    try:
        if SETTINGS_PATH.exists():
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                settings = yaml.safe_load(f)
            
            deposit_rates = settings.get("deposit_rates", {})
            if deposit_rates:
                rates = []
                for bank_key, bank_data in deposit_rates.items():
                    bank_name = bank_data.get("name", bank_key.title())
                    bank_rates = bank_data.get("rates", {})
                    for term, rate in bank_rates.items():
                        rates.append(DepositRate(bank_name, rate, int(term)))
                return rates
    except Exception:
        pass
    return None


def init_calculator():
    """Gelecek değer hesaplayıcısını başlat."""
    # Önce ayarlardan oranları yükle
    custom_rates = load_deposit_rates_from_settings()
    
    if "fv_calculator" not in st.session_state or custom_rates:
        st.session_state.fv_calculator = FutureValueCalculator(custom_rates)
    return st.session_state.fv_calculator


@st.cache_data
def yukle_veri():
    """Tüm banka dosyalarını yükle ve işle."""
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


def hesapla_aylik_toplamlar(df: pd.DataFrame) -> pd.DataFrame:
    """Aylık bazda toplamları hesapla."""
    df = df.copy()
    df["_tarih"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["_ay_yil"] = df["_tarih"].dt.to_period("M")
    
    aylik = df.groupby("_ay_yil").agg({
        "gross_amount": "sum",
        "commission_amount": "sum",
        "net_amount": "sum"
    }).reset_index()
    
    aylik.columns = ["Dönem", "Brüt Tutar", "Komisyon", "Net Tutar"]
    aylik["Dönem"] = aylik["Dönem"].astype(str)
    
    return aylik


def hesapla_ceyreklik_toplamlar(df: pd.DataFrame) -> pd.DataFrame:
    """Çeyreklik bazda toplamları hesapla."""
    df = df.copy()
    df["_tarih"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df["_ceyrek"] = df["_tarih"].dt.to_period("Q")
    
    ceyreklik = df.groupby("_ceyrek").agg({
        "gross_amount": "sum",
        "commission_amount": "sum",
        "net_amount": "sum"
    }).reset_index()
    
    ceyreklik.columns = ["Dönem", "Brüt Tutar", "Komisyon", "Net Tutar"]
    ceyreklik["Dönem"] = ceyreklik["Dönem"].astype(str)
    
    return ceyreklik


def render_veri_bazli_projeksiyon(calculator: FutureValueCalculator):
    """Yüklenen veriler ile projeksiyon yap."""
    st.subheader("📊 Veri Bazlı Gelecek Değer Projeksiyonu")
    
    # Veri yükle
    df = yukle_veri()
    
    if df is None or df.empty:
        st.warning("""
        ⚠️ **Veri Bulunamadı**
        
        Gelecek değer projeksiyonu yapabilmek için önce banka dosyalarını yüklemeniz gerekmektedir.
        
        👉 **"📤 Dosya Yükle"** sayfasından dosyalarınızı yükleyin.
        """)
        
        st.info("""
        💡 **İpucu:** Desteklenen dosya formatları:
        - Excel (.xlsx, .xls)
        - CSV (.csv)
        
        Dosya isimleri banka adını içermelidir (örn: "Akbank_2025.xlsx", "Garanti_rapor.csv")
        """)
        return
    
    # Özet metrikler
    toplam_brut = df["gross_amount"].sum()
    toplam_komisyon = df["commission_amount"].sum()
    toplam_net = df["net_amount"].sum()
    
    st.success(f"✅ **{len(df):,}** işlem yüklendi")
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Brüt", f"₺{toplam_brut:,.2f}")
    col2.metric("Toplam Komisyon", f"₺{toplam_komisyon:,.2f}")
    col3.metric("Toplam Net", f"₺{toplam_net:,.2f}")
    
    st.markdown("---")
    
    # Dönem seçimi
    donem_tipi = st.radio(
        "Dönem Tipi",
        ["Aylık", "Çeyreklik", "Toplam"],
        horizontal=True
    )
    
    if donem_tipi == "Aylık":
        donem_df = hesapla_aylik_toplamlar(df)
    elif donem_tipi == "Çeyreklik":
        donem_df = hesapla_ceyreklik_toplamlar(df)
    else:
        donem_df = pd.DataFrame([{
            "Dönem": "Toplam",
            "Brüt Tutar": toplam_brut,
            "Komisyon": toplam_komisyon,
            "Net Tutar": toplam_net
        }])
    
    if donem_df.empty:
        st.warning("⚠️ Seçilen dönem için veri bulunamadı.")
        return
    
    # Dönem tablosu
    st.markdown("### 📋 Dönem Bazlı Toplamlar")
    st.dataframe(
        donem_df.style.format({
            "Brüt Tutar": "₺{:,.2f}",
            "Komisyon": "₺{:,.2f}",
            "Net Tutar": "₺{:,.2f}"
        }),
        hide_index=True,
        use_container_width=True
    )
    
    st.markdown("---")
    
    # Projeksiyon parametreleri
    st.markdown("### 💰 Projeksiyon Parametreleri")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        yatirim_tutari = st.selectbox(
            "Yatırım Yapılacak Tutar",
            ["Net Tutar Toplamı", "Brüt Tutar Toplamı", "Manuel Giriş"]
        )
        
        if yatirim_tutari == "Net Tutar Toplamı":
            anapara = donem_df["Net Tutar"].sum()
        elif yatirim_tutari == "Brüt Tutar Toplamı":
            anapara = donem_df["Brüt Tutar"].sum()
        else:
            anapara = st.number_input("Anapara (₺)", min_value=0.0, value=100000.0, step=10000.0)
    
    with col2:
        faiz_orani = st.slider(
            "Yıllık Faiz Oranı (%)",
            min_value=20.0,
            max_value=60.0,
            value=42.0,
            step=0.5
        ) / 100
    
    with col3:
        vade_ay = st.selectbox(
            "Vade (Ay)",
            [3, 6, 9, 12, 18, 24, 36],
            index=3
        )
    
    # Hesaplama
    st.markdown("---")
    st.markdown("### 📈 Projeksiyon Sonuçları")
    
    basit_sonuc = calculator.calculate_simple_interest(anapara, faiz_orani, vade_ay)
    bilesik_sonuc = calculator.calculate_compound_interest(anapara, faiz_orani, vade_ay)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Basit Faiz")
        st.metric("Anapara", f"₺{anapara:,.2f}")
        st.metric("Gelecek Değer", f"₺{basit_sonuc['future_value']:,.2f}")
        st.metric("Faiz Geliri", f"₺{basit_sonuc['interest_earned']:,.2f}", 
                  delta=f"+{basit_sonuc['effective_rate']*100:.1f}%")
    
    with col2:
        st.markdown("#### 📊 Bileşik Faiz")
        st.metric("Anapara", f"₺{anapara:,.2f}")
        st.metric("Gelecek Değer", f"₺{bilesik_sonuc['future_value']:,.2f}")
        st.metric("Faiz Geliri", f"₺{bilesik_sonuc['interest_earned']:,.2f}",
                  delta=f"+{bilesik_sonuc['effective_rate']*100:.1f}%")
    
    # Grafik
    st.markdown("---")
    
    aylar = list(range(1, vade_ay + 1))
    basit_degerler = [anapara * (1 + faiz_orani * m / 12) for m in aylar]
    bilesik_degerler = [anapara * ((1 + faiz_orani / 12) ** m) for m in aylar]
    
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=aylar, y=basit_degerler,
        mode="lines+markers", name="Basit Faiz", line=dict(color="blue")
    ))
    
    fig.add_trace(go.Scatter(
        x=aylar, y=bilesik_degerler,
        mode="lines+markers", name="Bileşik Faiz", line=dict(color="green")
    ))
    
    fig.add_hline(y=anapara, line_dash="dash", line_color="gray", annotation_text="Anapara")
    
    fig.update_layout(
        title="Yatırım Değeri Büyümesi",
        xaxis_title="Ay",
        yaxis_title="Değer (₺)"
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_tek_yatirim(calculator: FutureValueCalculator):
    """Tek seferlik yatırım hesaplayıcı."""
    st.subheader("💵 Tek Seferlik Yatırım")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        anapara = st.number_input(
            "Anapara (₺)", min_value=0.0, value=100000.0, step=10000.0, format="%.2f"
        )
    
    with col2:
        bankalar = calculator.get_all_banks()
        if not bankalar:
            bankalar = ["Ziraat", "Vakıfbank", "Akbank", "Garanti", "İşbank", "Yapı Kredi"]
        secili_banka = st.selectbox("Banka", bankalar)
    
    with col3:
        mevcut_oranlar = calculator.get_rates_for_bank(secili_banka)
        vadeler = sorted(set(r.term_months for r in mevcut_oranlar)) if mevcut_oranlar else [3, 6, 12]
        vade_ay = st.selectbox("Vade (Ay)", vadeler)
    
    oran = 0.40
    for r in mevcut_oranlar:
        if r.term_months == vade_ay:
            oran = r.rate_annual
            break
    
    st.info(f"📊 **{secili_banka}** - {vade_ay} Aylık Yıllık Faiz Oranı: **%{oran*100:.1f}**")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Basit Faiz")
        basit_sonuc = calculator.calculate_simple_interest(anapara, oran, vade_ay)
        st.metric("Gelecek Değer", f"₺{basit_sonuc['future_value']:,.2f}")
        st.metric("Faiz Geliri", f"₺{basit_sonuc['interest_earned']:,.2f}")
    
    with col2:
        st.markdown("#### Bileşik Faiz")
        bilesik_sonuc = calculator.calculate_compound_interest(anapara, oran, vade_ay)
        st.metric("Gelecek Değer", f"₺{bilesik_sonuc['future_value']:,.2f}")
        st.metric("Faiz Geliri", f"₺{bilesik_sonuc['interest_earned']:,.2f}")


def render_faiz_oranlari(calculator: FutureValueCalculator):
    """Mevduat faiz oranları tablosu."""
    st.subheader("📋 Mevduat Faiz Oranları")
    
    if not DEPOSIT_RATES:
        st.warning("""
        ⚠️ **Faiz Oranları Tanımlanmamış**
        
        Mevduat faiz oranları henüz sisteme yüklenmemiş.
        """)
        return
    
    st.info("ℹ️ Bu oranlar yaklaşık değerlerdir ve güncel olmayabilir.")
    
    data = []
    for rate in DEPOSIT_RATES:
        data.append({
            "Banka": rate.bank_name,
            "Vade (Ay)": rate.term_months,
            "Yıllık Oran": rate.rate_annual,
        })
    
    df = pd.DataFrame(data)
    
    if df.empty:
        st.warning("⚠️ Gösterilecek faiz oranı bulunamadı.")
        return
    
    pivot = df.pivot(index="Banka", columns="Vade (Ay)", values="Yıllık Oran")
    
    fig = px.imshow(
        pivot.values * 100,
        x=[f"{c} Ay" for c in pivot.columns],
        y=pivot.index.tolist(),
        title="Mevduat Faiz Oranları (%)",
        labels=dict(x="Vade", y="Banka", color="Oran (%)"),
        color_continuous_scale="Greens",
        text_auto=".1f",
        aspect="auto"
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.dataframe(pivot.style.format("{:.1%}"), height=350, use_container_width=True)


def main():
    st.set_page_config(
        page_title="Gelecek Değer - Kariyer.net Finans",
        page_icon="💹",
        layout="wide"
    )
    
    if not check_password():
        st.stop()
    
    st.title("💹 Gelecek Değer Hesaplayıcı")
    st.markdown("**Kariyer.net Finans - Mevduat ve Yatırım Projeksiyon Aracı**")
    st.markdown("---")
    
    calculator = init_calculator()
    
    sekmeler = st.tabs([
        "📊 Veri Bazlı Projeksiyon",
        "💵 Tek Yatırım",
        "📋 Faiz Oranları"
    ])
    
    with sekmeler[0]:
        render_veri_bazli_projeksiyon(calculator)
    
    with sekmeler[1]:
        render_tek_yatirim(calculator)
    
    with sekmeler[2]:
        render_faiz_oranlari(calculator)
    
    # Footer
    st.markdown("---")
    st.caption("© 2026 Kariyer.net Finans Ekibi")


if __name__ == "__main__":
    main()
