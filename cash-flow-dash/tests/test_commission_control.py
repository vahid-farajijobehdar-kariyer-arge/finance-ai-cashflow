"""
Unit tests for Commission Control

© 2026 Kariyer.net Finans Ekibi
"""
import pytest
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from processing.commission_control import add_commission_control, get_control_summary, COMMISSION_RATES


class TestCommissionRates:
    """Test suite for commission rates configuration"""
    
    def test_commission_rates_loaded(self):
        """Test commission rates are loaded from config"""
        assert COMMISSION_RATES is not None
        assert len(COMMISSION_RATES) > 0
    
    def test_vakifbank_rates_exist(self):
        """Test Vakıfbank rates are defined"""
        # Check for vakifbank key (might be different case or alias)
        vakifbank_keys = [k for k in COMMISSION_RATES.keys() if 'vakif' in k.lower()]
        assert len(vakifbank_keys) > 0, "Vakıfbank rates not found"
    
    def test_pesin_rate_exists(self):
        """Test Peşin (single payment) rate exists for all banks"""
        for bank, rates in COMMISSION_RATES.items():
            # Check for installment 1 or "Peşin" key
            has_pesin = 1 in rates or "Peşin" in rates or "1" in rates
            assert has_pesin, f"Peşin rate not found for {bank}"


class TestCommissionControl:
    """Test suite for commission control functions"""
    
    def test_add_commission_control_adds_columns(self):
        """Test that commission control adds expected columns"""
        # Create sample dataframe with required columns
        df = pd.DataFrame({
            "bank": ["T. VAKIFLAR BANKASI T.A.O."],
            "installment_count": [1],
            "gross_amount": [1000.0],
            "commission_amount": [33.60],
        })
        
        result = add_commission_control(df)
        
        # Check expected columns are added
        expected_columns = ["rate_expected", "commission_expected", "rate_match"]
        for col in expected_columns:
            assert col in result.columns, f"Column {col} not found in result"
    
    def test_add_commission_control_calculates_rate(self):
        """Test that commission control calculates rate correctly"""
        df = pd.DataFrame({
            "bank": ["T. VAKIFLAR BANKASI T.A.O."],
            "installment_count": [1],
            "gross_amount": [1000.0],
            "commission_amount": [33.60],
        })
        
        result = add_commission_control(df)
        
        # Rate expected should be around 0.0336 for Vakıfbank Peşin
        assert result["rate_expected"].iloc[0] == pytest.approx(0.0336, abs=0.001)
    
    def test_get_control_summary(self):
        """Test control summary function"""
        df = pd.DataFrame({
            "bank": ["T. VAKIFLAR BANKASI T.A.O.", "T. VAKIFLAR BANKASI T.A.O."],
            "installment_count": [1, 2],
            "gross_amount": [1000.0, 2000.0],
            "commission_amount": [33.60, 99.80],
            "rate_match": [True, True],
            "commission_diff": [0.0, 0.0],
        })
        
        summary = get_control_summary(df)
        
        assert "matched_count" in summary or "match_count" in summary
        assert summary.get("matched_count", summary.get("match_count", 0)) == 2


class TestEdgeCases:
    """Test edge cases for commission control"""
    
    def test_empty_dataframe(self):
        """Test handling of empty dataframe"""
        df = pd.DataFrame(columns=["bank", "installment_count", "gross_amount", "commission_amount"])
        
        result = add_commission_control(df)
        
        assert len(result) == 0
        assert "rate_expected" in result.columns
    
    def test_unknown_bank(self):
        """Test handling of unknown bank"""
        df = pd.DataFrame({
            "bank": ["UNKNOWN BANK"],
            "installment_count": [1],
            "gross_amount": [1000.0],
            "commission_amount": [50.0],
        })
        
        result = add_commission_control(df)
        
        # Should not raise error, might have NaN for rate_expected
        assert len(result) == 1
    
    def test_zero_gross_amount(self):
        """Test handling of zero gross amount"""
        df = pd.DataFrame({
            "bank": ["T. VAKIFLAR BANKASI T.A.O."],
            "installment_count": [1],
            "gross_amount": [0.0],
            "commission_amount": [0.0],
        })
        
        result = add_commission_control(df)
        
        # Should not raise division by zero error
        assert len(result) == 1
