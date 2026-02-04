"""
📖 Nasıl Kullanılır - Kullanım Kılavuzu

POS Komisyon Takip Sistemi detaylı kullanım rehberi.

© 2026 Kariyer.net Finans Ekibi
"""

import streamlit as st
import pandas as pd
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
st.markdown("**POS Komisyon Takip Sistemi - Detaylı Kullanım Kılavuzu**")

# Sistem tanıtımı
st.info("""
🎯 **Sistem Amacı:** Kariyer.net POS işlemlerinden kesilen banka komisyonlarını takip etmek, 
beklenen oranlarla karşılaştırmak ve farkları analiz etmek.

📊 **8 Banka Desteği:** Akbank, Garanti, Halkbank, İşbank, QNB, Vakıfbank, YKB, Ziraat
""")

st.markdown("---")

# =============================================================================
# HIZLI BAŞLANGIÇ
# =============================================================================
st.header("🚀 Hızlı Başlangıç (3 Adım)")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    ### 1️⃣ Dosya Yükle
    
    1. **📤 Dosya Yükle** sayfasına git
    2. Excel/CSV dosyasını sürükle
    3. Banka otomatik tanınır
    4. **Kaydet** butonuna tıkla
    
    ✅ Mükerrer dosya kontrolü otomatik
    """)

with col2:
    st.markdown("""
    ### 2️⃣ Kontrol Et
    
    1. **🔍 Veri Kontrol** sayfasına git
    2. Yüklenen dosyaları gör
    3. Eksik veri uyarılarını incele
    4. Gerekirse düzelt ve tekrar yükle
    
    ✅ Veri kalitesi raporları
    """)

with col3:
    st.markdown("""
    ### 3️⃣ Analiz Yap
    
    1. **💰 Takip Sistemi** → Genel özet
    2. **🏦 Banka Detay** → Banka bazlı
    3. **📈 Trend Analizi** → Aylık trend
    4. **📥 Export** → Excel indir
    
    ✅ Komisyon fark analizi
    """)

st.markdown("---")

# =============================================================================
# DETAYLI SAYFA AÇIKLAMALARI
# =============================================================================
st.header("📑 Sayfa Açıklamaları")

# Ana Sayfalar
st.subheader("🏠 Ana Sayfalar")

with st.expander("📤 Dosya Yükle - Banka Ekstre Yükleme", expanded=True):
    st.markdown("""
    **Amaç:** Bankalardan gelen POS ekstre dosyalarını sisteme yüklemek.
    
    #### 📁 Desteklenen Dosya Formatları
    | Banka | Format | Encoding | Ayırıcı |
    |-------|--------|----------|---------|
    | Akbank | Excel (.xlsx) | UTF-8 | - |
    | Garanti | Excel (.xlsx) | UTF-8 | - |
    | Halkbank | Excel (.xlsx) | UTF-8 | - |
    | İşbank | Excel (.xlsx) | UTF-8 | - |
    | QNB | Excel (.xls) | UTF-8 | - |
    | Vakıfbank | **CSV** | ISO-8859-9 | Noktalı virgül (;) |
    | YKB | Excel (.xlsx) | UTF-8 | - |
    | Ziraat | Excel (.xlsx) | UTF-8 | - |
    
    #### 🔄 Yükleme Adımları
    1. **Dosya Seç:** Dosyayı sürükle veya "Browse files" tıkla
    2. **Banka Tanıma:** Sistem dosyadan bankayı otomatik tanır
    3. **Dönem Seç:** Ay ve yıl bilgisini seç
    4. **Önizle:** Veri önizlemesini kontrol et
    5. **Kaydet:** "💾 Kaydet" butonuna tıkla
    
    #### ⚠️ Dikkat Edilecekler
    - **Mükerrer Kontrol:** Aynı dosya tekrar yüklenemez
    - **Dosya Adı:** Banka adını içermeli (örn: `akbank_ocak2026.xlsx`)
    - **Klasör Yapısı:** Dosyalar `BANKA/YYYY-MM/` altına kaydedilir
    """)

with st.expander("🔍 Veri Kontrol - Kalite Kontrolü"):
    st.markdown("""
    **Amaç:** Yüklenen verilerin kalitesini doğrulamak.
    
    #### 📊 Kontrol Edilen Metrikler
    - **Dosya Sayısı:** Yüklenen toplam dosya
    - **İşlem Sayısı:** Toplam satır sayısı
    - **Eksik Veri:** Boş hücre oranları
    - **Tarih Aralığı:** En eski - en yeni tarih
    
    #### ⚠️ Uyarı Türleri
    | Uyarı | Anlam | Çözüm |
    |-------|-------|-------|
    | 🔴 Kritik | Veri okunamadı | Dosyayı kontrol et |
    | 🟡 Uyarı | Eksik sütun var | Ayarları kontrol et |
    | 🟢 Bilgi | Bazı satırlar boş | Normal olabilir |
    
    #### 🔄 Günlük Boşluk Analizi
    - Hafta içi eksik günler tespit edilir
    - Hafta sonları hariç tutulur
    """)

with st.expander("💰 Takip Sistemi - Genel Özet"):
    st.markdown("""
    **Amaç:** Tüm bankaların komisyon özetini görmek.
    
    #### 📊 Gösterilen Metrikler
    
    **Üst Kart Metrikleri:**
    | Metrik | Açıklama |
    |--------|----------|
    | 💵 Toplam Brüt | Tüm çekimlerin toplamı |
    | 💳 Toplam Komisyon | Kesilen toplam komisyon |
    | 💰 Toplam Net | Hesaba geçen net tutar |
    | 📈 Ortalama Oran | Genel komisyon oranı |
    
    **Sekmeler:**
    - **📊 Özet:** Genel bakış
    - **🏦 Banka:** Banka bazlı dağılım
    - **📅 Taksit:** Taksit sayısına göre
    - **📆 Aylık:** Aylık trend
    - **🔍 Kontrol:** Komisyon fark analizi
    
    #### ⚠️ Komisyon Fark Analizi
    Ayarlardaki beklenen oranlar ile gerçek oranlar karşılaştırılır:
    - ✅ **Eşleşen:** Fark < %0.1
    - 🔴 **Fazla Ödeme:** Gerçek > Beklenen
    - 🟢 **Az Ödeme:** Gerçek < Beklenen
    """)

# Banka Detay Sayfaları
st.subheader("🏦 Banka Detay Sayfaları")

with st.expander("🏦 Banka Bazlı Analiz (8 Sayfa)"):
    st.markdown("""
    **Her banka için ayrı detay sayfası mevcuttur:**
    
    | Sayfa | Banka |
    |-------|-------|
    | Akbank Detay | Akbank T.A.Ş. |
    | Garanti Detay | Garanti BBVA |
    | Halkbank Detay | Halkbank |
    | İşbank Detay | Türkiye İş Bankası |
    | QNB Detay | QNB Finansbank |
    | Vakıfbank Detay | Vakıfbank |
    | YKB Detay | Yapı Kredi |
    | Ziraat Detay | Ziraat Bankası |
    
    #### 📊 Her Sayfada Bulunanlar
    
    1. **📊 Özet Metrikler**
       - İşlem sayısı, brüt, komisyon, net, oran
    
    2. **💵 Peşin vs Taksitli**
       - Tek çekim ve taksitli karşılaştırma
       - Her biri için ayrı metrikler
    
    3. **⚠️ Komisyon Fark Analizi**
       - Gerçek vs beklenen komisyon farkları
       - Taksit bazında fark tablosu
       - Fark grafiği (pozitif/negatif)
    
    4. **📅 Aylık Trend**
       - Çekim ve komisyon grafiği
       - Çift eksenli (brüt + komisyon)
    
    5. **📊 Taksit Dağılımı**
       - Taksit bazında tutar dağılımı
       - Pasta ve bar grafikleri
    
    6. **📋 İşlem Detayları**
       - Tüm işlemlerin listesi
       - 500 satır önizleme
    
    7. **📥 Export**
       - CSV ve Excel indirme
    """)

# Diğer Sayfalar
st.subheader("📈 Analiz ve Ayarlar")

with st.expander("💹 Gelecek Değer - Yatırım Hesaplayıcı"):
    st.markdown("""
    **Amaç:** Net tutarların mevduata yatırılması durumunda gelecek değer hesabı.
    
    #### 💰 Hesaplama Türleri
    - **Basit Faiz:** Anapara × Oran × Süre
    - **Bileşik Faiz:** Anapara × (1 + Oran)^Süre
    
    #### 🏦 Mevduat Oranları
    Ayarlar sayfasından tanımlanan banka mevduat oranları kullanılır.
    
    #### 📊 Özellikler
    - Dönem bazlı toplam hesaplama
    - Banka ve vade seçimi
    - Karşılaştırmalı grafik
    """)

with st.expander("📈 Trend Analizi - Dönemsel Karşılaştırma"):
    st.markdown("""
    **Amaç:** Aylık ve banka bazlı trendleri analiz etmek.
    
    #### 📊 Grafikler
    - **Aylık Trend:** Çizgi grafik
    - **Banka Karşılaştırması:** Bar grafik
    - **Isı Haritası:** Banka × Ay matrisi
    
    #### 📋 Tablolar
    - Aylık detay tablosu
    - Banka bazlı özet
    """)

with st.expander("⚙️ Ayarlar - Sistem Konfigürasyonu"):
    st.markdown("""
    **Amaç:** Komisyon oranları ve sütun eşleştirmelerini yönetmek.
    
    #### 💳 Komisyon Oranları Sekmesi
    
    **Görüntüleme:**
    - Tüm bankaların taksit bazlı oranları
    - Peşin, 2, 3, 4... 12 taksit oranları
    
    **Düzenleme:**
    1. Banka seç
    2. Taksit oranlarını gir (% olarak)
    3. "Kaydet" tıkla
    
    **İçe/Dışa Aktarma:**
    - YAML dosyasından içe aktar
    - URL'den içe aktar
    - YAML/CSV olarak dışa aktar
    
    #### 💰 Mevduat Oranları Sekmesi
    - Banka mevduat faiz oranları
    - 3, 6, 12 aylık vadeler
    
    #### 📊 Excel Sütunları Sekmesi
    - Her banka için sütun eşleştirmeleri
    - `banks.yaml` dosyasından okur
    
    #### 📜 Değişiklik Geçmişi
    - Tüm oran değişiklikleri loglanır
    - Tarih, kullanıcı, eski/yeni değer
    """)

st.markdown("---")

# =============================================================================
# KOMİSYON FARK ANALİZİ
# =============================================================================
st.header("⚠️ Komisyon Fark Analizi - Detaylı Açıklama")

st.markdown("""
Bu sistem, bankaların kestiği gerçek komisyonları, ayarlarda tanımlı beklenen oranlarla karşılaştırır.
""")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
    ### 📥 Veri Kaynakları
    
    **1. Gerçek Komisyon (Dosyadan)**
    - Banka ekstre dosyasından okunan değer
    - `commission_amount` sütunu
    - Bazı bankalar oranı da verir
    
    **2. Beklenen Komisyon (Ayarlardan)**
    - `config/commission_rates.yaml`
    - Taksit bazlı tanımlı oranlar
    - Sistem: `brüt × oran = beklenen`
    """)

