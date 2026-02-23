"""Bank file reader module.

Reads Excel/CSV files from different banks and normalizes column names.
Supports bank-specific formats including Vakıfbank semicolon-delimited CSV.
"""

from pathlib import Path
from typing import Optional, List
import math
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


def parse_turkish_number(value) -> float:
    """Parse Turkish formatted number: 1.234.567,89 → 1234567.89
    
    Supports multiple formats:
    - Turkish: 1.234.567,89 (dot as thousands, comma as decimal)
    - English: 1,234,567.89 (comma as thousands, dot as decimal)
    - Vakıfbank: +00000000000005038.80
    - Plain: 1234567.89 or 1234567,89
    
    Args:
        value: String or numeric value.
        
    Returns:
        Parsed float value.
    """
    if pd.isna(value):
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    s = str(value).strip()
    if not s:
        return 0.0
    
    # Remove currency symbols
    s = s.replace("₺", "").replace("TL", "").replace("TRY", "").strip()
    
    # Check for negative
    is_negative = s.startswith("-")
    s = s.lstrip("+-")
    
    # Vakıfbank format: leading zeros
    if re.match(r"^0+\d", s):
        s = s.lstrip("0") or "0"
    
    # Remove spaces
    s = s.replace(" ", "")
    
    # Detect format based on separators
    dot_count = s.count(".")
    comma_count = s.count(",")
    
    if dot_count > 0 and comma_count > 0:
        # Both separators present
        last_dot = s.rfind(".")
        last_comma = s.rfind(",")
        
        if last_comma > last_dot:
            # Turkish format: 1.234.567,89
            s = s.replace(".", "").replace(",", ".")
        else:
            # English format: 1,234,567.89
            s = s.replace(",", "")
    elif comma_count == 1 and dot_count == 0:
        # Single comma as decimal: 1234567,89 (Turkish)
        s = s.replace(",", ".")
    elif comma_count > 1:
        # Multiple commas as thousands: 1,234,567 (English)
        s = s.replace(",", "")
    elif dot_count >= 1:
        # Only dots — check if they are thousands separators
        # "4.000" or "1.234.567" → Turkish thousands (3 digits after each dot)
        # "4.50" → English decimal
        parts = s.split(".")
        # All parts after the first must be exactly 3 digits for thousands
        if all(len(p) == 3 and p.isdigit() for p in parts[1:]):
            # Turkish thousands separators: 4.000 → 4000, 1.234.567 → 1234567
            s = s.replace(".", "")
        # else: English decimal format — leave as-is
    
    # Remove trailing dot
    s = s.rstrip(".")
    
    if not s or s == ".":
        return 0.0
    
    try:
        result = float(s)
        return -result if is_negative else result
    except ValueError:
        return 0.0


def normalize_column_name(name: str) -> str:
    """Normalize column names for robust matching."""
    if name is None:
        return ""
    s = str(name)
    s = s.replace("\ufeff", "").replace("\xa0", " ").replace("�", "")
    s = s.strip()
    if not s:
        return ""
    s = s.replace("_", " ").replace("-", " ").replace("/", " ")
    s = re.sub(r"\s+", " ", s)
    s = s.lower()
    s = s.translate(str.maketrans({
        "ı": "i",
        "İ": "i",
        "ş": "s",
        "Ş": "s",
        "ğ": "g",
        "Ğ": "g",
        "ü": "u",
        "Ü": "u",
        "ö": "o",
        "Ö": "o",
        "ç": "c",
        "Ç": "c",
    }))
    s = re.sub(r"[^a-z0-9 ]", "", s)
    return s


