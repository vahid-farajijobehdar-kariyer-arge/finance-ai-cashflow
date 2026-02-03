# Cash Flow Dashboard - AI Coding Instructions

## Overview
Turkish bank POS commission tracking system. Loads raw exports from **8 banks** (Akbank, Garanti, Halkbank, QNB, Vakıfbank, YKB, Ziraat, İşbank), verifies commission rates against expected values, calculates net amounts, and provides Streamlit dashboard for analysis.

**Design Pattern**: Data resets each time new files are imported. All caches are cleared automatically on file upload/delete.

## Quick Start
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
streamlit run src/dashboard/app.py
```

## Architecture

```
data/raw/*.csv → BankFileReader → Commission Control → Calculator → Dashboard
     ↓                ↓                  ↓                ↓
  Vakıfbank      Column Mapping     Verify Rates      Aggregation
  Akbank         Numeric Parsing    Flag Diffs        Ground Totals
  Garanti        Type Mapping       Match Check       Analysis Views
  Halkbank
  QNB
  YKB
  Ziraat
  İşbank
```

### Data Flow
1. **Ingestion**: `BankFileReader.read_all_files()` scans `data/raw/`, auto-detects bank, parses with correct delimiter/encoding
2. **Control**: `add_commission_control()` compares actual vs expected commission rates
3. **Filter**: `filter_successful_transactions()` excludes refunds (İADE/IAD)
4. **Calculate**: `calculate_ground_totals()` aggregates by bank, installment, period
5. **Display**: Streamlit tabs - Özet, Banka, Taksit, Aylık, Oranlar, Kontrol
6. **Cache**: `cache_utils.py` handles automatic cache clearing on data import

| Module | Purpose |
|--------|---------|
| `src/ingestion/reader.py` | `BankFileReader` - reads Excel/CSV, auto-detects bank, applies column mapping |
| `src/processing/commission_control.py` | `add_commission_control()` - verifies rates from `config/commission_rates.yaml` |
| `src/processing/calculator.py` | `aggregate_by_bank()`, `calculate_ground_totals()`, `filter_successful_transactions()` |
| `src/dashboard/app.py` | Main Streamlit app, loads from `data/raw/` |
| `src/dashboard/auth.py` | Password authentication for all pages |
| `src/dashboard/cache_utils.py` | `clear_all_data_caches()`, `auto_refresh_if_changed()` |
| `config/banks.yaml` | Per-bank: `raw_columns`, `delimiter`, `encoding`, `skip_rows` |
| `config/commission_rates.yaml` | Commission rates per bank and installment |

## Commission Control Pattern

**Key concept**: Bank provides actual rate, we verify against expected rate from `COMMISSION_RATES`:

```python
from processing.commission_control import add_commission_control, COMMISSION_RATES

df = add_commission_control(df)  # Adds: rate_expected, commission_expected, commission_diff, rate_match
summary = get_control_summary(df)  # Returns: matched_count, mismatched_count, total_commission_diff
```

## Vakıfbank CSV Format

Special handling in `reader.py`:
- **Delimiter**: `;` (semicolon)
- **Encoding**: `iso-8859-9` (Turkish)
- **Skip rows**: 2 (metadata headers)
- **Numeric format**: `+00000000000005038.80` → `5038.80` (parsed by `parse_vakifbank_amount()`)
- **Transaction types**: `TKS`→Taksit, `TEK`→Tek Çekim, `IAD`→İade

## Adding a New Bank

1. Add config to `config/banks.yaml`:
   ```yaml
   newbank:
     name: "NewBank"
     display_name: "NEW BANK A.S."
     file_pattern: "*NewBank*.csv"
     delimiter: ","
     encoding: "utf-8"
     raw_columns:
       "Amount": gross_amount
       "Fee": commission_amount
   ```
2. Add rates to `COMMISSION_RATES` in `commission_control.py`
3. If special parsing needed, add `_transform_newbank()` method in `reader.py`

## Key Turkish Terms
| Turkish | English | In Code |
|---------|---------|---------|
| Peşin / Tek Çekim | Single payment | installment_count = 1 |
| Taksit | Installment | installment_count = 2-12 |
| Brüt Tutar | Gross Amount | gross_amount |
| Komisyon | Commission | commission_amount |
| Net Tutar | Net Amount | net_amount |
| İade / IAD | Refund | Excluded by filter |

## Commission Rates (GÜNCELLENEN ORANLAR-v3)

Rates are stored in `config/commission_rates.yaml` and managed via `src/processing/rate_manager.py`.

### Rate Management Features
- **View/Edit**: Dashboard page `12__Komisyon_Oranlari.py`
- **Version Control**: `config/rate_history.json` tracks all changes
- **Import Sources**: YAML file, CSV file, or remote URL
- **Export**: Download rates as YAML or CSV
- **Backup**: Automatic backup before any import

### Updating Rates
1. **Via Dashboard**: Navigate to "Komisyon Oranları" page, edit rates directly
2. **Via File**: Upload new `commission_rates.yaml` or CSV file
3. **Via URL**: Import from remote YAML/JSON endpoint
4. **Via Code**:
```python
from processing.rate_manager import get_rate_manager
manager = get_rate_manager()
manager.update_bank_rate("vakifbank", 1, 0.0340)  # Update single rate
manager.import_from_url("https://example.com/rates.yaml")  # Import from URL
```

### Rate File Format (YAML)
```yaml
banks:
  vakifbank:
    aliases: ["T. VAKIFLAR BANKASI T.A.O.", "Vakıfbank"]
    rates:
      1: 0.0336    # Peşin
      2: 0.0499
      3: 0.0690
```

## Dashboard Pages
| Page | File | Purpose |
|------|------|---------|
| Dashboard | `app.py` | Main summary with all tabs |
| 📤 Dosya Yükle | `1__Dosya_Yukle.py` | Upload/manage bank files (triggers cache reset) |
| 💰 Gelecek Değer | `2__Gelecek_Deger.py` | Future value calculator |
| 🔍 Veri Kontrol | `3__Veri_Kontrol.py` | Data quality validation |
| 🏦 Ziraat Detay | `3__Ziraat_Detay.py` | Ziraat bank analysis |
| 🏦 Akbank Detay | `4__Akbank_Detay.py` | Akbank analysis |
| 🏦 Garanti Detay | `5__Garanti_Detay.py` | Garanti BBVA analysis |
| 🏦 Vakıfbank Detay | `6__Vakifbank_Detay.py` | Vakıfbank analysis |
| 🏦 Halkbank Detay | `7__Halkbank_Detay.py` | Halkbank analysis |
| 🏦 QNB Detay | `8__QNB_Detay.py` | QNB Finansbank analysis |
| 🏦 YKB Detay | `9__YKB_Detay.py` | Yapı Kredi analysis |
| 📊 Rapor | `10__Rapor.py` | Export reports (Excel, CSV) |
| 🏦 İşbank Detay | `11__Isbank_Detay.py` | İş Bankası analysis |
| 📊 Komisyon Oranları | `12__Komisyon_Oranlari.py` | Rate management (view, edit, import, history) |

## File Locations
- **Raw data**: `data/raw/` (bank Excel exports)
- **Metadata**: `data/metadata/files_metadata.json` (upload tracking)
- **Config**: `config/banks.yaml` (column mappings), `config/commission_rates.yaml` (rates)
- **Spec**: `spec/specification.md` (bilingual EN/TR requirements)

## Data Reset on Import
When new files are uploaded or deleted:
1. `clear_all_data_caches()` is called automatically
2. All `@st.cache_data` decorated functions are invalidated
3. `auto_refresh_if_changed()` detects file changes on page load
4. Fresh data is loaded from `data/raw/` on next access

## Session State (Streamlit)
Dashboard uses `st.session_state` for persistence:
- `password_correct`: Authentication status
- `metadata_manager`: FileMetadata tracking
- `file_cache`: Uploaded file storage
- `fv_calculator`: Future value calculator instance
- `_data_version`: Hash of current data files for change detection