with col2:
    st.markdown("""
    ### 🔄 Hesaplama Mantığı
    
    ```
    Gerçek Oran = Komisyon / Brüt Tutar
    Beklenen Oran = Ayarlardan (taksit bazlı)
    Beklenen Komisyon = Brüt × Beklenen Oran
    
    Fark = Gerçek Komisyon - Beklenen Komisyon
    
    Eşleşme = |Fark| < %0.1 × Brüt
    ```
    """)

st.markdown("""
### 📊 Kontrol Sütunları

| Sütun | Açıklama |
|-------|----------|
| `commission_rate` | Dosyadan hesaplanan gerçek oran |
| `rate_expected` | Ayarlardan alınan beklenen oran |
| `commission_expected` | Brüt × Beklenen Oran |
| `commission_diff` | Gerçek - Beklenen fark |
| `rate_match` | Fark tolerans içinde mi? |
| `rate_source` | Oran kaynağı (file/calculated) |

### ⚠️ Fark Durumları

| Durum | Anlamı | Aksiyon |
|-------|--------|---------|
| ✅ Eşleşiyor | Fark < %0.1 | Normal |
| 🔴 Fazla Ödeme | Banka fazla kesmiş | Bankaya itiraz et |
| 🟢 Az Ödeme | Banka az kesmiş | Fark kaydedilir |
| ⚪ Oran Yok | Ayarlarda tanım yok | Ayarlara ekle |
""")

