# Cash Flow Dashboard - Project Specification

**Date / Tarih:** January 27, 2026 (Last updated: June 2025)  
**Stakeholders / Paydaşlar:** Emre Deniz, Vahid Farajijobehdar, İlknur Köseoğlu Sarı

---

## 1. Problem Statement / Problem Tanımı

### 1.1 Current Pain Points / Mevcut Sorunlar

| EN | TR |
|----|-----|
| Finance team spends significant time manually tracking cash flow from **8 different bank POS systems** | Finans ekibi **8 farklı banka POS sisteminden** nakit akışını manuel takip etmek için önemli zaman harcıyor |

**Current Process / Mevcut Süreç:**

| Step | EN | TR |
|------|-----|-----|
| 1 | Manual data extraction from bank POS portals | Banka POS portallarından manuel veri çekimi |
| 2 | Copy-paste operations into Excel | Excel'e kopyala-yapıştır işlemleri |
| 3 | Manual formula creation for calculations | Hesaplamalar için manuel formül oluşturma |
| 4 | Manual validation through control mechanisms | Kontrol mekanizmalarıyla manuel doğrulama |

### 1.2 Core Problem / Ana Problem

| EN | TR |
|----|-----|
| Transform a time-consuming, error-prone manual Excel workflow into an automated Python-based cash flow tracking system | Zaman alan, hataya açık manuel Excel iş akışını otomatik Python tabanlı nakit akış takip sistemine dönüştürmek |

### 1.3 Business Impact / İş Etkisi

| EN | TR |
|----|-----|
| High time investment for monthly reconciliation | Aylık mutabakat için yüksek zaman yatırımı |
| Risk of human error in copy-paste and formulas | Kopyala-yapıştır ve formüllerde insan hatası riski |
| Delayed visibility into cash position | Nakit pozisyonuna gecikmeli görünürlük |
| Difficulty scaling to additional banks | Ek bankalara ölçekleme zorluğu |

---

## 2. Problem Breakdown / Problem Ayrıştırma

### 2.1 Sub-Problems to Solve / Çözülecek Alt Problemler

| # | Problem (EN) | Problem (TR) | Input Needed | Output Expected |
|---|--------------|--------------|--------------|-----------------|
| P1 | Read bank POS exports (different formats per bank) | Banka POS dışa aktarımlarını oku (her banka farklı format) | Excel files from 8 banks | Normalized DataFrame |
| P2 | Map different column names to standard schema | Farklı sütun isimlerini standart şemaya eşle | Column mapping config | Unified column names |
| P3 | Filter only successful transactions | Sadece başarılı işlemleri filtrele | Raw transactions | Filtered transactions |
| P4 | Calculate commission and net amounts | Komisyon ve net tutarları hesapla | Gross amount, commission rate | Net amount per transaction |
| P5 | Track blocked/pending amounts | Bloke/bekleyen tutarları takip et | Transaction status | Blocked amount per bank |
| P6 | Determine settlement dates | Ödeme tarihlerini belirle | Transaction date, bank rules | When money arrives |
| P7 | Handle installment transactions | Taksitli işlemleri yönet | Installment count, dates | Payment schedule |
| P8 | Aggregate by bank/period | Banka/dönem bazında topla | All transactions | Summary reports |
| P9 | Generate dashboard/reports | Panel/raporlar oluştur | Aggregated data | Visual dashboard |

### 2.2 Data Flow Context / Veri Akış Bağlamı

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INPUT FILES (Awaiting)                       │
│                        GİRİŞ DOSYALARI (Bekleniyor)                 │
├─────────────────────────────────────────────────────────────────────┤
│  Bank 1: [?.xlsx]  →  Columns: ?                                    │
│  Bank 2: [?.xlsx]  →  Columns: ?                                    │
│  Bank 3: [?.xlsx]  →  Columns: ?                                    │
│  ...                                                                │
│  Bank 8: [?.xlsx]  →  Columns: ?                                    │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    COLUMN MAPPING (To Define)                       │
│                    SÜTUN EŞLEŞTİRME (Tanımlanacak)                  │
├─────────────────────────────────────────────────────────────────────┤
│  Bank 1: "İşlem Tutarı" → gross_amount                              │
│  Bank 2: "Tutar" → gross_amount                                     │
│  Bank 3: "Amount" → gross_amount                                    │
│  ...                                                                │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    OUTPUT (Expected)                                │
│                    ÇIKTI (Beklenen)                                 │
├─────────────────────────────────────────────────────────────────────┤
│  Summary by bank: Gross | Commission | Net | Blocked                │
│  Banka bazında özet: Brüt | Komisyon | Net | Bloke                  │
│                                                                     │
│  Timeline: When will money arrive in account?                       │
│  Zaman çizelgesi: Para hesaba ne zaman gelecek?                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Data Sources / Veri Kaynakları

