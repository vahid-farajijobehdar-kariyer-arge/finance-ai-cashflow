"""
Unit tests for BankFileReader

© 2026 Kariyer.net Finans Ekibi
"""
import pytest
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ingestion.reader import BankFileReader, parse_vakifbank_amount


class TestBankFileReader:
    """Test suite for BankFileReader class"""
    
    def test_reader_initialization(self):
        """Test reader initializes correctly"""
        reader = BankFileReader()
        assert reader is not None
        assert hasattr(reader, 'config')
    
    def test_reader_has_bank_configs(self):
        """Test reader has bank configurations loaded"""
        reader = BankFileReader()
        assert reader.config is not None
        assert len(reader.config) > 0


class TestVakifbankParser:
    """Test suite for Vakıfbank specific parsing"""
    
    def test_parse_vakifbank_positive_amount(self):
        """Test parsing positive Vakıfbank amount format"""
        result = parse_vakifbank_amount("+00000000000005038.80")
        assert result == 5038.80
    
    def test_parse_vakifbank_negative_amount(self):
        """Test parsing negative Vakıfbank amount format"""
        result = parse_vakifbank_amount("-00000000000001234.56")
        assert result == -1234.56
    
    def test_parse_vakifbank_zero_amount(self):
        """Test parsing zero Vakıfbank amount format"""
        result = parse_vakifbank_amount("+00000000000000000.00")
        assert result == 0.0
    
    def test_parse_vakifbank_small_amount(self):
        """Test parsing small Vakıfbank amount format"""
        result = parse_vakifbank_amount("+00000000000000100.00")
        assert result == 100.0