st.markdown("---")

# =============================================================================
# DESTEKLENEN BANKALAR
# =============================================================================
st.header("🏦 Desteklenen Bankalar")

banks_detailed = pd.DataFrame({
    "Banka": ["Akbank", "Garanti BBVA", "Halkbank", "İş Bankası", "QNB Finansbank", "Vakıfbank", "Yapı Kredi", "Ziraat Bankası"],
    "Kod": ["akbank", "garanti", "halkbank", "isbank", "qnb", "vakifbank", "ykb", "ziraat"],
    "Dosya Formatı": ["Excel (.xlsx)", "Excel (.xlsx)", "Excel (.xlsx)", "Excel (.xlsx)", "Excel (.xls)", "CSV", "Excel (.xlsx)", "Excel (.xlsx)"],
    "Encoding": ["UTF-8", "UTF-8", "UTF-8", "UTF-8", "UTF-8", "ISO-8859-9", "UTF-8", "UTF-8"],
    "Özel Not": ["-", "-", "-", "-", "Eski Excel formatı", "Noktalı virgül ayırıcı", "-", "-"]
})

st.dataframe(banks_detailed, width="stretch", hide_index=True)

st.markdown("""
### 📁 Dosya Adlandırma Kuralları

Sistem banka adını dosya adından otomatik tanır. Önerilen format:

```
BankaAdı_YYYY-MM_açıklama.xlsx
```

**Örnekler:**
- `Akbank_2026-01_POS.xlsx` ✅
- `garanti_ocak.xlsx` ✅
- `VAKIFBANK_rapor.csv` ✅
- `rapor.xlsx` ❌ (banka tanınamaz)
""")

