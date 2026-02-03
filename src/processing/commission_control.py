"""Commission Control Module.

Verifies commission rates and amounts against expected bank rates.
Flags discrepancies between actual (from bank CSV) and expected rates.
Loads rates from config/commission_rates.yaml
"""

from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Optional

import pandas as pd
import yaml


# Cache for loaded commission rates
_COMMISSION_RATES_CACHE = None
_ANOMALY_THRESHOLD = 0.005  # Default 0.5%


def _load_commission_rates_from_yaml() -> dict:
    """Load commission rates from YAML file."""
    global _COMMISSION_RATES_CACHE, _ANOMALY_THRESHOLD
    
    if _COMMISSION_RATES_CACHE is not None:
        return _COMMISSION_RATES_CACHE
    
    # Find the config file
    config_paths = [
        Path(__file__).parent.parent.parent / "config" / "commission_rates.yaml",
        Path("config/commission_rates.yaml"),
        Path(__file__).parent.parent / "config" / "commission_rates.yaml",
    ]
    
    yaml_path = None
    for path in config_paths:
        if path.exists():
            yaml_path = path
            break
    
    if yaml_path is None:
        print("WARNING: commission_rates.yaml not found, using fallback rates")
        return _get_fallback_rates()
    
    with open(yaml_path, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    # Get anomaly threshold
    if 'anomaly' in config:
        _ANOMALY_THRESHOLD = config['anomaly'].get('threshold', 0.005)
    
    # Convert YAML format to internal format
    rates = {}
    for bank_key, bank_data in config.get('banks', {}).items():
        # Map each alias to the rates
        for alias in bank_data.get('aliases', []):
            rates[alias] = {}
            for inst, rate in bank_data.get('rates', {}).items():
                inst_key = "Peşin" if inst == 1 else str(inst)
                rates[alias][inst_key] = rate
                rates[alias][str(inst)] = rate  # Also add numeric key
    
    _COMMISSION_RATES_CACHE = rates
    return rates


def _get_fallback_rates() -> dict:
    """Fallback rates if YAML file is not found."""
    return {
        "Vakıfbank": {"Peşin": 0.0336, "1": 0.0336, "2": 0.0499, "3": 0.0690},
        "ZİRAAT BANKASI": {"Peşin": 0.0295, "1": 0.0295, "2": 0.0489, "3": 0.0680},
        "Akbank": {"Peşin": 0.0360, "1": 0.0360, "2": 0.0586, "3": 0.0773},
    }


def get_commission_rates() -> dict:
    """Get commission rates dictionary (loaded from YAML)."""
    return _load_commission_rates_from_yaml()


def get_anomaly_threshold() -> float:
    """Get anomaly threshold from config."""
    _load_commission_rates_from_yaml()  # Ensure loaded
    return _ANOMALY_THRESHOLD


# For backward compatibility
COMMISSION_RATES = property(lambda self: get_commission_rates())


def get_expected_rate(bank_name: str, installment_count: int) -> Optional[float]:
    """Get expected commission rate for bank and installment count.
    
    Args:
        bank_name: Bank name (full or short form).
        installment_count: Number of installments (1 = Peşin/single payment).
        
    Returns:
        Expected commission rate as decimal, or None if not found.
    """
    # Handle None/NaN bank_name
    if bank_name is None or (isinstance(bank_name, float) and pd.isna(bank_name)):
        return None
    
    bank_name = str(bank_name)
    
    # Get rates from YAML
    commission_rates = get_commission_rates()
    
    # Normalize installment count
    installment_key = str(installment_count) if installment_count > 1 else "Peşin"
    
    # Try exact match first
    if bank_name in commission_rates:
        rates = commission_rates[bank_name]
        return rates.get(installment_key, rates.get(str(installment_count)))
    
    # Try partial match
    for bank_key, rates in commission_rates.items():
        if bank_key.lower() in bank_name.lower() or bank_name.lower() in bank_key.lower():
            return rates.get(installment_key, rates.get(str(installment_count)))
    
    return None


def calculate_expected_commission(
    gross_amount: float,
    bank_name: str,
    installment_count: int
) -> tuple[float, float]:
    """Calculate expected commission amount using our rate table.
    
    Args:
        gross_amount: Transaction gross amount.
        bank_name: Bank name.
        installment_count: Number of installments.
        
    Returns:
        Tuple of (expected_rate, expected_commission_amount).
    """
    rate = get_expected_rate(bank_name, installment_count)
    if rate is None:
        return 0.0, 0.0
    
    commission = gross_amount * rate
    return rate, round(commission, 2)


def verify_commission(
    gross_amount: float,
    commission_actual: float,
    rate_actual: float,
    bank_name: str,
    installment_count: int,
    tolerance: float = 0.01
) -> dict:
    """Verify commission against expected rate.
    
    Args:
        gross_amount: Transaction gross amount.
        commission_actual: Commission amount from bank.
        rate_actual: Commission rate from bank (as decimal, e.g., 0.2395).
        bank_name: Bank name.
        installment_count: Number of installments.
        tolerance: Acceptable rate difference (default 1%).
        
    Returns:
        Dictionary with verification results.
    """
    rate_expected, commission_expected = calculate_expected_commission(
        gross_amount, bank_name, installment_count
    )
    
    # Calculate differences
    rate_diff = rate_actual - rate_expected if rate_expected else 0.0
    commission_diff = commission_actual - commission_expected
    
    # Check if within tolerance
    rate_match = abs(rate_diff) <= tolerance if rate_expected else False
    
    return {
        "rate_expected": rate_expected,
        "rate_actual": rate_actual,
        "rate_diff": rate_diff,
        "commission_expected": commission_expected,
        "commission_actual": commission_actual,
        "commission_diff": commission_diff,
        "rate_match": rate_match,
        "status": "✓ Doğru" if rate_match else "⚠ Fark Var"
    }


def add_commission_control(df: pd.DataFrame, bank_name: str = "Vakıfbank") -> pd.DataFrame:
    """Add commission control columns to DataFrame.
    
    Args:
        df: Transaction DataFrame with gross_amount, commission_amount, 
            commission_rate, installment_count columns.
        bank_name: Default bank name if not in DataFrame.
        
    Returns:
        DataFrame with added control columns.
    """
    df = df.copy()
    
    # Initialize control columns
    df["rate_expected"] = 0.0
    df["commission_expected"] = 0.0
    df["rate_diff"] = 0.0
    df["commission_diff"] = 0.0
    df["rate_match"] = False
    df["control_status"] = ""
    
    for idx, row in df.iterrows():
        # Get values
        gross = row.get("gross_amount", 0)
        commission_actual = row.get("commission_amount", 0)
        rate_actual = row.get("commission_rate", 0)
        installment = row.get("installment_count", 1)
        bank = row.get("bank_name", bank_name)
        
        # Ensure bank is a valid string
        if bank is None or (isinstance(bank, float) and pd.isna(bank)):
            bank = bank_name if bank_name and not (isinstance(bank_name, float) and pd.isna(bank_name)) else "Unknown"
        bank = str(bank)
        
        # Handle rate as percentage vs decimal
        if pd.notna(rate_actual) and rate_actual > 1:  # Rate given as percentage (e.g., 23.95)
            rate_actual = rate_actual / 100
        
        # Get installment count
        inst_count = int(installment) if pd.notna(installment) else 1
        
        # ALWAYS get expected rate from our table based on bank and installment
        rate_from_table = get_expected_rate(bank, inst_count)
        
        # If we have a rate from our table, use it to fill/override
        if rate_from_table is not None:
            # Fill commission_rate with our table rate
            df.at[idx, "commission_rate"] = rate_from_table
            
            # Calculate expected commission using our rate
            commission_from_table = gross * rate_from_table
            df.at[idx, "commission_expected"] = round(commission_from_table, 2)
            df.at[idx, "rate_expected"] = rate_from_table
            
            # Calculate differences (between actual and our expected)
            rate_diff = abs((rate_actual or 0) - rate_from_table)
            commission_diff = commission_actual - commission_from_table
            
            df.at[idx, "rate_diff"] = rate_diff
            df.at[idx, "commission_diff"] = round(commission_diff, 2)
            df.at[idx, "rate_match"] = rate_diff < 0.001  # ~0.1% tolerance
            df.at[idx, "control_status"] = "✓ OK" if rate_diff < 0.001 else f"⚠ Fark: {rate_diff*100:.2f}%"
        else:
            # No rate in our table for this bank/installment - keep original
            df.at[idx, "rate_expected"] = 0.0
            df.at[idx, "commission_expected"] = 0.0
            df.at[idx, "rate_diff"] = 0.0
            df.at[idx, "commission_diff"] = 0.0
            df.at[idx, "rate_match"] = False
            df.at[idx, "control_status"] = "? Tabloda yok"
    
    return df


def get_control_summary(df: pd.DataFrame) -> dict:
    """Get summary of commission control results.
    
    Args:
        df: DataFrame with commission control columns.
        
    Returns:
        Summary dictionary with totals and counts.
    """
    total_transactions = len(df)
    matched = df["rate_match"].sum() if "rate_match" in df.columns else 0
    mismatched = total_transactions - matched
    
    total_commission_actual = df["commission_amount"].sum() if "commission_amount" in df.columns else 0
    total_commission_expected = df["commission_expected"].sum() if "commission_expected" in df.columns else 0
    total_diff = total_commission_actual - total_commission_expected
    
    return {
        "total_transactions": total_transactions,
        "matched_count": int(matched),
        "mismatched_count": int(mismatched),
        "match_percentage": (matched / total_transactions * 100) if total_transactions > 0 else 0,
        "total_commission_actual": total_commission_actual,
        "total_commission_expected": total_commission_expected,
        "total_commission_diff": total_diff,
        "status": "✓ Tüm oranlar doğru" if mismatched == 0 else f"⚠ {mismatched} işlemde fark var"
    }
