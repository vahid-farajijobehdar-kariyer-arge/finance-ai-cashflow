#!/usr/bin/env python3
"""Test script for bank file reader."""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ingestion.reader import BankFileReader

def main():
    reader = BankFileReader()
    df = reader.read_all_files()

    print("=== NORMALIZE EDILMIS VERI ===")
    print(f"Toplam satir: {len(df)}")
    print(f"\nBanka dagilimi:")
    print(df["bank_name"].value_counts())

    print("\n=== HER BANKA ICIN STANDART SUTUNLAR ===")
    std_cols = ["gross_amount", "commission_amount", "commission_rate", "installment_count", "net_amount"]
    
    for bank in df["bank_name"].unique():
        print(f"\n--- {bank} ---")
        bank_df = df[df["bank_name"] == bank]
        for col in std_cols:
            if col in bank_df.columns:
                non_null = bank_df[col].notna().sum()
                if non_null > 0:
                    sample = bank_df[col].dropna().head(1).values[0]
                    print(f"  OK {col}: {non_null} deger, ornek: {sample}")
                else:
                    print(f"  X {col}: VERI YOK")
            else:
                print(f"  X {col}: SUTUN YOK")

if __name__ == "__main__":
    main()
