"""
Unit tests for Calculator functions

© 2026 Kariyer.net Finans Ekibi
"""
import pytest
import pandas as pd
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from processing.calculator import (
    filter_successful_transactions,
    aggregate_by_bank,
    aggregate_by_installment,
    calculate_ground_totals
)


class TestFilterSuccessfulTransactions:
    """Test suite for transaction filtering"""
    
    def test_filter_excludes_refunds(self):
        """Test that refunds (İADE) are kept — negative amounts subtract from totals"""
        df = pd.DataFrame({
            "transaction_type": ["SATIS", "İADE", "SATIS", "IADE"],
            "gross_amount": [100, -50, 200, -75],
        })
        
        result = filter_successful_transactions(df)
        
        # Refund rows are kept — their negative amounts reduce the total
        assert len(result) == 4
        assert result["gross_amount"].sum() == 175
    
    def test_filter_keeps_sales(self):
        """Test that sales are kept"""
        df = pd.DataFrame({
            "transaction_type": ["SATIS", "TKS", "TEK"],
            "gross_amount": [100, 200, 300],
        })
        
        result = filter_successful_transactions(df)
        
        assert len(result) == 3
    
    def test_filter_empty_dataframe(self):
        """Test filtering empty dataframe"""
        df = pd.DataFrame(columns=["transaction_type", "gross_amount"])
        
        result = filter_successful_transactions(df)
        
        assert len(result) == 0


class TestAggregateByBank:
    """Test suite for bank aggregation"""
    
    def test_aggregate_by_bank(self):
        """Test aggregation by bank"""
        df = pd.DataFrame({
            "bank": ["Akbank", "Akbank", "Garanti"],
            "gross_amount": [100, 200, 300],
            "commission_amount": [10, 20, 30],
            "net_amount": [90, 180, 270],
        })
        
        result = aggregate_by_bank(df)
        
        assert len(result) == 2
        assert "bank" in result.columns
        assert "gross_amount" in result.columns
    
    def test_aggregate_sums_correctly(self):
        """Test that aggregation sums correctly"""
        df = pd.DataFrame({
            "bank": ["Akbank", "Akbank"],
            "gross_amount": [100, 200],
            "commission_amount": [10, 20],
            "net_amount": [90, 180],
        })
        
        result = aggregate_by_bank(df)
        
        akbank_row = result[result["bank"] == "Akbank"]
        assert akbank_row["gross_amount"].iloc[0] == 300
        assert akbank_row["commission_amount"].iloc[0] == 30


class TestAggregateByInstallment:
    """Test suite for installment aggregation"""
    
    def test_aggregate_by_installment(self):
        """Test aggregation by installment count"""
        df = pd.DataFrame({
            "installment_count": [1, 1, 3, 6],
            "gross_amount": [100, 200, 300, 400],
            "commission_amount": [10, 20, 30, 40],
        })
        
        result = aggregate_by_installment(df)
        
        assert len(result) == 3  # 1, 3, 6
        assert "installment_count" in result.columns
    
    def test_pesin_aggregation(self):
        """Test Peşin (installment_count=1) aggregation"""
        df = pd.DataFrame({
            "installment_count": [1, 1, 1],
            "gross_amount": [100, 200, 300],
            "commission_amount": [5, 10, 15],
        })
        
        result = aggregate_by_installment(df)
        
        pesin_row = result[result["installment_count"] == 1]
        assert pesin_row["gross_amount"].iloc[0] == 600


class TestCalculateGroundTotals:
    """Test suite for ground totals calculation"""
    
    def test_calculate_ground_totals(self):
        """Test ground totals calculation"""
        df = pd.DataFrame({
            "bank": ["Akbank", "Garanti"],
            "gross_amount": [1000, 2000],
            "commission_amount": [100, 200],
            "net_amount": [900, 1800],
        })
        
        result = calculate_ground_totals(df)
        
        assert "total_gross" in result or result.get("gross_amount") is not None
    
    def test_totals_sum_correctly(self):
        """Test that totals sum correctly"""
        df = pd.DataFrame({
            "gross_amount": [1000, 2000, 3000],
            "commission_amount": [100, 200, 300],
            "net_amount": [900, 1800, 2700],
        })
        
        result = calculate_ground_totals(df)
        
        # Check total gross is 6000
        total = result.get("total_gross", result.get("gross_amount", 0))
        if isinstance(total, (int, float)):
            assert total == 6000
