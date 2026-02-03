# Cash Flow Dashboard - AI Coding Instructions

## Overview
Turkish bank POS commission tracking system. Loads raw exports from **8 banks**, verifies commission rates against expected values, calculates net amounts, and provides Streamlit dashboard for analysis.

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
  Garanti...     Type Mapping       Match Check       Analysis Views
```

### Data Flow
1. **Ingestion**: `BankFileReader.read_all_files()` scans `data/raw/`, auto-detects bank, parses with correct delimiter/encoding
2. **Control**: `add_commission_control()` compares actual vs expected commission rates
3. **Filter**: `filter_successful_transactions()` excludes refunds (İADE/IAD)
4. **Calculate**: `calculate_ground_totals()` aggregates by bank, installment, period
5. **Display**: Streamlit tabs - Özet, Banka, Taksit, Aylık, Oranlar, Kontrol

| Module | Purpose |
|--------|---------|
| `src/ingestion/reader.py` | `BankFileReader` - reads Excel/CSV, auto-detects bank, applies column mapping, parses Vakıfbank format |
| `src/processing/commission_control.py` | `add_commission_control()` - verifies rates, `COMMISSION_RATES` dict, `get_control_summary()` |
| `src/processing/calculator.py` | `aggregate_by_bank()`, `calculate_ground_totals()`, `filter_successful_transactions()` |
| `src/validation/models.py` | Pydantic: `Transaction`, `BankSummary`, `ControlSummary` with control fields |
| `src/dashboard/app.py` | Main Streamlit app, loads from `data/raw/`, displays Kontrol tab |
| `config/banks.yaml` | Per-bank: `raw_columns`, `delimiter`, `encoding`, `skip_rows`, `transaction_type_map` |

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

Defined in `src/processing/commission_control.py`. Example:
```python
"T. VAKIFLAR BANKASI T.A.O.": {
    "Peşin": 0.0336, "1": 0.0336,
    "2": 0.0499, "3": 0.0690, ..., "12": 0.2395
}
```

## Dashboard Tabs
| Tab | Purpose |
|-----|---------|
| 📊 Özet | Summary metrics, Tek Çekim vs Taksit split |
| 🏦 Banka | Per-bank breakdown |
| 💳 Taksit | By installment count analysis |
| 📅 Aylık | Monthly trends |
| 📊 Oranlar | Commission rates heatmap |
| 🔍 Kontrol | **Commission verification** - actual vs expected, flag discrepancies |
| Future Value | `pages/2__Future_Value.py` | Deposit interest calculator |

## File Locations
- **Raw data**: `data/raw/` (bank Excel exports)
- **Metadata**: `data/metadata/files_metadata.json` (upload tracking)
- **Config**: `config/banks.yaml` (column mappings), `config/settings.yaml` (app settings)
- **Spec**: `spec/specification.md` (bilingual EN/TR requirements)

## Adding a New Bank
1. Add bank config to `config/banks.yaml` with `raw_columns` mapping
2. Add commission rates to `COMMISSION_RATES` dict in `app.py`
3. Test with sample file using `BankFileReader.read_file()`

## Session State (Streamlit)
Dashboard uses `st.session_state` for persistence:
- `metadata_manager`: FileMetadata tracking
- `file_cache`: Uploaded file storage
- `fv_calculator`: Future value calculator instance
