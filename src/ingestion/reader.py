"""Bank file reader module.

Reads Excel/CSV files from different banks and normalizes column names.
"""

from pathlib import Path
from typing import Optional

import pandas as pd
import yaml


def load_bank_config(config_path: Path = None) -> dict:
    """Load bank configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "banks.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


class BankFileReader:
    """Reads and normalizes bank POS export files."""

    def __init__(self, config_path: Path = None):
        """Initialize reader with bank configuration.
        
        Args:
            config_path: Path to banks.yaml configuration file.
        """
        self.config = load_bank_config(config_path)
        self.banks = self.config.get("banks", {})
        self.defaults = self.config.get("defaults", {})

    def detect_bank(self, file_path: Path) -> Optional[str]:
        """Detect which bank a file belongs to based on filename patterns.
        
        Args:
            file_path: Path to the bank export file.
            
        Returns:
            Bank identifier key or None if not detected.
        """
        filename = file_path.name.lower()
        
        for bank_key, bank_config in self.banks.items():
            pattern = bank_config.get("file_pattern", "").lower()
            # Simple pattern matching - convert glob to basic check
            pattern_base = pattern.replace("*", "").replace(".xlsx", "").replace(".csv", "")
            if pattern_base and pattern_base in filename:
                return bank_key
        
        return None

    def get_column_mapping(self, bank_key: str) -> dict:
        """Get column name mapping for a specific bank.
        
        Args:
            bank_key: Bank identifier key from config.
            
        Returns:
            Dictionary mapping original column names to standard names.
        """
        if bank_key not in self.banks:
            return {}
        
        return self.banks[bank_key].get("columns", {})

    def read_file(
        self,
        file_path: Path,
        bank_key: Optional[str] = None,
        sheet_name: Optional[str] = None,
    ) -> pd.DataFrame:
        """Read a bank export file and normalize columns.
        
        Args:
            file_path: Path to Excel/CSV file.
            bank_key: Bank identifier. Auto-detected if not provided.
            sheet_name: Excel sheet name. Uses first sheet if not provided.
            
        Returns:
            DataFrame with normalized column names.
        """
        file_path = Path(file_path)
        
        # Auto-detect bank if not specified
        if bank_key is None:
            bank_key = self.detect_bank(file_path)
        
        # Read file based on extension
        if file_path.suffix.lower() in [".xlsx", ".xls"]:
            df = self._read_excel(file_path, sheet_name)
        elif file_path.suffix.lower() == ".csv":
            df = self._read_csv(file_path)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        # Apply column mapping if bank is known
        if bank_key:
            df = self._apply_column_mapping(df, bank_key)
            df["bank_name"] = self.banks[bank_key].get("name", bank_key)
        
        return df

    def _read_excel(self, file_path: Path, sheet_name: Optional[str] = None) -> pd.DataFrame:
        """Read Excel file with appropriate engine."""
        engine = "xlrd" if file_path.suffix.lower() == ".xls" else "openpyxl"
        
        # Try to read with specified sheet or first sheet
        try:
            if sheet_name:
                return pd.read_excel(file_path, sheet_name=sheet_name, engine=engine)
            else:
                return pd.read_excel(file_path, sheet_name=0, engine=engine)
        except Exception as e:
            raise ValueError(f"Error reading Excel file {file_path}: {e}")

    def _read_csv(self, file_path: Path) -> pd.DataFrame:
        """Read CSV file with Turkish locale support."""
        # Try different encodings common in Turkish systems
        encodings = ["utf-8", "utf-8-sig", "iso-8859-9", "cp1254"]
        
        for encoding in encodings:
            try:
                return pd.read_csv(
                    file_path,
                    encoding=encoding,
                    decimal=self.defaults.get("decimal_separator", ","),
                    thousands=self.defaults.get("thousands_separator", "."),
                )
            except UnicodeDecodeError:
                continue
        
        raise ValueError(f"Could not read CSV file with any supported encoding: {file_path}")

    def _apply_column_mapping(self, df: pd.DataFrame, bank_key: str) -> pd.DataFrame:
        """Apply column name mapping from config.
        
        Args:
            df: DataFrame with original column names.
            bank_key: Bank identifier.
            
        Returns:
            DataFrame with renamed columns.
        """
        column_mapping = self.get_column_mapping(bank_key)
        
        # Create rename dict for columns that exist in the DataFrame
        rename_dict = {}
        for original, standard in column_mapping.items():
            if original in df.columns:
                rename_dict[original] = standard
        
        return df.rename(columns=rename_dict)

    def get_successful_transaction_types(self, bank_key: str) -> list:
        """Get list of transaction type values that indicate successful sales."""
        if bank_key not in self.banks:
            return ["successful_sale", "SATIŞ", "Satış"]
        
        types = self.banks[bank_key].get("transaction_types", {})
        return types.get("successful", ["successful_sale", "SATIŞ", "Satış"])


def read_bank_file(
    file_path: Path,
    bank_key: Optional[str] = None,
    config_path: Path = None,
) -> pd.DataFrame:
    """Convenience function to read a bank file.
    
    Args:
        file_path: Path to the bank export file.
        bank_key: Bank identifier. Auto-detected if not provided.
        config_path: Path to banks.yaml configuration.
        
    Returns:
        DataFrame with normalized columns.
    """
    reader = BankFileReader(config_path)
    return reader.read_file(file_path, bank_key)
