"""
📖 Nasıl Kullanılır - Kariyer.net Finans POS Komisyon Takip Sistemi

Kullanım kılavuzu ve sistem bilgileri.
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from auth import check_password

st.set_page_config(
    page_title="Nasıl Kullanılır - POS Komisyon",
    page_icon="📖",
    layout="wide"
)

# Authentication
if not check_password():
    st.stop()

st.title("📖 Nasıl Kullanılır")
st.markdown("**Kariyer.net Finans - POS Komisyon Takip Sistemi**")
st.markdown("---")

# Quick Start
st.header("🚀 Hızlı Başlangıç")

st.markdown("""
### 1️⃣ Dosya Yükleme
1. Sol menüden **"📤 Dosya Yükle"** sayfasına gidin
2. Banka POS ekstre dosyalarınızı (Excel/CSV) yükleyin
3. Sistem otomatik olarak bankayı tanır ve sütunları eşleştirir

### 2️⃣ Ana Panel'i İnceleyin
- **Ana Panel** (💰) sayfasında tüm verilerin özeti görünür
- Banka bazlı, taksit bazlı ve aylık analizler mevcuttur

### 3️⃣ Raporları İndirin
- **"📊 Detay Rapor"** sayfasından Excel formatında rapor alabilirsiniz
- Aylık bazda banka komisyon analizleri indirilebilir
""")

st.markdown("---")

# Supported Banks
st.header("🏦 Desteklenen Bankalar")

banks_data = {
    "Banka": ["Ziraat Bankası", "Akbank", "Garanti BBVA", "Halkbank", "QNB Finansbank", "Vakıfbank", "Yapı Kredi", "İş Bankası"],
    "Dosya Formatı": ["Excel (.xlsx)", "Excel (.xlsx)", "Excel (.xlsx)", "Excel (.xlsx)", "Excel (.xls)", "CSV (;)", "Excel (.xlsx)", "Excel (.xlsx)"],
    "Otomatik Tanıma": ["✅ Dosya adında 'ziraat'", "✅ Dosya adında 'akbank'", "✅ Dosya adında 'garanti'", "✅ Dosya adında 'halk'", "✅ Dosya adında 'qnb' veya 'finans'", "✅ Dosya adında 'vakıf'", "✅ Dosya adında 'ykb' veya 'yapı'", "✅ Dosya adında 'isbank' veya 'iş'"]
}

import pandas as pd
st.dataframe(pd.DataFrame(banks_data), use_container_width=True, hide_index=True)

st.markdown("---")

# Page Descriptions
st.header("📑 Sayfa Açıklamaları")

pages_info = """
| Sayfa | Açıklama |
|-------|----------|
| 💰 **Ana Panel** | Tüm verilerin özeti, banka/taksit/aylık analizler |
| 📤 **Dosya Yükle** | Banka ekstre dosyalarını yükle/sil |
| 💹 **Gelecek Değer** | Yatırım getirisi ve nakit akış hesaplama |
| 🔍 **Veri Kontrol** | Komisyon oranlarını beklenen değerlerle karşılaştır |
| 🏦 **Banka Detay** | Banka bazlı detaylı analiz ve grafikler |
| 📊 **Detay Rapor** | Excel formatında aylık detay raporları |
| 💳 **Komisyon Oranları** | Komisyon oranlarını görüntüle/düzenle/içe aktar |
"""
st.markdown(pages_info)

st.markdown("---")

# Terminology
st.header("📚 Terimler Sözlüğü")

terms = """
| Terim | Açıklama |
|-------|----------|
| **Brüt Tutar** | Müşteriden çekilen toplam tutar (komisyon dahil) |
| **Komisyon** | Bankaya ödenen hizmet bedeli |
| **Net Tutar** | Brüt Tutar - Komisyon = Hesaba geçen tutar |
| **Peşin** | Tek çekim işlem (taksit yok) |
| **Taksit** | 2-12 ay arası taksitli işlem |
| **Komisyon Oranı** | Komisyon / Brüt Tutar (%) |
| **Beklenen Oran** | Sözleşmede belirlenen oran |
| **Oran Farkı** | Gerçekleşen Oran - Beklenen Oran |
"""
st.markdown(terms)

st.markdown("---")

# Tips
st.header("💡 İpuçları")

st.info("""
**📁 Dosya İsimlendirme:**
- Dosya adında banka ismini kullanın (örn: `Akbank_Ocak2026.xlsx`)
- Sistem otomatik olarak bankayı tanır

**🔄 Veri Güncelleme:**
- Yeni dosya yüklediğinizde tüm önbellek otomatik temizlenir
- Sayfa yenilemesine gerek yoktur

**📊 Raporlar:**
- Detay Rapor sayfasından Excel formatında tüm aylık verileri indirebilirsiniz
- Komisyon Oranları sayfasından güncel oranları dışa aktarabilirsiniz
""")

st.markdown("---")

# FAQ
st.header("❓ Sık Sorulan Sorular")

with st.expander("Dosyam neden tanınmadı?"):
    st.markdown("""
    - Dosya adında banka isminin geçtiğinden emin olun
    - Desteklenen formatlardan birini kullanın (xlsx, xls, csv)
    - Vakıfbank için CSV dosyası olmalıdır
    """)

with st.expander("Komisyon oranları nereden geliyor?"):
    st.markdown("""
    - Oranlar `config/commission_rates.yaml` dosyasında tanımlıdır
    - "Komisyon Oranları" sayfasından görüntüleyip düzenleyebilirsiniz
    - URL veya dosyadan toplu import yapabilirsiniz
    """)

with st.expander("Veriler güvenli mi?"):
    st.markdown("""
    - Tüm veriler yerel sunucuda işlenir
    - Şifre koruması mevcuttur
    - Yüklenen dosyalar sadece `data/raw/` klasöründe saklanır
    """)

st.markdown("---")

# Credits
st.header("👥 Geliştirici Ekip")

st.success("""
### Kariyer.net Finans Ekibi

**POS Komisyon Takip Sistemi v2.0**

Bu uygulama Kariyer.net Finans Departmanı için özel olarak geliştirilmiştir.
Banka POS ekstre verilerinin analizi, komisyon kontrolü ve raporlama işlemlerini
otomatize etmek amacıyla tasarlanmıştır.

---

© 2026 Kariyer.net - Finans Ekibi

🔧 Teknik Destek: vahid.farajijobehdar@kariyer.net
""")

# Version Info
st.markdown("---")
st.caption("""
**Sistem Bilgileri:**
- Versiyon: 2.0.0
- Son Güncelleme: Şubat 2026
- Python: 3.13+
- Framework: Streamlit
""")
