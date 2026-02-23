┌─────────────────────────────────────────────────────────────────────┐
│                         AKIŞ DİYAGRAMI                              │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│   📁 Ham Veri (CSV/Excel)                                          │
│        ↓                                                            │
│   🔄 Dosya Okuma (BankFileReader)                                  │
│        • Banka otomatik algılama (dosya adından)                   │
│        • Sütun eşleştirme (banks.yaml'dan)                         │
│        • Türkçe karakter/sayı format desteği                       │
│        • transaction_category ayrımı (POS İşlemi / İade)          │
│        ↓                                                            │
│   🔍 Komisyon Kontrol (commission_control.py)                      │
│        • Gerçek oran vs Beklenen oran karşılaştırma                │
│        • Fark varsa işaretleme                                     │
│        ↓                                                            │
│   📊 Hesaplama (calculator.py)                                     │
│        • Banka/Taksit/Ay bazında toplam                            │
│        • Brüt → Komisyon → Net                                     │
│        • İade işlemleri filtreleme                                  │
│        ↓                                                            │
│   🃏 Kart Tipi Analizi                                             │
│        • Kart tipine göre komisyon oranı dağılımı                  │
│        • Peşin / Taksitli ayrımı                                   │
│        ↓                                                            │
│   💰 Dashboard (Streamlit)                                         │
│        • Türkçe para formatı (₺1.234,56) - format_utils.py        │
│        • 6 Tab: Özet, Banka, Taksit, Aylık, Oranlar, Kontrol      │
│        • 8 Banka Detay sayfası (BankDetailPage base class)         │
│        • Ay seçici: Son Excel veri ayına varsayılan                 │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘

UI Yapısı (Streamlit)
Tab	İçerik
📊 Özet	Tek Çekim vs Taksit ayrımı, toplam metrikler
🏦 Banka	Banka bazında çekim/komisyon/net dağılımı
💳 Taksit	2-12 taksit dağılım analizi
📅 Aylık	Aylık trend grafikleri
📊 Oranlar	Komisyon oranları heatmap
🔍 Kontrol	⭐ Gerçek vs Beklenen komisyon doğrulama

Sayfa Yapısı
Sayfa	Dosya	Açıklama
❓ Nasıl Kullanılır	0__Nasil_Kullanilir.py	Kullanım kılavuzu
📤 Dosya Yükle	1__Dosya_Yukle.py	Dosya yükleme/yönetim
🔍 Veri Kontrol	2__Veri_Kontrol.py	Veri kalite kontrolü
📋 Takip Sistemi	3__Takip_Sistemi.py	İşlem takip sistemi
💰 Gelecek Değer	4__Gelecek_Deger.py	Gelecek değer hesaplama
🏦 Banka Detay	5__Banka_Detay.py	Banka bazlı detay
📊 Konsolide Rapor	5__Konsolide_Rapor.py	Konsolide raporlama
📈 Trend Analizi	6__Trend_Analizi.py	Trend analizi
⚙️ Ayarlar	7__Ayarlar.py	Uygulama ayarları
🏦 10-17 Detay	10-17__*_Detay.py	8 banka için özel detay sayfaları

Banka Detay Sayfası Özellikleri (BankDetailPage)
• Ay seçici → son Excel veri ayına varsayılan (takvim ayı değil)
• Peşin/Taksitli ayrımı (metrikler + tablo)
• 🃏 Kart Tipi Bazında Oran Dağılımı tablosu
• Komisyon kontrol (beklenen vs gerçek oran)
• Tüm tutarlar Türk Lirası formatında (₺1.234,56)

Turkish Formatting Pipeline
format_utils.py → tl(), _tl(), _tl0()
• Python: 1,234.89 → Türkçe: 1.234,89 ₺
• st.metric(), DataFrame.style.format() tüm sayfalarda uygulanır


┌─────────────────────────────────────────────────────────────────┐
│  📤 Yeni Dosya Yükle                                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                                                             ││
│  │     CSV veya Excel dosyalarını buraya sürükleyin           ││
│  │              veya tıklayarak seçin                          ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Desteklenen bankalar: Akbank, Garanti, Halkbank, İşbank,      │
│  QNB, Vakıfbank, YKB, Ziraat                                   │
│                                                                 │
│  [Yükle ve Analiz Et]                                          │
└─────────────────────────────────────────────────────────────────┘