st.markdown("---")

# =============================================================================
# DOSYA KLASÖR YAPISI
# =============================================================================
st.header("📁 Dosya ve Klasör Yapısı")

st.code("""
data/
├── raw/                          # Ham banka dosyaları
│   ├── AKBANK/
│   │   ├── 2026-01/
│   │   │   └── akbank_ocak.xlsx
│   │   └── 2026-02/
│   │       └── akbank_subat.xlsx
│   ├── GARANTI/
│   ├── HALKBANK/
│   ├── ISBANK/
│   ├── QNB/
│   ├── VAKIFBANK/
│   ├── YKB/
│   └── ZIRAAT/
│
├── metadata/
│   └── files_metadata.json       # Dosya takip bilgileri
│
└── output/                       # Export dosyaları

config/
├── banks.yaml                    # Banka sütun eşleştirmeleri
├── commission_rates.yaml         # Komisyon oranları
├── rate_history.json             # Oran değişiklik geçmişi
└── settings.yaml                 # Genel ayarlar
""", language="text")

st.markdown("---")

# =============================================================================
# İPUÇLARI VE EN İYİ UYGULAMALAR
# =============================================================================
st.header("💡 İpuçları ve En İyi Uygulamalar")

tip1, tip2 = st.columns(2)

with tip1:
    st.success("""
    **✅ Yapılması Gerekenler**
    
    - Dosyaları aylık düzenli yükleyin
    - Yüklemeden önce Veri Kontrol sayfasını kullanın
    - Komisyon oranlarını güncel tutun
    - Fark raporlarını düzenli inceleyin
    - Export özelliğini yedekleme için kullanın
    """)

with tip2:
    st.error("""
    **❌ Kaçınılması Gerekenler**
    
    - Aynı dosyayı tekrar yüklemeyin (mükerrer)
    - Dosya adını değiştirmeden yüklemeyin
    - Oranları güncellemeden analiz yapmayın
    - Excel dosyalarını düzenleyip kaydetmeyin
    - Sistem dosyalarını silmeyin (config/)
    """)

