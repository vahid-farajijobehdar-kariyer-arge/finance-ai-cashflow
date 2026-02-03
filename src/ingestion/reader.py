"""Bank file reader module.

Reads Excel/CSV files from different banks and normalizes column names.
Supports bank-specific formats including Vakıfbank semicolon-delimited CSV.
"""

from pathlib import Path
from typing import Optional, List
import re

import pandas as pd
import yaml


def load_bank_config(config_path: Path = None) -> dict:
    """Load bank configuration from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent.parent.parent / "config" / "banks.yaml"
    
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def parse_vakifbank_amount(value) -> float:
    """Parse Vakıfbank numeric format: +00000000000005038.80 → 5038.80
    
    Args:
        value: String or numeric value from Vakıfbank CSV.
        
    Returns:
        Parsed float value.
    """
    if pd.isna(value):
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    # Remove leading +/- and zeros, keep sign
    s = str(value).strip()
    if not s:
        return 0.0
    
    # Check for negative
    is_negative = s.startswith("-")
    
    # Remove leading +/- and zeros
    s = s.lstrip("+-0")
    
    # Handle empty string after stripping (was all zeros)
    if not s or s == ".":
        return 0.0
    
    # If starts with decimal, add leading zero
    if s.startswith("."):
        s = "0" + s
    
    try:
        result = float(s)
        return -result if is_negative else result
    except ValueError:
        return 0.0


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
        
        # Direct keyword matching for common bank names
        bank_keywords = {
            "vakıf": "vakifbank",
            "vakif": "vakifbank",
            "akbank": "akbank",
            "garanti": "garanti",
            "halkbank": "halkbank",
            "halk": "halkbank",
            "ziraat": "ziraat",
            "ykb": "ykb",
            "yapı kredi": "ykb",
            "yapıkredi": "ykb",
            "qnb": "qnb",
            "finans": "qnb",
            "işbank": "isbankasi",
            "isbank": "isbankasi",
            "iş bank": "isbankasi",
        }
        
        for keyword, bank_key in bank_keywords.items():
            if keyword in filename:
                return bank_key
        
        # Fallback to config patterns
        for bank_key, bank_config in self.banks.items():
            pattern = bank_config.get("file_pattern", "").lower()
            # Simple pattern matching - convert glob to basic check
            pattern_base = pattern.replace("*", "").replace(".xlsx", "").replace(".csv", "")
            if pattern_base and pattern_base in filename:
                return bank_key
            
            # Also try bank name
            bank_name = bank_config.get("name", "").lower()
            if bank_name and bank_name in filename:
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
        
        return self.banks[bank_key].get("raw_columns", {})

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
        
        # Get bank config
        bank_config = self.banks.get(bank_key, {}) if bank_key else {}
        
        # Read file based on extension
        if file_path.suffix.lower() in [".xlsx", ".xls"]:
            df = self._read_excel(file_path, sheet_name)
        elif file_path.suffix.lower() == ".csv":
            df = self._read_csv(file_path, bank_config)
        else:
            raise ValueError(f"Unsupported file format: {file_path.suffix}")
        
        # Apply column mapping if bank is known
        if bank_key:
            df = self._apply_column_mapping(df, bank_key)
            df["bank_name"] = bank_config.get("display_name", bank_config.get("name", bank_key))
            
            # Apply bank-specific transformations
            df = self._apply_bank_transforms(df, bank_key, bank_config)
        else:
            # Bank not detected - try to extract name from filename
            bank_name = self._extract_bank_name_from_filename(file_path.name)
            df["bank_name"] = bank_name
        
        return df
    
    def _extract_bank_name_from_filename(self, filename: str) -> str:
        """Extract bank name from filename.
        
        Args:
            filename: File name.
            
        Returns:
            Bank display name.
        """
        # Remove extension and common prefixes/numbers
        name = Path(filename).stem
        # Remove leading numbers and dots (like "1.", "2.")
        import re
        name = re.sub(r'^[\d\.\s]+', '', name)
        # Map common patterns to display names
        name_map = {
            "akbank": "AKBANK T.A.S.",
            "garanti": "T. GARANTI BANKASI A.S.",
            "halkbank": "T. HALK BANKASI A.S.",
            "halkabank": "T. HALK BANKASI A.S.",
            "ziraat": "ZİRAAT BANKASI",
            "ykb": "YAPI VE KREDI BANKASI A.S.",
            "yapı kredi": "YAPI VE KREDI BANKASI A.S.",
            "qnb": "FINANSBANK A.S.",
            "finans": "FINANSBANK A.S.",
            "işbank": "T. IS BANKASI A.S.",
            "isbank": "T. IS BANKASI A.S.",
            "vakıfbank": "T. VAKIFLAR BANKASI T.A.O.",
            "vakifbank": "T. VAKIFLAR BANKASI T.A.O.",
        }
        
        name_lower = name.lower().strip()
        for pattern, display_name in name_map.items():
            if pattern in name_lower:
                return display_name
        
        return name.strip()

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

    def _read_csv(self, file_path: Path, bank_config: dict = None) -> pd.DataFrame:
        """Read CSV file with bank-specific settings.
        
        Args:
            file_path: Path to CSV file.
            bank_config: Bank configuration with delimiter, encoding, skip_rows.
        """
        bank_config = bank_config or {}
        
        # Get bank-specific settings
        delimiter = bank_config.get("delimiter", ",")
        skip_rows = bank_config.get("skip_rows", 0)
        encoding = bank_config.get("encoding")
        
        # Encodings to try
        encodings = [encoding] if encoding else []
        encodings.extend(["utf-8", "utf-8-sig", "iso-8859-9", "cp1254"])
        
        for enc in encodings:
            if enc is None:
                continue
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=enc,
                    delimiter=delimiter,
                    skiprows=skip_rows,
                    decimal=self.defaults.get("decimal_separator", "."),
                    on_bad_lines="skip",
                )
                # Successfully read - return
                return df
            except (UnicodeDecodeError, pd.errors.ParserError):
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
            # Handle encoding issues in column names
            for col in df.columns:
                if original in str(col) or str(col).replace("�", "ı").replace("�", "ş") == original:
                    rename_dict[col] = standard
                    break
            if original in df.columns:
                rename_dict[original] = standard
        
        return df.rename(columns=rename_dict)

    def _apply_bank_transforms(self, df: pd.DataFrame, bank_key: str, bank_config: dict) -> pd.DataFrame:
        """Apply bank-specific data transformations.
        
        Args:
            df: DataFrame with mapped columns.
            bank_key: Bank identifier.
            bank_config: Bank configuration.
            
        Returns:
            Transformed DataFrame.
        """
        # Apply bank-specific transformations
        if bank_key == "vakifbank":
            df = self._transform_vakifbank(df, bank_config)
        elif bank_key == "ziraat":
            df = self._transform_ziraat(df, bank_config)
        elif bank_key == "akbank":
            df = self._transform_akbank(df, bank_config)
        elif bank_key == "garanti":
            df = self._transform_garanti(df, bank_config)
        elif bank_key == "halkbank":
            df = self._transform_halkbank(df, bank_config)
        elif bank_key == "qnb":
            df = self._transform_qnb(df, bank_config)
        
        return df
    
    def _transform_ziraat(self, df: pd.DataFrame, bank_config: dict) -> pd.DataFrame:
        """Ziraat Bankası dönüşümleri."""
        # Oran yüzde olarak geliyor (20.55 gibi)
        if "commission_rate" in df.columns:
            df["commission_rate"] = pd.to_numeric(df["commission_rate"], errors="coerce") / 100
        
        # Taksit sayısı
        if "installment_count" in df.columns:
            df["installment_count"] = pd.to_numeric(df["installment_count"], errors="coerce").fillna(1).astype(int)
        else:
            # Taksitli işlem tipinden çıkar
            df["installment_count"] = 1
        
        # Tarih dönüşümü
        for col in ["transaction_date", "settlement_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        
        return df
    
    def _transform_akbank(self, df: pd.DataFrame, bank_config: dict) -> pd.DataFrame:
        """Akbank dönüşümleri."""
        # EO_KES_TUTAR komisyon tutarı
        if "commission_amount" not in df.columns or df["commission_amount"].isna().all():
            if "commission_amount_alt" in df.columns:
                df["commission_amount"] = df["commission_amount_alt"]
        
        # Komisyon oranı hesapla (tutar ve komisyondan)
        if "gross_amount" in df.columns and "commission_amount" in df.columns:
            df["commission_rate"] = df.apply(
                lambda r: r["commission_amount"] / r["gross_amount"] if r["gross_amount"] > 0 else 0, 
                axis=1
            )
        
        # Taksit sayısı
        if "installment_count" in df.columns:
            df["installment_count"] = pd.to_numeric(df["installment_count"], errors="coerce").fillna(1).astype(int)
        
        # Tarih dönüşümü
        for col in ["transaction_date", "settlement_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        
        return df
    
    def _transform_garanti(self, df: pd.DataFrame, bank_config: dict) -> pd.DataFrame:
        """Garanti BBVA dönüşümleri."""
        # Komisyon oranı hesapla
        if "gross_amount" in df.columns and "commission_amount" in df.columns:
            df["commission_rate"] = df.apply(
                lambda r: r["commission_amount"] / r["gross_amount"] if r["gross_amount"] > 0 else 0, 
                axis=1
            )
        
        # Taksit sayısı
        if "installment_count" in df.columns:
            df["installment_count"] = pd.to_numeric(df["installment_count"], errors="coerce").fillna(1).astype(int)
        
        # Tarih dönüşümü (dd.mm.yyyy formatında)
        if "transaction_date" in df.columns:
            df["transaction_date"] = pd.to_datetime(df["transaction_date"], format="%d.%m.%Y", errors="coerce")
        if "settlement_date" in df.columns:
            df["settlement_date"] = pd.to_datetime(df["settlement_date"], format="%d.%m.%Y", errors="coerce")
        
        return df
    
    def _transform_halkbank(self, df: pd.DataFrame, bank_config: dict) -> pd.DataFrame:
        """Halkbank dönüşümleri."""
        # Oran yüzde olarak geliyor (24.08 gibi)
        if "commission_rate" in df.columns:
            df["commission_rate"] = pd.to_numeric(df["commission_rate"], errors="coerce") / 100
        
        # Taksit sayısı (İşlem Tipi'nden çıkar: "Taksitli" veya "Peşin")
        if "installment_count" not in df.columns:
            if "transaction_type" in df.columns:
                df["installment_count"] = df["transaction_type"].apply(
                    lambda x: 1 if str(x).lower() in ["peşin", "tek", "pesin"] else 2
                )
            else:
                df["installment_count"] = 1
        
        # Tarih dönüşümü
        for col in ["transaction_date", "settlement_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        
        return df
    
    def _transform_qnb(self, df: pd.DataFrame, bank_config: dict) -> pd.DataFrame:
        """QNB Finansbank dönüşümleri."""
        # Çözülmüş Alacak Tutarı negatif olabilir (iade)
        if "gross_amount" in df.columns:
            df["gross_amount"] = pd.to_numeric(df["gross_amount"], errors="coerce").abs()
        
        if "commission_amount" in df.columns:
            df["commission_amount"] = pd.to_numeric(df["commission_amount"], errors="coerce").abs()
        
        # Oran zaten 0 veya decimal
        if "commission_rate" in df.columns:
            rate = pd.to_numeric(df["commission_rate"], errors="coerce")
            df["commission_rate"] = rate.apply(lambda x: x / 100 if x > 1 else x)
        
        # Taksit sayısı (Taksit Tipi'nden çıkar)
        if "installment_count" not in df.columns:
            if "transaction_type" in df.columns:
                df["installment_count"] = df["transaction_type"].apply(
                    lambda x: 1 if "taksitsiz" in str(x).lower() or "peş" in str(x).lower() else 2
                )
            else:
                df["installment_count"] = 1
        
        # Tarih dönüşümü
        for col in ["transaction_date", "settlement_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        
        return df

    def _transform_vakifbank(self, df: pd.DataFrame, bank_config: dict) -> pd.DataFrame:
        """Apply Vakıfbank-specific transformations.
        
        - Parse numeric format: +00000000000005038.80 → 5038.80
        - Map transaction types: TKS → Taksit, TEK → Tek Çekim
        - Parse commission rate from percentage
        """
        # Parse amount columns
        amount_columns = ["gross_amount", "commission_amount", "net_amount"]
        for col in amount_columns:
            if col in df.columns:
                df[col] = df[col].apply(parse_vakifbank_amount)
        
        # Parse commission rate (given as percentage like 23.95)
        if "commission_rate" in df.columns:
            df["commission_rate"] = df["commission_rate"].apply(
                lambda x: float(x) / 100 if pd.notna(x) and float(x) > 1 else float(x) if pd.notna(x) else 0
            )
        
        # Map transaction types
        type_map = bank_config.get("transaction_type_map", {})
        if "transaction_type" in df.columns and type_map:
            df["transaction_type_original"] = df["transaction_type"]
            df["transaction_type"] = df["transaction_type"].map(type_map).fillna(df["transaction_type"])
        
        # Parse installment count (may be string)
        if "installment_count" in df.columns:
            df["installment_count"] = pd.to_numeric(df["installment_count"], errors="coerce").fillna(1).astype(int)
        
        # Parse dates
        date_columns = ["transaction_date", "settlement_date"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="%d/%m/%Y", errors="coerce")
        
        return df

    def get_successful_transaction_types(self, bank_key: str) -> list:
        """Get list of transaction type values that indicate successful sales."""
        if bank_key not in self.banks:
            return ["successful_sale", "SATIŞ", "Satış", "Taksit", "Tek Çekim", "TKS", "TEK"]
        
        types = self.banks[bank_key].get("transaction_types", {})
        return types.get("successful", ["successful_sale", "SATIŞ", "Satış", "Taksit", "Tek Çekim"])

    def read_all_files(self, directory: Path = None) -> pd.DataFrame:
        """Read all bank files from a directory and merge into single DataFrame.
        
        Args:
            directory: Directory containing bank files. Defaults to data/raw/.
            
        Returns:
            Merged DataFrame with all transactions and bank_name column.
        """
        if directory is None:
            directory = Path(__file__).parent.parent.parent / "data" / "raw"
        
        directory = Path(directory)
        if not directory.exists():
            raise ValueError(f"Directory not found: {directory}")
        
        # Find all supported files (handle both cases for extensions)
        files = (
            list(directory.glob("*.csv")) + list(directory.glob("*.CSV")) +
            list(directory.glob("*.xlsx")) + list(directory.glob("*.XLSX")) +
            list(directory.glob("*.xls")) + list(directory.glob("*.XLS"))
        )
        # Remove duplicates (in case of case-insensitive filesystem)
        files = list(set(files))
        
        if not files:
            return pd.DataFrame()
        
        # Read and merge all files
        dfs = []
        for file_path in files:
            if file_path.name.startswith("."):  # Skip hidden files
                continue
            try:
                df = self.read_file(file_path)
                df["source_file"] = file_path.name
                dfs.append(df)
            except Exception as e:
                print(f"Warning: Could not read {file_path.name}: {e}")
                continue
        
        if not dfs:
            return pd.DataFrame()
        
        result = pd.concat(dfs, ignore_index=True)
        # Remove duplicate columns (keep first)
        result = result.loc[:, ~result.columns.duplicated()]
        return result


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
