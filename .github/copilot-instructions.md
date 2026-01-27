# Cash Flow Dashboard - AI Coding Instructions

## Project Overview

Python-based cash flow tracking system that automates manual Excel workflows from **8 Turkish bank POS systems**. Transforms raw bank exports into normalized data, calculates net amounts after commissions, and visualizes via Streamlit dashboard.

## Architecture

```
Bank Excel Files → Ingestion (per-bank parsers) → Validation (pandera/pydantic) 
    → Processing (calculations) → Aggregation → Streamlit Dashboard
```

### Key Components
- **`src/ingestion/`** - Bank-specific parsers (each bank has different column names/formats)
- **`src/validation/`** - Pydantic models for `Transaction` and `BankSummary` (see [spec/specification.md](spec/specification.md#L178-L210))
- **`src/processing/`** - Commission calculation, settlement date logic, installment expansion
- **`src/dashboard/`** - Streamlit app
- **`config/banks.yaml`** - Column mappings per bank (critical for normalization)

## Data Models (Required Schema)

Use these exact field names when creating or processing data:

```python
# Core fields for Transaction model
bank_name, transaction_date, settlement_date, gross_amount, 
commission_rate, commission_amount, net_amount, transaction_type,
installment_count, installment_number
```

## Bank Processing Patterns

### Column Mapping
Each bank exports different column names. Map to standard schema via `config/banks.yaml`:
```yaml
bank_1:
  "İşlem Tutarı": gross_amount
  "Komisyon": commission_amount
bank_2:
  "Tutar": gross_amount
  "Amount": gross_amount  # Some banks use English
```

### Filtering Rule
Only include successful sales: `df[df['transaction_type'] == 'successful_sale']`
Exclude: refunds, cancellations, failed transactions.

### Net Amount Calculation
```python
net_amount = gross_amount - commission_amount
# OR if only rate provided:
commission_amount = gross_amount * commission_rate
```

## File Locations

- **Raw bank exports**: `data/raw/` (Excel/CSV from 8 banks)
- **Processed data**: `data/processed/`
- **Output reports**: `data/output/`
- **Project spec**: [spec/specification.md](spec/specification.md) (bilingual EN/TR)

## Tech Stack

```
pandas, openpyxl, xlrd     # Excel I/O
pandera, pydantic          # Validation
streamlit, plotly          # Dashboard
pyyaml                     # Config
```

## Development Notes

- **Bilingual context**: Stakeholders are Turkish; column names in bank files may be Turkish (e.g., "İşlem Tutarı", "Komisyon", "Brüt Tutar")
- **Decimal precision**: Use `Decimal` type for monetary amounts, not `float`
- **Date handling**: Use `python-dateutil` for parsing varied date formats across banks
- **Installments**: Some transactions span multiple months—expand into separate rows with individual settlement dates

## Actual Data Structure (Discovered)

### Raw Data Source:
**`data/raw/Ziraat Bankası- Aralık Tek Çekim İşlemler Raporu-Bank-raw.xlsx`**
- Sheet: **`Ziraat Ekstre-31.12`** - Raw transaction data (14,984 rows)

> Note: Other files/sheets in `data/raw/` are prepared dashboards, NOT raw data.

### Raw Data Columns (Ziraat Ekstre-31.12):
| Column | Description | Sample Values |
|--------|-------------|---------------|
| İşlem Tipi | Transaction type | Satış, İade |
| İşlem Durumu | Transaction status | Başarılı |
| Ay | Month name (Turkish) | Haziran, Temmuz, Ağustos... |
| İşlem Tarihi | Transaction date | datetime |
| Kartın Bankası | Card issuer bank | DÜNYA KATILIM BANKASI A.Ş. |
| Banka adı | POS Bank | ZİRAAT BANKASI, AKBANK T.A.S. |
| Tutar | Amount (TRY) | 223.08, 18468.00 |
| Para Birimi | Currency | TRY |
| Taksit | Installment count | Peşin, 2, 3, ... 10 |
| Kart Markası | Card brand | VISA, MASTERCARD, TROY |
| TÜR | Payment type | Tek çekim, Taksitli |

### Column Mapping (Raw → Standard):
```python
{
    "Ay": "AY",
    "İşlem Tarihi": "Tarih",
    "Banka adı": "Banka Adı",
    "Tutar": "Tutar",
    "Taksit": "Taksit Sayısı",
    "TÜR": "Tek Çekim / Taksit",
}
```

### Veri Sheet Columns (Standard Schema):
| Column | Description | Sample Values |
|--------|-------------|---------------|
| AY | Month name (Turkish) | Ocak, Şubat, Mart... |
| Tarih | Transaction date | datetime |
| Taksit Sayısı | Installment count | Peşin, 2, 3, ... 12 |
| Banka Adı | Bank name | Garanti, Akbank, etc. |
| Tutar | Gross amount | numeric (TRY) |
| Oran | Commission rate | 0.0374 (decimal) |
| Komisyon | Commission amount | numeric (TRY) |
| Tek Çekim / Taksit | Payment type | "Tek Çekim" or "Taksit" |

### Key Turkish Terms:
- **Peşin** = Cash/Single payment (no installments)
- **Tek Çekim** = Single payment type
- **Taksit** = Installment
- **Oran** = Rate
- **Komisyon** = Commission
- **Tutar** = Amount

### Banks (8 total):
Garanti, Akbank, Halkbank, YKB, Ziraat, Vakıfbank, QNB, İşbankası

### Commission Rate Ranges:
- **Lowest**: Ziraat (Peşin: 2.95%, 12-month: ~20%)
- **Highest**: Some banks reach ~25% for 12-month installments
- Rates increase with installment count

## Current Status

Dashboard implemented with Streamlit. Core analysis views:
1. **Özet (Summary)** - Total metrics, bank breakdown charts
2. **Bankalar (Banks)** - Per-bank analysis
3. **Taksit (Installments)** - Installment distribution analysis
4. **Trend** - Monthly trends
5. **Oranlar (Rates)** - Commission rates comparison
6. **Veri (Data)** - Raw data table with filters
