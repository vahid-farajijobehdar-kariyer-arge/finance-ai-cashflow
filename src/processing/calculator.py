"""Transaction processing and calculations.

Handles commission calculations, filtering, and aggregation.
"""

from decimal import Decimal
from typing import List, Optional

import pandas as pd
import yaml
from pathlib import Path


def load_settings(settings_path: Path = None) -> dict:
    """Load application settings from YAML file."""
    if settings_path is None:
        settings_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
    
    with open(settings_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def calculate_commission(
    gross_amount: Decimal,
    commission_rate: Decimal,
) -> Decimal:
    """Calculate commission amount from gross and rate.
    
    Args:
        gross_amount: Transaction gross amount.
        commission_rate: Commission rate as decimal (e.g., 0.0175 for 1.75%).
        
    Returns:
        Commission amount.
    """
    return gross_amount * commission_rate


def calculate_net_amount(
    gross_amount: Decimal,
    commission_amount: Decimal,
) -> Decimal:
    """Calculate net amount after commission.
    
    Args:
        gross_amount: Transaction gross amount.
        commission_amount: Commission deducted by bank.
        
    Returns:
        Net amount deposited to account.
    """
    return gross_amount - commission_amount


def calculate_net_from_rate(
    gross_amount: Decimal,
    commission_rate: Decimal,
) -> Decimal:
    """Calculate net amount directly from rate.
    
    Args:
        gross_amount: Transaction gross amount.
        commission_rate: Commission rate as decimal.
        
    Returns:
        Net amount deposited to account.
    """
    commission = calculate_commission(gross_amount, commission_rate)
    return gross_amount - commission


def filter_successful_transactions(
    df: pd.DataFrame,
    transaction_type_column: str = "transaction_type",
    successful_types: Optional[List[str]] = None,
    settings_path: Path = None,
) -> pd.DataFrame:
    """Filter DataFrame to only include successful sales.
    
    Args:
        df: Transaction DataFrame.
        transaction_type_column: Column name containing transaction type.
        successful_types: List of values indicating successful sales.
        settings_path: Path to settings.yaml for defaults.
        
    Returns:
        Filtered DataFrame with only successful transactions.
    """
    # Load default successful types from settings if not provided
    if successful_types is None:
        settings = load_settings(settings_path)
        successful_types = settings.get("processing", {}).get(
            "include_transaction_types",
            ["successful_sale", "SATIŞ", "Satış", "Peşin Satış"]
        )
    
    # If transaction_type column doesn't exist, return as-is
    if transaction_type_column not in df.columns:
        return df
    
    return df[df[transaction_type_column].isin(successful_types)].copy()


def ensure_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure amount columns are numeric.
    
    Handles Turkish number format (comma as decimal, dot as thousands).
    
    Args:
        df: Transaction DataFrame.
        
    Returns:
        DataFrame with numeric amount columns.
    """
    amount_columns = ["gross_amount", "commission_amount", "net_amount", "blocked_amount"]
    
    for col in amount_columns:
        if col in df.columns:
            # If already numeric, skip
            if pd.api.types.is_numeric_dtype(df[col]):
                continue
            
            # Handle Turkish format: replace . with nothing, replace , with .
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(".", "", regex=False)
                .str.replace(",", ".", regex=False)
                .str.replace("₺", "", regex=False)
                .str.replace(" ", "", regex=False)
                .astype(float)
            )
    
    return df


def aggregate_by_bank(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate transaction data by bank.
    
    Args:
        df: Transaction DataFrame with bank_name column.
        
    Returns:
        Summary DataFrame grouped by bank.
    """
    if "bank_name" not in df.columns:
        raise ValueError("DataFrame must have 'bank_name' column")
    
    df = ensure_numeric_columns(df)
    
    agg_dict = {
        "gross_amount": "sum",
        "commission_amount": "sum",
        "net_amount": "sum",
    }
    
    # Only include columns that exist
    agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
    
    # Add count
    result = df.groupby("bank_name").agg(agg_dict).reset_index()
    result["transaction_count"] = df.groupby("bank_name").size().values
    
    # Calculate commission percentage
    if "gross_amount" in result.columns and "commission_amount" in result.columns:
        result["commission_pct"] = (
            result["commission_amount"] / result["gross_amount"] * 100
        ).round(2)
    
    return result


def aggregate_by_period(
    df: pd.DataFrame,
    date_column: str = "transaction_date",
    period: str = "M",
) -> pd.DataFrame:
    """Aggregate transaction data by time period.
    
    Args:
        df: Transaction DataFrame.
        date_column: Column containing transaction dates.
        period: Pandas period string ('D' daily, 'W' weekly, 'M' monthly).
        
    Returns:
        Summary DataFrame grouped by period.
    """
    if date_column not in df.columns:
        raise ValueError(f"DataFrame must have '{date_column}' column")
    
    df = ensure_numeric_columns(df)
    
    # Ensure date column is datetime
    df[date_column] = pd.to_datetime(df[date_column])
    
    # Create period column
    df["period"] = df[date_column].dt.to_period(period)
    
    agg_dict = {
        "gross_amount": "sum",
        "commission_amount": "sum",
        "net_amount": "sum",
    }
    
    # Only include columns that exist
    agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
    
    result = df.groupby("period").agg(agg_dict).reset_index()
    result["transaction_count"] = df.groupby("period").size().values
    result["period"] = result["period"].astype(str)
    
    return result


def aggregate_by_bank_and_period(
    df: pd.DataFrame,
    date_column: str = "transaction_date",
    period: str = "M",
) -> pd.DataFrame:
    """Aggregate by both bank and time period.
    
    Args:
        df: Transaction DataFrame.
        date_column: Column containing transaction dates.
        period: Pandas period string.
        
    Returns:
        Summary DataFrame grouped by bank and period.
    """
    if "bank_name" not in df.columns:
        raise ValueError("DataFrame must have 'bank_name' column")
    if date_column not in df.columns:
        raise ValueError(f"DataFrame must have '{date_column}' column")
    
    df = ensure_numeric_columns(df)
    df[date_column] = pd.to_datetime(df[date_column])
    df["period"] = df[date_column].dt.to_period(period)
    
    agg_dict = {
        "gross_amount": "sum",
        "commission_amount": "sum",
        "net_amount": "sum",
    }
    
    agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
    
    result = df.groupby(["bank_name", "period"]).agg(agg_dict).reset_index()
    result["transaction_count"] = df.groupby(["bank_name", "period"]).size().values
    result["period"] = result["period"].astype(str)
    
    return result