st.markdown("---")

# =============================================================================
# KLAVYE KISAYOLLARI VE NAVİGASYON
# =============================================================================
st.header("⌨️ Navigasyon")

st.markdown("""
### 📱 Sidebar Menüsü

Sol taraftaki menüden sayfalara erişebilirsiniz:

| Bölüm | Sayfalar |
|-------|----------|
| **Ana İşlemler** | Dosya Yükle, Veri Kontrol |
| **Analiz** | Takip Sistemi, Gelecek Değer |
| **Banka Detay** | 8 banka sayfası |
| **Raporlama** | Trend Analizi |
| **Yönetim** | Ayarlar |

### 🔄 Veri Yenileme

- Yeni dosya yüklendiğinde otomatik güncellenir
- Manuel yenileme: Tarayıcıda **F5** veya **⌘+R**
- Cache temizleme: Ayarlar sayfasından
""")

st.markdown("---")

# =============================================================================
# SSS - SIKÇA SORULAN SORULAR
# =============================================================================
st.header("❓ Sıkça Sorulan Sorular")

with st.expander("Dosyam yüklenmiyor, ne yapmalıyım?"):
    st.markdown("""
    1. Dosya formatını kontrol edin (Excel veya CSV)
    2. Dosya adının banka adını içerdiğinden emin olun
    3. Vakıfbank için CSV ve noktalı virgül ayırıcı kullanın
    4. Dosyanın bozuk olmadığını doğrulayın
    5. Tarayıcı önbelleğini temizleyin
    """)

with st.expander("Komisyon farkı neden çıkıyor?"):
    st.markdown("""
    Fark çıkma nedenleri:
    1. **Oran Güncel Değil:** Ayarlardaki oranlar eski olabilir
    2. **Özel Anlaşma:** Bankayla farklı oran anlaşması olabilir
    3. **Promosyon:** Geçici indirimli oran uygulanmış olabilir
    4. **Yuvarlamalar:** Kuruş farklılıkları normal
    
    **Çözüm:** Ayarlar sayfasından oranları güncelleyin
    """)

with st.expander("Eski verileri nasıl silebilirim?"):
    st.markdown("""
    1. **📤 Dosya Yükle** sayfasına gidin
    2. Alt kısımda "Dosya Yönetimi" bölümünü bulun
    3. Silmek istediğiniz dosyanın yanındaki 🗑️ simgesine tıklayın
    4. Onaylayın
    
    ⚠️ **Dikkat:** Silinen veriler geri alınamaz!
    """)

with st.expander("Export dosyaları nereye kaydediliyor?"):
    st.markdown("""
    Export butonları tarayıcınızın indirme klasörüne dosya indirir.
    
    Dosya formatları:
    - **CSV:** Virgülle ayrılmış değerler
    - **Excel:** .xlsx formatı (modern Excel)
    """)

with st.expander("Yeni banka nasıl eklenir?"):
    st.markdown("""
    Yeni banka eklemek için:
    
    1. `config/banks.yaml` dosyasına banka tanımı ekleyin
    2. `config/commission_rates.yaml` dosyasına oranları ekleyin
    3. Uygulamayı yeniden başlatın
    
    Detaylı bilgi için README.md dosyasına bakın.
    """)

st.markdown("---")

# =============================================================================
# VERSİYON VE DESTEK
# =============================================================================
st.header("📞 Versiyon ve Destek")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("""
    **📦 Sistem Bilgisi**
    - Versiyon: 2.0.0
    - Python: 3.13+
    - Streamlit: 1.53+
    - Son Güncelleme: Şubat 2026
    """)

with col2:
    st.markdown("""
    **👨‍💻 Geliştirici**
    - Vahid Faraji Jobehdar
    - vahid.farajijobehdar@kariyer.net
    - Kariyer.net Finans Ekibi
    """)

with col3:
    st.markdown("""
    **📚 Kaynaklar**
    - GitHub Repository
    - Azure DevOps Wiki
    - README.md
    - spec/specification.md
    """)

# Footer
st.markdown("---")
st.caption("© 2026 Kariyer.net Finans Ekibi - POS Komisyon Takip Sistemi v2.0")