| Source / Kaynak | Format | Count / Sayı | Status / Durum |
|-----------------|--------|--------------|----------------|
| Bank POS Systems / Banka POS Sistemleri | Excel/CSV | 8 banks / 8 banka | ⏳ Awaiting files / Dosyalar bekleniyor |
| Bank Statements / Banka Ekstreleri | Excel/PDF | 8 banks / 8 banka | ⏳ Awaiting files / Dosyalar bekleniyor |
| Current Summary Table / Mevcut Özet Tablo | Excel | 1 file / 1 dosya | ⏳ Awaiting file / Dosya bekleniyor |

---

## 4. Functional Requirements / Fonksiyonel Gereksinimler

### 4.1 Input Data Fields / Giriş Veri Alanları

| Field / Alan | EN Description | TR Açıklama | Type / Tip |
|--------------|----------------|-------------|------------|
| `transaction_date` | Date of the transaction | İşlem tarihi | Date |
| `transaction_amount` | Gross transaction amount | Brüt işlem tutarı | Numeric |
| `commission_rate` | Bank commission percentage | Banka komisyon oranı | Numeric |
| `commission_amount` | Deducted commission | Kesilen komisyon | Numeric |
| `net_amount` | Amount deposited (gross - commission) | Hesaba geçen tutar (brüt - komisyon) | Numeric |
| `blocked_amount` | Pending/held amounts | Bloke/bekleyen tutar | Numeric |
| `settlement_date` | Date when funds arrive | Paranın hesaba geçtiği tarih | Date |
| `transaction_type` | Type (sale, refund, etc.) | Tip (satış, iade, vb.) | String |
| `installment_count` | Number of installments | Taksit sayısı | Integer |
| `transaction_category` | POS sale vs refund classification | POS İşlemi / İade sınıflandırması | String |
| `card_type` | Card type (credit, prepaid, etc.) | Kart tipi (kredi, prepaid, vb.) | String |

### 4.2 Filtering Rules / Filtreleme Kuralları

| Rule / Kural | EN | TR |
|--------------|-----|-----|
| Include / Dahil | Only `successful_sale` transactions | Sadece `başarılı_satış` işlemleri |
| Exclude / Hariç | Refunds, cancellations, failed (`transaction_category == "İade"`) | İadeler, iptaller, başarısız |
| Classify / Sınıfla | `transaction_category`: "POS İşlemi" vs "İade" | İşlem kategorisi ayrımı |
| Focus / Odak | Net amount reaching bank account | Banka hesabına ulaşan net tutar |

### 4.3 Tracking Requirements / Takip Gereksinimleri

| Requirement / Gereksinim | EN | TR |
|--------------------------|-----|-----|
| Settlement tracking | When payment will be deposited | Ödeme ne zaman hesaba geçecek |
| Cash availability | When funds available in register | Para kasada ne zaman kullanılabilir |
| Installments | First installment date | İlk taksit tarihi |
| Cancellations | Handle partial refunds | Kısmi iadeleri yönet |

---

## 5. Technical Specification / Teknik Spesifikasyon

### 5.1 Python Packages (No AI - Deterministic)

```
# Core Data Processing / Temel Veri İşleme
pandas              # DataFrame operations, Excel I/O
openpyxl            # Excel file reading/writing (.xlsx)
xlrd                # Legacy Excel format support (.xls)

# Data Validation / Veri Doğrulama
pandera             # DataFrame schema validation
pydantic            # Data model validation

# Date/Time Handling / Tarih/Saat İşleme
python-dateutil     # Date parsing and manipulation

# Reporting & Visualization / Raporlama & Görselleştirme
streamlit           # Rapid dashboard prototyping
plotly              # Interactive charts

# Configuration / Konfigürasyon
pyyaml              # Bank column mappings
python-dotenv       # Environment variables
```

