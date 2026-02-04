"""
📖 Nasıl Kullanılır - Kullanım Kılavuzu

POS Komisyon Takip Sistemi kullanım rehberi.

© 2026 Kariyer.net Finans Ekibi
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()
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
st.markdown("**POS Komisyon Takip Sistemi Kullanım Kılavuzu**")
st.markdown("---")

# Quick Start
st.header("🚀 Hızlı Başlangıç")

st.markdown("""
### 1. Dosya Yükleme
1. Sol menüden **📤 Dosya Yükle** sayfasına gidin
2. Banka ekstre dosyalarınızı (Excel veya CSV) sürükleyip bırakın
3. Banka ve tarih bilgisini seçin
4. **Kaydet** butonuna tıklayın

### 2. Veri Kontrolü
1. **🔍 Veri Kontrol** sayfasından yüklenen verileri doğrulayın
2. Eksik veya hatalı satırları inceleyin
3. Gerekirse dosyayı düzeltip tekrar yükleyin

### 3. Analiz
1. **💰 Takip Sistemi** sayfasından özet metrikleri görüntüleyin
2. **🏦 Banka Detay** sayfasından banka bazlı analiz yapın
3. **📈 Trend Analizi** sayfasından aylık trendleri inceleyin
""")

st.markdown("---")

# Supported Banks
st.header("🏦 Desteklenen Bankalar")

banks_data = {
    "Banka": ["Akbank", "Garanti BBVA", "Halkbank", "QNB Finansbank", "Vakıfbank", "Yapı Kredi", "Ziraat Bankası", "İş Bankası"],
    "Dosya Formatı": ["Excel (.xlsx)", "Excel (.xlsx)", "Excel (.xlsx)", "Excel (.xls)", "CSV", "Excel (.xlsx)", "Excel (.xlsx)", "Excel (.xlsx)"],
    "Özel Not": ["-", "-", "-", "-", "Noktalı virgül (;) ayırıcı", "-", "-", "-"]
}

import pandas as pd
st.dataframe(pd.DataFrame(banks_data), width="stretch", hide_index=True)

st.markdown("---")

# Page Descriptions
st.header("📑 Sayfa Açıklamaları")

pages = [
    ("📤 Dosya Yükle", "Banka ekstre dosyalarını sisteme yükleyin. Mükerrer dosya kontrolü otomatik yapılır."),
    ("🔍 Veri Kontrol", "Yüklenen verilerin kalitesini kontrol edin. Eksik/hatalı satırları görün."),
    ("💰 Takip Sistemi", "Özet metrikler, banka dağılımları ve komisyon analizleri."),
    ("💹 Gelecek Değer", "Yatırım ve faiz hesaplamaları için gelecek değer hesaplayıcı."),
    ("🏦 Banka Detay", "Seçilen banka için detaylı işlem analizi."),
    ("📈 Trend Analizi", "Aylık ve yıllık komisyon trendleri, karşılaştırmalar."),
    ("⚙️ Ayarlar", "Komisyon oranları ve Excel sütun eşleştirmelerini yönetin.")
]

for page, desc in pages:
    with st.expander(page):
        st.write(desc)

st.markdown("---")

# Tips
st.header("💡 İpuçları")

st.info("""
**🔄 Veri Yenileme:** Yeni dosya yüklediğinizde tüm sayfalar otomatik olarak güncellenir.

**📊 Filtreleme:** Çoğu sayfada tarih ve banka filtreleri mevcuttur.

**💾 Export:** Analiz sonuçlarını Excel veya CSV olarak indirebilirsiniz.

**🔒 Güvenlik:** Oturum 24 saat boyunca açık kalır.
""")

st.markdown("---")

# Contact
st.header("📞 Destek")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    **Teknik Destek:**
    - Email: vahid.farajijobehdar@kariyer.net
    """)

with col2:
    st.markdown("""
    **Dokümantasyon:**
    - Azure DevOps Wiki
    - README.md
    """)

# Footer
st.markdown("---")
st.caption("© 2026 Kariyer.net Finans Ekibi")
