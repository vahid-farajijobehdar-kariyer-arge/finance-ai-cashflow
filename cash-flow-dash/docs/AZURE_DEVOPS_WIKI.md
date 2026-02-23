# Finance AI Transformation - POS Komisyon Takip Sistemi

## 📋 Proje Özeti

**Kariyer.net Finans Ekibi** için geliştirilmiş POS komisyon takip ve analiz sistemi. 8 farklı Türk bankasından gelen POS ekstre verilerini otomatik olarak işler, komisyon oranlarını doğrular ve interaktif dashboard üzerinden analiz sunar.

| Özellik | Değer |
|---------|-------|
| **Proje Adı** | Finance AI Transformation |
| **Teknoloji** | Python 3.11, Streamlit, Pandas |
| **Repository** | [GitHub](https://github.com/vahid-farajijobehdar-kariyer-arge/finance-ai-cashflow) |
| **Durum** | ✅ Aktif |
| **Son Güncelleme** | Şubat 2026 |

---

## 🏦 Desteklenen Bankalar

| Banka | Dosya Formatı | Delimiter | Encoding |
|-------|---------------|-----------|----------|
| Akbank | Excel (.xlsx) | - | UTF-8 |
| Garanti BBVA | Excel (.xlsx) | - | UTF-8 |
| Halkbank | Excel (.xlsx) | - | UTF-8 |
| QNB Finansbank | Excel (.xls) | - | UTF-8 |
| Vakıfbank | CSV | `;` | ISO-8859-9 |
| Yapı Kredi | Excel (.xlsx) | - | UTF-8 |
| Ziraat Bankası | Excel (.xlsx) | - | UTF-8 |
| İş Bankası | Excel (.xlsx) | - | UTF-8 |

---

## 🔄 Veri Akışı

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│  Banka Dosyası  │────▶│  BankFileReader  │────▶│ Commission Control│
│  (CSV/Excel)    │     │  (Auto-detect)   │     │  (Rate Verify)    │
└─────────────────┘     └──────────────────┘     └───────────────────┘
                                                          │
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌───────────────────┐
│   Dashboard     │◀────│   Calculator     │◀────│  Filter Success   │
│  (Streamlit)    │     │  (Aggregation)   │     │  (Exclude Refund) │
└─────────────────┘     └──────────────────┘     └───────────────────┘
```

---

## 📊 Dashboard Sayfaları

| Sayfa | Dosya | Açıklama |
|-------|-------|----------|
| 🏠 Ana Sayfa | `app.py` | Giriş ekranı ve özet |
| 📤 Dosya Yükle | `1__Dosya_Yukle.py` | Banka dosyalarını yükle |
| 🔍 Veri Kontrol | `2__Veri_Kontrol.py` | Veri doğrulama |
| 💰 Takip Sistemi | `3__Takip_Sistemi.py` | Ana analiz dashboard'u |
| 💹 Gelecek Değer | `4__Gelecek_Deger.py` | Yatırım hesaplayıcı |
| 🏦 Banka Detay | `5__Banka_Detay.py` | Banka bazlı analiz |
| 📈 Trend Analizi | `6__Trend_Analizi.py` | Aylık/yıllık trendler |
| ⚙️ Ayarlar | `7__Ayarlar.py` | Komisyon oranları ve sütun eşleştirmeleri |

---

## 🚀 Kurulum ve Çalıştırma

### Gereksinimler
- Python 3.11+
- pip veya conda

### Lokal Kurulum

```bash
# Repository'yi klonla
git clone https://dev.azure.com/KariyerNetTech/Applied%20AI%20Projects/_git/Applied%20AI%20Projects
cd Applied\ AI\ Projects/Finance-ai-transformation

# Virtual environment oluştur
python3 -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows

# Bağımlılıkları yükle
pip install -r requirements.txt

# Uygulamayı başlat
./run.sh
# veya
streamlit run src/dashboard/app.py
```

### Docker ile Çalıştırma

```bash
# Docker image oluştur
docker build -t cash-flow-dashboard .

# Container başlat
docker run -p 8501:8501 cash-flow-dashboard

# veya Docker Compose ile
docker-compose up -d
```

---

## 🔐 Kimlik Doğrulama

Dashboard şifre korumalıdır. Şifre yapılandırması:

| Yöntem | Dosya/Değişken | Öncelik |
|--------|----------------|---------|
| Streamlit Secrets | `.streamlit/secrets.toml` | 1 (En yüksek) |
| Environment Variable | `DASHBOARD_PASSWORD` | 2 |
| Varsayılan | Hardcoded | 3 (Fallback) |

**secrets.toml formatı:**
```toml
[passwords]
dashboard_password = "your_secure_password"
```

---

## 💰 Komisyon Oranları

Komisyon oranları `config/commission_rates.yaml` dosyasında saklanır:

```yaml
banks:
  vakifbank:
    aliases: ["T. VAKIFLAR BANKASI T.A.O.", "Vakıfbank"]
    rates:
      1: 0.0336    # Peşin
      2: 0.0499    # 2 Taksit
      3: 0.0690    # 3 Taksit
      # ...
```

### Oran Güncelleme
1. Dashboard → "Komisyon Oranları" sayfası
2. İlgili banka ve taksit seç
3. Yeni oranı gir
4. "Kaydet" tıkla

---

## 🔄 CI/CD Pipeline

### Pipeline Aşamaları

```
┌─────────────┐     ┌─────────────┐     ┌─────────────────┐
│   Build &   │────▶│   Staging   │────▶│   Production    │
│    Test     │     │   Deploy    │     │     Deploy      │
└─────────────┘     └─────────────┘     └─────────────────┘
     │                    │                     │
     │                    │                     │
  main/develop        develop               main branch
```

### Tetikleyiciler

| Branch | Aşama |
|--------|-------|
| `main` | Build → Test → **Production** |
| `develop` | Build → Test → **Staging** |
| PR to `main` | Build → Test only |

### Pipeline Dosyası
`azure-pipelines.yml` - Ana CI/CD yapılandırması

---

## 📁 Proje Yapısı

```
Finance-ai-transformation/
├── src/
│   ├── dashboard/          # Streamlit uygulaması
│   │   ├── app.py          # Ana dashboard
│   │   ├── auth.py         # Kimlik doğrulama
│   │   ├── cache_utils.py  # Cache yönetimi
│   │   └── pages/          # Dashboard sayfaları
│   ├── ingestion/
│   │   └── reader.py       # Banka dosya okuyucu
│   ├── processing/
│   │   ├── calculator.py   # Hesaplama fonksiyonları
│   │   ├── commission_control.py  # Komisyon doğrulama
│   │   └── rate_manager.py # Oran yönetimi
│   └── storage/
│       ├── cache.py        # Cache işlemleri
│       └── metadata.py     # Dosya metadata
├── config/
│   ├── banks.yaml          # Banka sütun eşleştirmeleri
│   ├── commission_rates.yaml  # Komisyon oranları
│   └── settings.yaml       # Genel ayarlar
├── data/
│   ├── raw/                # Ham banka dosyaları
│   ├── processed/          # İşlenmiş veriler
│   └── output/             # Raporlar
├── tests/                  # Unit testler
├── azure-pipelines.yml     # CI/CD
├── Dockerfile              # Docker image
└── docker-compose.yml      # Docker compose
```

---

## 🧪 Test

```bash
# Tüm testleri çalıştır
pytest tests/ -v

# Coverage ile
pytest tests/ -v --cov=src --cov-report=html

# Belirli test dosyası
pytest tests/test_reader.py -v
```

### Test Kapsamı

| Modül | Test Dosyası |
|-------|--------------|
| BankFileReader | `test_reader.py` |
| Calculator | `test_calculator.py` |
| Commission Control | `test_commission_control.py` |

---

## 📞 İletişim

| Rol | İsim | Email |
|-----|------|-------|
| Geliştirici | Vahid Faraji | farajijobehdarvahid@gmail.com |
| Ekip | Kariyer.net Finans | - |

---

## 📝 Sürüm Geçmişi

| Versiyon | Tarih | Değişiklikler |
|----------|-------|---------------|
| 1.0.0 | Şubat 2026 | İlk sürüm - 8 banka desteği |
| 1.1.0 | Şubat 2026 | CI/CD pipeline eklendi |
| 1.2.0 | Şubat 2026 | Docker desteği eklendi |

---

© 2026 Kariyer.net Finans Ekibi - Applied AI Projects