### 5.2 Processing Pipeline / İşleme Hattı

```
[P1] READ          → pandas.read_excel() for each bank
[P2] MAP           → Apply column mapping from config/banks.yaml
[P3] FILTER        → df[df['transaction_type'] == 'successful_sale']
[P4] CALCULATE     → net_amount = gross_amount - commission_amount
[P5] BLOCKED       → Group by status, sum blocked amounts
[P6] SETTLEMENT    → Apply bank-specific settlement rules
[P7] INSTALLMENTS  → Expand installment rows with dates
[P8] AGGREGATE     → df.groupby(['bank', 'period']).sum()
[P9] DASHBOARD     → streamlit app with charts
```

### 5.3 Data Models / Veri Modelleri

```python
from pydantic import BaseModel
from datetime import date
from decimal import Decimal
from typing import Optional

class Transaction(BaseModel):
    """Single transaction record / Tek işlem kaydı"""
    bank_name: str                    # Banka adı
    transaction_date: date            # İşlem tarihi
    settlement_date: date             # Ödeme tarihi
    gross_amount: Decimal             # Brüt tutar
    commission_rate: Decimal          # Komisyon oranı
    commission_amount: Decimal        # Komisyon tutarı
    net_amount: Decimal               # Net tutar
    transaction_type: str             # İşlem tipi
    installment_count: Optional[int] = 1   # Taksit sayısı
    installment_number: Optional[int] = 1  # Taksit numarası

class BankSummary(BaseModel):
    """Bank-level summary / Banka düzeyinde özet"""
    bank_name: str                    # Banka adı
    period: str                       # Dönem (YYYY-MM)
    total_gross: Decimal              # Toplam brüt
    total_commission: Decimal         # Toplam komisyon
    total_net: Decimal                # Toplam net
    blocked_amount: Decimal           # Bloke tutar
    transaction_count: int            # İşlem sayısı
```

---

## 6. Deliverables / Teslim Edilecekler

### Phase 1: Data Pipeline / Faz 1: Veri Hattı
| Task | EN | TR | Status |
|------|-----|-----|--------|
| 1.1 | Excel/CSV ingestion for all 8 banks | 8 banka için Excel/CSV okuma | ✅ Done |
| 1.2 | Column mapping configuration per bank | Banka bazında sütun eşleştirme | ✅ Done |
| 1.3 | Data validation with error reporting | Hata raporlamalı veri doğrulama | ✅ Done |
| 1.4 | Net amount calculation | Net tutar hesaplama | ✅ Done |
| 1.5 | Transaction category (POS İşlemi / İade) | İşlem kategorisi sınıflandırma | ✅ Done |
| 1.6 | Turkish Lira formatting (₺1.234,56) | Türk Lirası formatlama | ✅ Done |

### Phase 2: Aggregation / Faz 2: Toplama
| Task | EN | TR | Status |
|------|-----|-----|--------|
| 2.1 | Bank-level summaries | Banka düzeyinde özetler | ✅ Done |
| 2.2 | Daily/Weekly/Monthly aggregations | Günlük/Haftalık/Aylık toplamlar | ✅ Done |
| 2.3 | Blocked amount tracking | Bloke tutar takibi | ⏳ |
| 2.4 | Settlement date forecasting | Ödeme tarihi tahmini | ⏳ |
| 2.5 | Card type breakdown per bank | Kart tipi bazında oran dağılımı | ✅ Done |

### Phase 3: Dashboard / Faz 3: Panel
| Task | EN | TR | Status |
|------|-----|-----|--------|
| 3.1 | Interactive web dashboard | İnteraktif web paneli | ✅ Done |
| 3.2 | Bank comparison view | Banka karşılaştırma görünümü | ✅ Done |
| 3.3 | Cash flow timeline | Nakit akış zaman çizelgesi | ✅ Done |
| 3.4 | Export to Excel | Excel'e dışa aktarma | ✅ Done |
| 3.5 | Per-bank detail pages (8 banks) | Banka bazında detay sayfaları | ✅ Done |
| 3.6 | Commission rate verification | Komisyon oranı doğrulama | ✅ Done |
| 3.7 | Month selector (defaults to last data month) | Ay seçici (son veri ayına varsayılan) | ✅ Done |

