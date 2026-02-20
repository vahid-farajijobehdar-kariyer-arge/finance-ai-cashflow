"""Transaction processing and calculations.

Handles commission calculations, filtering, aggregation, and ground totals with control.
"""

from decimal import Decimal
from typing import List, Optional, Dict

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
    exclude_types: Optional[List[str]] = None,
    settings_path: Path = None,
) -> pd.DataFrame:
    """Filter DataFrame to only include successful sales.
    
    Args:
        df: Transaction DataFrame.
        transaction_type_column: Column name containing transaction type.
        successful_types: List of values indicating successful sales.
        exclude_types: List of values to exclude (refunds, cancellations).
        settings_path: Path to settings.yaml for defaults.
        
    Returns:
        Filtered DataFrame with only successful transactions.
    """
    # Load settings
    settings = load_settings(settings_path)
    processing_settings = settings.get("processing", {})
    
    # Get types to include
    if successful_types is None:
        successful_types = processing_settings.get(
            "include_transaction_types",
            ["successful_sale", "SATIŞ", "Satış", "Peşin Satış", "Taksit", "Tek Çekim", "TKS", "TEK"]
        )
    
    # Get types to exclude (used as substring patterns)
    # İADE/iade satırları negatif tutara sahiptir — toplamdan düşülmesi için tutulur.
    # PNLT (ceza/ödül iadesi) ve PUCRT (hizmet ücreti) kategorize edilir, hariç tutulmaz.
    if exclude_types is None:
        exclude_types = processing_settings.get(
            "exclude_transaction_types",
            ["İPTAL", "IPTAL", "BAŞARISIZ"]
        )
    
    # If transaction_type column doesn't exist, skip type-based filtering
    if transaction_type_column in df.columns:
        # Exclude unwanted types using substring matching (case-insensitive)
        exclude_pattern = "|".join(exclude_types)
        mask = ~df[transaction_type_column].astype(str).str.strip().str.upper().str.contains(
            exclude_pattern, case=False, na=False, regex=True
        )
        df = df[mask].copy()
    
    return df


def ensure_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure amount columns are numeric.
    
    Handles Turkish number format (comma as decimal, dot as thousands).
    
    Args:
        df: Transaction DataFrame.
        
    Returns:
        DataFrame with numeric amount columns.
    """
    amount_columns = [
        "gross_amount", "commission_amount", "net_amount", "blocked_amount",
        "commission_expected", "commission_diff"
    ]
    
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


def aggregate_by_bank(df: pd.DataFrame, include_control: bool = True) -> pd.DataFrame:
    """Aggregate transaction data by bank with commission control.
    
    Args:
        df: Transaction DataFrame with bank_name column.
        include_control: Include commission control columns in aggregation.
        
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
    
    # Add control columns if present
    if include_control:
        if "commission_expected" in df.columns:
            agg_dict["commission_expected"] = "sum"
        if "commission_diff" in df.columns:
            agg_dict["commission_diff"] = "sum"
    
    # Only include columns that exist
    agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
    
    # Add count
    result = df.groupby("bank_name").agg(agg_dict).reset_index()
    result["transaction_count"] = df.groupby("bank_name").size().values
    
    # Add control counts
    if include_control and "rate_match" in df.columns:
        result["matched_count"] = df.groupby("bank_name")["rate_match"].sum().values
        result["mismatched_count"] = result["transaction_count"] - result["matched_count"]
    
    # Calculate commission percentage
    if "gross_amount" in result.columns and "commission_amount" in result.columns:
        result["commission_pct"] = (
            result["commission_amount"] / result["gross_amount"] * 100
        ).round(2)
    
    return result


def aggregate_by_installment(df: pd.DataFrame) -> pd.DataFrame:
    """Aggregate transaction data by installment count.
    
    Args:
        df: Transaction DataFrame with installment_count column.
        
    Returns:
        Summary DataFrame grouped by installment count.
    """
    if "installment_count" not in df.columns:
        raise ValueError("DataFrame must have 'installment_count' column")
    
    df = ensure_numeric_columns(df)
    
    agg_dict = {
        "gross_amount": "sum",
        "commission_amount": "sum",
        "net_amount": "sum",
    }
    
    if "commission_expected" in df.columns:
        agg_dict["commission_expected"] = "sum"
    if "commission_diff" in df.columns:
        agg_dict["commission_diff"] = "sum"
    
    agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
    
    result = df.groupby("installment_count").agg(agg_dict).reset_index()
    result["transaction_count"] = df.groupby("installment_count").size().values
    
    # Calculate commission percentage
    if "gross_amount" in result.columns and "commission_amount" in result.columns:
        result["commission_pct"] = (
            result["commission_amount"] / result["gross_amount"] * 100
        ).round(2)
    
    return result.sort_values("installment_count")


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
    
    if "commission_expected" in df.columns:
        agg_dict["commission_expected"] = "sum"
    if "commission_diff" in df.columns:
        agg_dict["commission_diff"] = "sum"
    
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
    
    if "commission_expected" in df.columns:
        agg_dict["commission_expected"] = "sum"
    if "commission_diff" in df.columns:
        agg_dict["commission_diff"] = "sum"
    
    agg_dict = {k: v for k, v in agg_dict.items() if k in df.columns}
    
    result = df.groupby(["bank_name", "period"]).agg(agg_dict).reset_index()
    result["transaction_count"] = df.groupby(["bank_name", "period"]).size().values
    result["period"] = result["period"].astype(str)
    
    return result


def calculate_ground_totals(df: pd.DataFrame) -> Dict:
    """Calculate ground totals for all transactions with control summary.
    
    Args:
        df: Transaction DataFrame with commission control columns.
        
    Returns:
        Dictionary with total metrics.
    """
    df = ensure_numeric_columns(df)
    
    # Grand total: tüm değerler dahil (pozitif + negatif)
    # Negatif tutarlar (iade/chargeback) toplamı doğal olarak düşürür.
    totals = {
        "total_transactions": len(df),
        "total_gross": df["gross_amount"].sum() if "gross_amount" in df.columns else 0,
        "total_commission": df["commission_amount"].sum() if "commission_amount" in df.columns else 0,
        "total_net": df["net_amount"].sum() if "net_amount" in df.columns else 0,
    }
    
    # Add control totals if available
    if "commission_expected" in df.columns:
        totals["total_commission_expected"] = df["commission_expected"].sum()
        totals["total_commission_diff"] = totals["total_commission"] - totals["total_commission_expected"]
    
    if "rate_match" in df.columns:
        totals["matched_count"] = int(df["rate_match"].sum())
        totals["mismatched_count"] = totals["total_transactions"] - totals["matched_count"]
        totals["match_percentage"] = (
            totals["matched_count"] / totals["total_transactions"] * 100
            if totals["total_transactions"] > 0 else 0
        )
    
    # Commission percentage
    if totals["total_gross"] > 0:
        totals["commission_pct"] = round(totals["total_commission"] / totals["total_gross"] * 100, 2)
    else:
        totals["commission_pct"] = 0
    
    return totals
