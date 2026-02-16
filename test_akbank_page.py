"""Test Akbank Detay page logic without Streamlit."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
import pandas as pd
from pathlib import Path
from ingestion.reader import BankFileReader
from processing.commission_control import add_commission_control
from processing.calculator import filter_successful_transactions

RAW_PATH = Path(os.path.dirname(__file__)) / 'data' / 'raw'

reader = BankFileReader()
dfs = []
for f in RAW_PATH.iterdir():
    if f.name.startswith("~$") or f.name.startswith("."):
        continue
    if f.suffix.lower() not in [".xlsx", ".xls", ".csv"]:
        continue
    if "akbank" not in f.name.lower():
        continue
    df = reader.read_file(f)
    dfs.append(df)

df = pd.concat(dfs, ignore_index=True)
df = df.loc[:, ~df.columns.duplicated()]
df = filter_successful_transactions(df)
df = add_commission_control(df)

print(f"Rows: {len(df)}")
print(f"Columns: {list(df.columns)}")
print()

# Test taksit groupby
for inst, grp in df.groupby("installment_count"):
    actual_rate = grp["commission_rate"].mean()
    expected_rate = grp["rate_expected"].mean() if "rate_expected" in grp.columns else 0
    print(f"Taksit {int(inst):>2}: actual_rate={actual_rate:.4f}, expected_rate={expected_rate:.4f}")

# Test Styler.map (not applymap)
print()
try:
    test_df = pd.DataFrame({"A": [1], "Durum": ["✅ KABUL"]})
    styled = test_df.style.map(lambda v: "background-color: green" if "KABUL" in str(v) else "", subset=["Durum"])
    print("Styler.map works OK")
except Exception as e:
    print(f"Styler.map FAILED: {e}")

try:
    styled = test_df.style.applymap(lambda v: "background-color: green" if "KABUL" in str(v) else "", subset=["Durum"])
    print("Styler.applymap works OK")
except Exception as e:
    print(f"Styler.applymap FAILED: {e}")