---

## 7. File Structure / Dosya Yapısı

```
cash-flow-dash/
├── data/
│   ├── raw/                  # Original bank exports / Orijinal banka dışa aktarımları
│   │   ├── bank1/            # Bank 1 files / Banka 1 dosyaları
│   │   ├── bank2/            # Bank 2 files / Banka 2 dosyaları
│   │   └── ...
│   ├── processed/            # Cleaned data / Temizlenmiş veri
│   └── output/               # Reports / Raporlar
├── src/
│   ├── ingestion/            # Bank parsers / Banka ayrıştırıcıları
│   ├── validation/           # Schema definitions / Şema tanımları
│   ├── processing/           # Calculation logic / Hesaplama mantığı
│   └── dashboard/            # Streamlit app / Streamlit uygulaması
├── config/
│   ├── banks.yaml            # Column mappings / Sütun eşleştirmeleri
│   └── settings.yaml         # App config / Uygulama ayarları
├── spec/
│   └── specification.md      # This file / Bu dosya
└── requirements.txt
```

---

## 8. Next Steps / Sonraki Adımlar

| # | Action / Aksiyon | Owner / Sorumlu | Deadline / Süre |
|---|------------------|-----------------|-----------------|
| 1 | Share sample Excel files from each bank | Emre | Thu-Fri |
| 1 | Her bankadan örnek Excel dosyalarını paylaş | Emre | Perş-Cuma |
| 2 | Share current summary table (output format) | Emre | Thu-Fri |
| 2 | Mevcut özet tabloyu paylaş (çıktı formatı) | Emre | Perş-Cuma |
| 3 | Analyze file structures, create mappings | Vahid | After files received |
| 3 | Dosya yapılarını analiz et, eşleştirme oluştur | Vahid | Dosyalar alındıktan sonra |
| 4 | Review and track progress | İlknur | Ongoing |
| 4 | İnceleme ve ilerleme takibi | İlknur | Devam eden |

---

## 9. Files Awaited / Beklenen Dosyalar

### Input Files / Giriş Dosyaları

| File Type | Description (EN) | Açıklama (TR) | Received |
|-----------|------------------|---------------|----------|
| `bank1_pos_export.xlsx` | POS export from Bank 1 | Banka 1 POS dışa aktarımı | ⬜ |
| `bank2_pos_export.xlsx` | POS export from Bank 2 | Banka 2 POS dışa aktarımı | ⬜ |
| `bank3_pos_export.xlsx` | POS export from Bank 3 | Banka 3 POS dışa aktarımı | ⬜ |
| `bank4_pos_export.xlsx` | POS export from Bank 4 | Banka 4 POS dışa aktarımı | ⬜ |
| `bank5_pos_export.xlsx` | POS export from Bank 5 | Banka 5 POS dışa aktarımı | ⬜ |
| `bank6_pos_export.xlsx` | POS export from Bank 6 | Banka 6 POS dışa aktarımı | ⬜ |
| `bank7_pos_export.xlsx` | POS export from Bank 7 | Banka 7 POS dışa aktarımı | ⬜ |
| `bank8_pos_export.xlsx` | POS export from Bank 8 | Banka 8 POS dışa aktarımı | ⬜ |

### Output Files / Çıktı Dosyaları

| File Type | Description (EN) | Açıklama (TR) | Received |
|-----------|------------------|---------------|----------|
| `current_summary.xlsx` | Current manual summary table | Mevcut manuel özet tablo | ⬜ |

---

## 10. Notes / Notlar

| EN | TR |
|----|-----|
| Monthly process is repetitive → high automation ROI | Aylık süreç tekrarlayan → yüksek otomasyon getirisi |
| Previous similar system was built → can scale to 10+ banks | Daha önce benzer sistem kuruldu → 10+ bankaya ölçeklenebilir |
| Installment cancellation edge cases need handling | Taksit iptal uç durumları ele alınmalı |
| Risk assessment after initial analysis | İlk analizden sonra risk değerlendirmesi |

---

*Specification extracted from meeting transcript / Toplantı transkriptinden çıkarılan spesifikasyon*  
*Last updated / Son güncelleme: June 2025*

