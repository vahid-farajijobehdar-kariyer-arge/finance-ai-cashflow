"""
Türkçe Sayı Formatlama Yardımcıları

Türkiye'de kullanılan sayı formatı:
- Bin ayırıcı: nokta (.)
- Ondalık ayırıcı: virgül (,)
- Para birimi: TL veya ₺

Örnek: 1.234.567,89 TL

© 2026 Kariyer.net Finans Ekibi
"""

import re
from typing import Union


def format_turkish_currency(value: float, symbol: str = "₺", decimals: int = 2) -> str:
    """
    Sayıyı Türkçe para birimi formatına çevir.
    
    Args:
        value: Formatlanacak sayı
        symbol: Para birimi sembolü (₺ veya TL)
        decimals: Ondalık basamak sayısı
    
    Returns:
        Formatlanmış string: "1.234.567,89 ₺"
    
    Examples:
        >>> format_turkish_currency(1234567.89)
        '1.234.567,89 ₺'
        >>> format_turkish_currency(1234567.89, "TL")
        '1.234.567,89 TL'
    """
    if value is None:
        return "-"
    
    # Negatif kontrolü
    is_negative = value < 0
    value = abs(value)
    
    # Python formatla, sonra Türkçe'ye çevir
    # Python: 1,234,567.89 → Türkçe: 1.234.567,89
    formatted = f"{value:,.{decimals}f}"
    
    # İngilizce → Türkçe dönüşüm
    # Önce virgülleri geçici karaktere çevir
    formatted = formatted.replace(",", "X")
    # Noktayı virgüle çevir
    formatted = formatted.replace(".", ",")
    # Geçici karakteri noktaya çevir
    formatted = formatted.replace("X", ".")
    
    # Negatif işareti ekle
    if is_negative:
        formatted = "-" + formatted
    
    return f"{formatted} {symbol}"


def format_turkish_number(value: float, decimals: int = 2) -> str:
    """
    Sayıyı Türkçe formatına çevir (para birimi olmadan).
    
    Args:
        value: Formatlanacak sayı
        decimals: Ondalık basamak sayısı
    
    Returns:
        Formatlanmış string: "1.234.567,89"
    """
    if value is None:
        return "-"
    
    is_negative = value < 0
    value = abs(value)
    
    formatted = f"{value:,.{decimals}f}"
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    
    if is_negative:
        formatted = "-" + formatted
    
    return formatted


def format_turkish_currency_short(value: float, symbol: str = "₺") -> str:
    """
    Büyük sayıları kısaltarak formatla (K, M, B).
    
    Args:
        value: Formatlanacak sayı
        symbol: Para birimi sembolü
    
    Returns:
        Kısaltılmış format: "1,23M ₺" veya "456,78K ₺"
    """
    if value is None:
        return "-"
    
    is_negative = value < 0
    value = abs(value)
    
    if value >= 1_000_000_000:
        formatted = f"{value/1_000_000_000:.2f}".replace(".", ",") + "B"
    elif value >= 1_000_000:
        formatted = f"{value/1_000_000:.2f}".replace(".", ",") + "M"
    elif value >= 1_000:
        formatted = f"{value/1_000:.2f}".replace(".", ",") + "K"
    else:
        formatted = f"{value:.2f}".replace(".", ",")
    
    if is_negative:
        formatted = "-" + formatted
    
    return f"{formatted} {symbol}"


def format_turkish_percent(value: float, decimals: int = 2) -> str:
    """
    Yüzde formatla.
    
    Args:
        value: Oran (0.1234 → %12,34)
        decimals: Ondalık basamak sayısı
    
    Returns:
        Formatlanmış yüzde: "%12,34"
    """
    if value is None:
        return "-"
    
    percent_value = value * 100
    formatted = f"{percent_value:.{decimals}f}".replace(".", ",")
    return f"%{formatted}"


