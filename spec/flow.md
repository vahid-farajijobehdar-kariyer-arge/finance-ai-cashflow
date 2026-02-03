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
│        ↓                                                            │
│   🔍 Komisyon Kontrol (commission_control.py)                      │
│        • Gerçek oran vs Beklenen oran karşılaştırma                │
│        • Fark varsa işaretleme                                     │
│        ↓                                                            │
│   📊 Hesaplama (calculator.py)                                     │
│        • Banka/Taksit/Ay bazında toplam                            │
│        • Brüt → Komisyon → Net                                     │
│        ↓                                                            │
│   💰 Dashboard (Streamlit)                                         │
│        • 6 Tab: Özet, Banka, Taksit, Aylık, Oranlar, Kontrol       │
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
🆕 Drag & Drop Özelliği (Eklenecek)


┌─────────────────────────────────────────────────────────────────┐
│  📤 Yeni Dosya Yükle                                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                                                             ││
│  │     CSV veya Excel dosyalarını buraya sürükleyin           ││
│  │              veya tıklayarak seçin                          ││
│  │                                                             ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                 │
│  Desteklenen bankalar: Vakıfbank, Akbank, Garanti, Halkbank... │
│                                                                 │
│  [Yükle ve Analiz Et]                                          │
└─────────────────────────────────────────────────────────────────┘