class BankFileReader:
    """Reads and normalizes bank POS export files."""

    REQUIRED_STANDARD_COLUMNS = {
        "transaction_date",
        "gross_amount",
        "commission_amount",
        "net_amount",
        "installment_count",
    }
    
    @staticmethod
    def calculate_commission_rate(df: pd.DataFrame) -> pd.DataFrame:
        """Komisyon oranı yoksa veya NaN ise hesapla ve doğrula.
        
        - commission_rate yoksa: commission_amount / gross_amount ile hesapla
        - rate_source: 'file' (dosyadan), 'calculated' (hesaplandı)
        - rate_verified: gross_amount × commission_rate ≈ commission_amount
        - amount_diff: Hesaplanan ile gerçek tutar arasındaki fark
        
        Args:
            df: Transaction DataFrame
            
        Returns:
            DataFrame with rate calculation and verification columns
        """
        df = df.copy()
        
        # Rate source sütunu ekle
        if "rate_source" not in df.columns:
            df["rate_source"] = "unknown"
        
        # Commission rate yoksa oluştur
        if "commission_rate" not in df.columns:
            df["commission_rate"] = None
        
        # Her satır için işle
        for idx, row in df.iterrows():
            gross = row.get("gross_amount", 0) or 0
            commission_actual = row.get("commission_amount", 0) or 0
            rate_from_file = row.get("commission_rate")
            
            # Rate dosyadan mı geliyor yoksa hesaplanacak mı?
            if pd.notna(rate_from_file) and rate_from_file != 0:
                # Dosyadan gelen oran
                rate = rate_from_file
                # Yüzde olarak verilmişse düzelt (23.95 → 0.2395)
                if rate > 1:
                    rate = rate / 100
                df.at[idx, "commission_rate"] = rate
                df.at[idx, "rate_source"] = "file"
            else:
                # Oran yok - hesapla
                if gross != 0:
                    rate = abs(commission_actual / gross)
                    df.at[idx, "commission_rate"] = round(rate, 6)
                    df.at[idx, "rate_source"] = "calculated"
                else:
                    df.at[idx, "commission_rate"] = 0.0
                    df.at[idx, "rate_source"] = "zero_gross"
        
        # Ensure required columns exist before verification
        if "gross_amount" not in df.columns:
            df["gross_amount"] = 0.0
        if "commission_amount" not in df.columns:
            df["commission_amount"] = 0.0
        
        # Tutar doğrulaması: gross × rate = commission_amount?
        df["commission_calculated"] = df["gross_amount"] * df["commission_rate"]
        df["amount_diff"] = df["commission_amount"] - df["commission_calculated"]
        df["amount_diff_pct"] = df.apply(
            lambda r: abs(r["amount_diff"]) / r["commission_amount"] * 100 
            if r["commission_amount"] != 0 else 0, 
            axis=1
        )
        
        # Doğrulama flag: %1'den az fark varsa OK
        df["rate_verified"] = df["amount_diff_pct"] < 1.0
        
        return df

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
            "yapikredi": "ykb",
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

    def detect_bank_by_columns(self, columns: List[str]) -> Optional[str]:
        """Detect bank based on header columns if filename is not helpful."""
        normalized_cols = {normalize_column_name(c) for c in columns}
        normalized_cols.discard("")
        if not normalized_cols:
            return None

        best_key = None
        best_score = 0
        best_ratio = 0.0
        best_min_matches = 0

        for bank_key, bank_config in self.banks.items():
            raw_columns = bank_config.get("raw_columns", {})
            if not raw_columns:
                continue
            normalized_raw = {normalize_column_name(c) for c in raw_columns.keys()}
            normalized_raw.discard("")
            if not normalized_raw:
                continue

            match_count = len(normalized_cols & normalized_raw)
            if match_count == 0:
                continue

            ratio = match_count / max(1, len(normalized_raw))
            min_matches = max(2, min(5, math.ceil(len(normalized_raw) * 0.2)))

            if match_count > best_score or (match_count == best_score and ratio > best_ratio):
                best_key = bank_key
                best_score = match_count
                best_ratio = ratio
                best_min_matches = min_matches

        if best_key is None or best_score < best_min_matches:
            return None
        return best_key

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

        # If filename detection failed, try header-based detection
        if bank_key is None:
            bank_key = self.detect_bank_by_columns(list(df.columns))
            bank_config = self.banks.get(bank_key, {}) if bank_key else {}
        
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

        # Komisyon oranı yoksa hesapla ve doğrula
        df = self.calculate_commission_rate(df)
        
        # Net tutar: her zaman gross - commission
        # Ödül/servis kesintileri (Garanti vb.) ayrı sütunlarda takip edilir.
        if "gross_amount" in df.columns and "commission_amount" in df.columns:
            df["gross_amount"] = pd.to_numeric(df["gross_amount"], errors="coerce").fillna(0)
            df["commission_amount"] = pd.to_numeric(df["commission_amount"], errors="coerce").fillna(0)
            df["net_amount"] = df["gross_amount"] - df["commission_amount"]
        
        df.attrs["bank_key"] = bank_key
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
        
        normalized_df_cols = {}
        for col in df.columns:
            norm = normalize_column_name(col)
            if not norm:
                continue
            normalized_df_cols.setdefault(norm, []).append(col)

        rename_dict = {}
        for original, standard in column_mapping.items():
            norm_original = normalize_column_name(original)
            if not norm_original:
                continue
            candidates = normalized_df_cols.get(norm_original, [])
            if not candidates:
                continue
            if len(candidates) == 1:
                rename_dict[candidates[0]] = standard
                continue
            exact_matches = [
                c for c in candidates
                if str(c).strip().lower() == str(original).strip().lower()
            ]
            rename_dict[exact_matches[0] if exact_matches else candidates[0]] = standard

        return df.rename(columns=rename_dict)

    def get_required_standard_columns(self, bank_key: str) -> List[str]:
        """Return required standard columns for a bank based on its mapping."""
        if bank_key not in self.banks:
            return []
        mapped = set(self.get_column_mapping(bank_key).values())
        required = self.REQUIRED_STANDARD_COLUMNS.intersection(mapped)
        return sorted(required)

    def validate_columns(self, df: pd.DataFrame, bank_key: Optional[str]) -> dict:
        """Validate required normalized columns exist for a bank."""
        if not bank_key or bank_key not in self.banks:
            return {"missing": [], "required": []}
        required = self.get_required_standard_columns(bank_key)
        missing = [col for col in required if col not in df.columns]
        return {"missing": missing, "required": required}

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
        elif bank_key == "ykb":
            df = self._transform_ykb(df, bank_config)
        
        return df
    
    def _transform_ziraat(self, df: pd.DataFrame, bank_config: dict) -> pd.DataFrame:
        """Ziraat Bankası dönüşümleri.
        
        Ziraat verisinde taksit sayısı sadece taksitli işlemlerde dolu gelir;
        peşin / e-ticaret işlemlerinde NaN olur → 1 (peşin) olarak set edilir.
        
        Komisyon oranı yüzde cinsinden gelir (ör. 2.95 = %2.95) → /100 ile ondalığa çevrilir.
        
        İşlem kategorileri:
          - Çok Taksitli Satış → POS İşlemi (taksitli)
          - E-commers Std / E-ticaret Satış → POS İşlemi (peşin)
          - *İade / *Iade → İade
        """
        # ── İşlem Kategorisi (iade vs normal POS) ──
        if "transaction_type" in df.columns:
            tt = df["transaction_type"].astype(str).str.strip()
            df["transaction_category"] = "POS İşlemi"
            # İade satırları: "Ecommerce Satıs Iade", "E-ticaret Satış İade" vb.
            iade_mask = tt.str.contains("ade", case=False, na=False)
            df.loc[iade_mask, "transaction_category"] = "İade"
        else:
            df["transaction_category"] = "POS İşlemi"
        
        # ── Komisyon oranı: yüzde → ondalık ──
        if "commission_rate" in df.columns:
            df["commission_rate"] = pd.to_numeric(df["commission_rate"], errors="coerce") / 100
        
        # ── Taksit sayısı ──
        # Ziraat'ta Taksit Sayısı sadece taksitli işlemlerde dolu;
        # peşin/e-ticaret satışlarda NaN → 1 (peşin) olarak atanır.
        if "installment_count" in df.columns:
            df["installment_count"] = pd.to_numeric(df["installment_count"], errors="coerce").fillna(1).astype(int)
            df.loc[df["installment_count"] == 0, "installment_count"] = 1
        else:
            df["installment_count"] = 1
        
        # ── Tarih dönüşümü ──
        for col in ["transaction_date", "settlement_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        
        return df
    
    def _transform_akbank(self, df: pd.DataFrame, bank_config: dict) -> pd.DataFrame:
        """Akbank dönüşümleri."""
        # EO_KES_TUTAR = gerçek komisyon tutarı (commission_amount_alt)
        # KOMISYON_TUTAR genelde 0, kullanma
        # PROVIZYON_TUTAR = brüt tutar (gross_amount)
        # commission_rate = EO_KES_TUTAR / PROVIZYON_TUTAR
        if "commission_amount_alt" in df.columns:
            alt_vals = pd.to_numeric(df["commission_amount_alt"], errors="coerce").fillna(0)
            # Always use EO_KES_TUTAR as the real commission amount
            df["commission_amount"] = alt_vals
        
        # Komisyon oranı: EO_KES_TUTAR / PROVIZYON_TUTAR
        if "gross_amount" in df.columns and "commission_amount" in df.columns:
            df["gross_amount"] = pd.to_numeric(df["gross_amount"], errors="coerce").fillna(0)
            df["commission_amount"] = pd.to_numeric(df["commission_amount"], errors="coerce").fillna(0)
            df["commission_rate"] = df.apply(
                lambda r: abs(r["commission_amount"] / r["gross_amount"]) if r["gross_amount"] != 0 else 0, 
                axis=1
            )
        
        # Taksit sayısı (0 = peşin)
        if "installment_count" in df.columns:
            df["installment_count"] = pd.to_numeric(df["installment_count"], errors="coerce").fillna(1).astype(int)
            df.loc[df["installment_count"] == 0, "installment_count"] = 1
        
        # Tarih dönüşümü
        for col in ["transaction_date", "settlement_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        
        return df
    
    def _transform_garanti(self, df: pd.DataFrame, bank_config: dict) -> pd.DataFrame:
        """Garanti BBVA dönüşümleri."""
        # PNLT/PUCRT satırlarını silme — kategorize et.
        # PNLT = Ceza iadesi (ODULKESINTISI negatif, banka geri ödüyor)
        # PUCRT = Hizmet ücreti
        # İADE satırları negatif tutara sahiptir ve toplamdan düşülmelidir.
        if "transaction_type" in df.columns:
            tt = df["transaction_type"].astype(str).str.strip().str.upper()
            df["transaction_category"] = "POS İşlemi"
            df.loc[tt == "PNLT", "transaction_category"] = "Ceza/Ödül İadesi"
            df.loc[tt == "PUCRT", "transaction_category"] = "Hizmet Ücreti"
            # İade işlemlerini (negatif brüt) ayrıca işaretle
            # (iade satırları PNLT/PUCRT değildir, normal POS iadesidir)
        else:
            df["transaction_category"] = "POS İşlemi"

        # Tutarları Turkish number formatından parse et
        for col in ["gross_amount", "commission_amount", "net_amount", "reward_deduction", "service_deduction"]:
            if col in df.columns:
                df[col] = df[col].apply(parse_turkish_number)

        # Komisyon oranı hesapla
        if "gross_amount" in df.columns and "commission_amount" in df.columns:
            df["commission_rate"] = df.apply(
                lambda r: abs(r["commission_amount"] / r["gross_amount"]) if r["gross_amount"] != 0 else 0, 
                axis=1
            )
            # net_amount = gross - commission (ödül/servis kesintileri NET'e dahil değil,
            # ayrı sütun olarak takip edilir)
            df["net_amount"] = df["gross_amount"] - df["commission_amount"]
        
        # Taksit sayısı (0 = peşin)
        if "installment_count" in df.columns:
            df["installment_count"] = pd.to_numeric(df["installment_count"], errors="coerce").fillna(1).astype(int)
            df.loc[df["installment_count"] == 0, "installment_count"] = 1
        
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
        
        # Parse installment count (may be string, 0 = peşin)
        if "installment_count" in df.columns:
            df["installment_count"] = pd.to_numeric(df["installment_count"], errors="coerce").fillna(1).astype(int)
            df.loc[df["installment_count"] == 0, "installment_count"] = 1
        
        # Parse dates
        date_columns = ["transaction_date", "settlement_date"]
        for col in date_columns:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], format="%d/%m/%Y", errors="coerce")
        
        return df

    def _transform_ykb(self, df: pd.DataFrame, bank_config: dict) -> pd.DataFrame:
        """Yapı Kredi dönüşümleri.
        
        Sütun eşleştirme:
          - Yükleme Tarihi → transaction_date (İşlem Günü)
          - Ödeme Tarihi → settlement_date (Valor)
          - İşlem Tutarı → gross_amount (Brüt Tutar)
          - Komisyon = Taksitli İşlem Komisyonu + Katkı Payı TL
          - Mesaj Tipi → iade tespiti ("İade" ise ters işlem)
          - Net = Brüt - Komisyon (hesaplanır)
          - Taksit Sayısı / Taksit Numarası → installment_count
        """
        # ── Mesaj Tipi ile iade tespiti ──
        iade_mask = pd.Series(False, index=df.index)
        if "mesaj_tipi" in df.columns:
            iade_mask = df["mesaj_tipi"].astype(str).str.strip().str.lower().str.contains("iade", na=False)
        
        # ── Komisyon tutarı ──
        # Komisyon = Taksitli İşlem Komisyonu + Katkı Payı TL
        # Her zaman pozitif hesaplanır, iade ise işaret çevrilir.
        taksitli = pd.to_numeric(df.get("commission_taksitli", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
        katki = pd.to_numeric(df.get("katki_payi_tl", pd.Series(0, index=df.index)), errors="coerce").fillna(0)
        df["commission_amount"] = (taksitli + katki).abs()
        # İade satırlarında komisyonu negatif yap (ters işlem)
        df.loc[iade_mask, "commission_amount"] = -df.loc[iade_mask, "commission_amount"]
        
        # ── Brüt Tutar ──
        if "gross_amount" in df.columns:
            df["gross_amount"] = pd.to_numeric(df["gross_amount"], errors="coerce").fillna(0)
            # İade satırlarında brüt tutarı negatif yap
            df.loc[iade_mask, "gross_amount"] = -df.loc[iade_mask, "gross_amount"].abs()
        
        # ── Net = Brüt - Komisyon ──
        if "gross_amount" in df.columns and "commission_amount" in df.columns:
            df["net_amount"] = df["gross_amount"] - df["commission_amount"]
        
        # ── Komisyon oranı hesapla (her zaman pozitif) ──
        if "gross_amount" in df.columns and "commission_amount" in df.columns:
            df["commission_rate"] = df.apply(
                lambda r: abs(r["commission_amount"] / r["gross_amount"]) if r["gross_amount"] != 0 else 0,
                axis=1
            )
        
        # ── Taksit sayısı (format: "3/3" veya sayı, 0 = peşin) ──
        if "installment_count" in df.columns:
            df["installment_count"] = df["installment_count"].apply(
                lambda x: int(str(x).split("/")[0]) if pd.notna(x) and "/" in str(x) else (
                    int(float(x)) if pd.notna(x) and str(x).replace(".", "").isdigit() else 1
                )
            )
            df.loc[df["installment_count"] == 0, "installment_count"] = 1
        else:
            df["installment_count"] = 1
        
        # ── İşlem kategorisi (Mesaj Tipi'nden) ──
        if "mesaj_tipi" in df.columns:
            df["transaction_category"] = "POS İşlemi"
            df.loc[iade_mask, "transaction_category"] = "İade"
        elif "transaction_type" in df.columns:
            tt = df["transaction_type"].astype(str).str.strip()
            df["transaction_category"] = "POS İşlemi"
            df.loc[tt.str.contains("ade", case=False, na=False), "transaction_category"] = "İade"
        else:
            df["transaction_category"] = "POS İşlemi"
        
        # ── Tarih dönüşümü ──
        for col in ["transaction_date", "settlement_date"]:
            if col in df.columns:
                df[col] = pd.to_datetime(df[col], errors="coerce")
        
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
        
        # Find all supported files
        # 1. Kök dizindeki dosyalar
        files = (
            list(directory.glob("*.csv")) + list(directory.glob("*.CSV")) +
            list(directory.glob("*.xlsx")) + list(directory.glob("*.XLSX")) +
            list(directory.glob("*.xls")) + list(directory.glob("*.XLS"))
        )
        
        # 2. Alt klasörlerdeki dosyalar (BANKA/YYYY-MM/dosya.xlsx yapısı)
        for bank_dir in directory.iterdir():
            if bank_dir.is_dir() and not bank_dir.name.startswith("."):
                # Doğrudan banka klasöründeki dosyalar
                files.extend(
                    list(bank_dir.glob("*.csv")) + list(bank_dir.glob("*.CSV")) +
                    list(bank_dir.glob("*.xlsx")) + list(bank_dir.glob("*.XLSX")) +
                    list(bank_dir.glob("*.xls")) + list(bank_dir.glob("*.XLS"))
                )
                # Ay klasörlerindeki dosyalar (BANKA/YYYY-MM/)
                for month_dir in bank_dir.iterdir():
                    if month_dir.is_dir() and not month_dir.name.startswith("."):
                        files.extend(
                            list(month_dir.glob("*.csv")) + list(month_dir.glob("*.CSV")) +
                            list(month_dir.glob("*.xlsx")) + list(month_dir.glob("*.XLSX")) +
                            list(month_dir.glob("*.xls")) + list(month_dir.glob("*.XLS"))
                        )
        
        # Remove duplicates (in case of case-insensitive filesystem)
        files = list(set(files))
        
        if not files:
            return pd.DataFrame()
        
        # Read and merge all files
        dfs = []
        for file_path in files:
            if file_path.name.startswith(".") or file_path.name.startswith("~$"):  # Skip hidden/temp files
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