def parse_turkish_number(value: Union[str, float, int]) -> float:
    """
    Türkçe formatlı sayıyı float'a çevir.
    
    Desteklenen formatlar:
    - "1.234.567,89" → 1234567.89
    - "1234567,89" → 1234567.89
    - "1,234,567.89" → 1234567.89 (İngilizce format)
    - "1234567.89" → 1234567.89
    - "+00000005038.80" → 5038.80 (Vakıfbank format)
    
    Args:
        value: Parse edilecek değer
    
    Returns:
        Float değer
    """
    if value is None:
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value)
    
    s = str(value).strip()
    if not s:
        return 0.0
    
    # Para birimi sembollerini kaldır
    s = s.replace("₺", "").replace("TL", "").replace("TRY", "").strip()
    
    # Negatif kontrolü
    is_negative = s.startswith("-")
    s = s.lstrip("+-")
    
    # Vakıfbank formatı: +00000000000005038.80
    if re.match(r"^0+\d", s):
        s = s.lstrip("0") or "0"
    
    # Boşlukları kaldır
    s = s.replace(" ", "")
    
    # Format tespiti: virgül ondalık mı, nokta ondalık mı?
    dot_count = s.count(".")
    comma_count = s.count(",")
    
    if dot_count > 0 and comma_count > 0:
        # Hem nokta hem virgül var
        # Hangisi daha sonda ise o ondalık ayırıcı
        last_dot = s.rfind(".")
        last_comma = s.rfind(",")
        
        if last_comma > last_dot:
            # Türkçe format: 1.234.567,89
            s = s.replace(".", "").replace(",", ".")
        else:
            # İngilizce format: 1,234,567.89
            s = s.replace(",", "")
    elif comma_count == 1 and dot_count == 0:
        # Sadece virgül var: 1234567,89 (Türkçe ondalık)
        s = s.replace(",", ".")
    elif comma_count > 1:
        # Birden fazla virgül: 1,234,567 (İngilizce bin ayırıcı)
        s = s.replace(",", "")
    # dot_count >= 1 ve comma_count == 0: İngilizce format, değiştirme
    
    # Son karakter nokta ise kaldır
    s = s.rstrip(".")
    
    if not s or s == ".":
        return 0.0
    
    try:
        result = float(s)
        return -result if is_negative else result
    except ValueError:
        return 0.0


# Streamlit için özel formatter sınıfı
class TurkishFormatter:
    """Streamlit dataframe'leri için Türkçe formatlayıcı."""
    
    @staticmethod
    def currency(col_name: str) -> dict:
        """Para birimi sütunu için format."""
        return {col_name: lambda x: format_turkish_currency(x) if x else "-"}
    
    @staticmethod
    def number(col_name: str, decimals: int = 2) -> dict:
        """Sayı sütunu için format."""
        return {col_name: lambda x: format_turkish_number(x, decimals) if x else "-"}
    
    @staticmethod
    def percent(col_name: str) -> dict:
        """Yüzde sütunu için format."""
        return {col_name: lambda x: format_turkish_percent(x) if x else "-"}


# ─── Pandas style.format() için Türkçe format fonksiyonları ───
def _tl(val, decimals=2, signed=False):
    """Pandas style.format() ile kullanılmak üzere Türk Lirası formatı.
    
    Kullanım:
        df.style.format({"Tutar": _tl})
        df.style.format({"Fark": lambda x: _tl(x, signed=True)})
    """
    try:
        v = float(val)
    except (TypeError, ValueError):
        return "-"
    fmt = f"{{:+,.{decimals}f}}" if signed else f"{{:,.{decimals}f}}"
    s = fmt.format(v)
    s = s.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"₺{s}"


def _tl0(val):
    """Türk Lirası formatı — ondalıksız (style.format için)."""
    return _tl(val, decimals=0)


def tl(val, decimals=2):
    """f-string yerine kullanılacak inline Türk Lirası formatı.
    
    Kullanım:
        st.metric("Toplam", tl(gross))
    """
    return _tl(val, decimals=decimals)


# Backward compatibility için eski fonksiyon adları
def format_currency(value: float) -> str:
    """Backward compatible currency formatter."""
    return format_turkish_currency_short(value)
