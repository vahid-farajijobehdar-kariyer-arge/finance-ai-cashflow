"""Data models for cash flow transactions.

Pydantic models for validating bank POS transaction data.
Includes commission control fields for rate verification.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class Transaction(BaseModel):
    """Single transaction record / Tek işlem kaydı."""

    bank_name: str = Field(..., description="Banka adı")
    transaction_date: date = Field(..., description="İşlem tarihi")
    settlement_date: Optional[date] = Field(None, description="Ödeme tarihi")
    gross_amount: Decimal = Field(..., description="Brüt tutar", ge=0)
    commission_rate: Optional[Decimal] = Field(None, description="Komisyon oranı (actual)", ge=0, le=1)
    commission_amount: Decimal = Field(default=Decimal("0"), description="Komisyon tutarı (actual)", ge=0)
    net_amount: Decimal = Field(..., description="Net tutar", ge=0)
    transaction_type: str = Field(default="successful_sale", description="İşlem tipi")
    installment_count: int = Field(default=1, description="Taksit sayısı", ge=1)
    installment_number: int = Field(default=1, description="Taksit numarası", ge=1)
    
    # Optional fields for additional tracking
    transaction_id: Optional[str] = Field(None, description="İşlem ID")
    card_type: Optional[str] = Field(None, description="Kart tipi")
    card_brand: Optional[str] = Field(None, description="Kart markası (VISA, MC, TROY)")
    blocked_amount: Decimal = Field(default=Decimal("0"), description="Bloke tutar", ge=0)
    source_file: Optional[str] = Field(None, description="Kaynak dosya adı")
    
    # Commission control fields
    commission_rate_expected: Optional[Decimal] = Field(None, description="Beklenen komisyon oranı")
    commission_expected: Optional[Decimal] = Field(None, description="Beklenen komisyon tutarı")
    commission_diff: Optional[Decimal] = Field(None, description="Komisyon farkı (actual - expected)")
    rate_match: bool = Field(default=True, description="Oran eşleşmesi kontrolü")
    control_status: str = Field(default="", description="Kontrol durumu")

    @field_validator("net_amount", mode="before")
    @classmethod
    def calculate_net_if_missing(cls, v, info):
        """Calculate net amount if not provided."""
        if v is None and info.data.get("gross_amount") and info.data.get("commission_amount"):
            return info.data["gross_amount"] - info.data["commission_amount"]
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "bank_name": "Vakıfbank",
                "transaction_date": "2025-12-01",
                "settlement_date": "2025-12-02",
                "gross_amount": "5038.80",
                "commission_rate": "0.2395",
                "commission_amount": "1206.80",
                "net_amount": "3832.00",
                "transaction_type": "Taksit",
                "installment_count": 12,
                "installment_number": 1,
                "card_brand": "VISA",
                "commission_rate_expected": "0.2395",
                "commission_expected": "1206.80",
                "commission_diff": "0.00",
                "rate_match": True,
                "control_status": "✓ Doğru"
            }
        }
    }


class BankSummary(BaseModel):
    """Bank-level summary / Banka düzeyinde özet."""

    bank_name: str = Field(..., description="Banka adı")
    period: str = Field(..., description="Dönem (YYYY-MM)")
    total_gross: Decimal = Field(default=Decimal("0"), description="Toplam brüt")
    total_commission: Decimal = Field(default=Decimal("0"), description="Toplam komisyon (actual)")
    total_commission_expected: Decimal = Field(default=Decimal("0"), description="Toplam beklenen komisyon")
    total_commission_diff: Decimal = Field(default=Decimal("0"), description="Toplam komisyon farkı")
    total_net: Decimal = Field(default=Decimal("0"), description="Toplam net")
    blocked_amount: Decimal = Field(default=Decimal("0"), description="Bloke tutar")
    transaction_count: int = Field(default=0, description="İşlem sayısı", ge=0)
    matched_count: int = Field(default=0, description="Eşleşen işlem sayısı")
    mismatched_count: int = Field(default=0, description="Eşleşmeyen işlem sayısı")

    @property
    def commission_percentage(self) -> Decimal:
        """Calculate average commission percentage."""
        if self.total_gross == 0:
            return Decimal("0")
        return (self.total_commission / self.total_gross) * 100

    @property
    def match_percentage(self) -> float:
        """Calculate percentage of matched transactions."""
        if self.transaction_count == 0:
            return 0.0
        return (self.matched_count / self.transaction_count) * 100

    model_config = {
        "json_schema_extra": {
            "example": {
                "bank_name": "Vakıfbank",
                "period": "2025-12",
                "total_gross": "500000.00",
                "total_commission": "50000.00",
                "total_commission_expected": "49500.00",
                "total_commission_diff": "500.00",
                "total_net": "450000.00",
                "blocked_amount": "0.00",
                "transaction_count": 150,
                "matched_count": 148,
                "mismatched_count": 2,
            }
        }
    }


class ControlSummary(BaseModel):
    """Commission control summary / Komisyon kontrol özeti."""
    
    total_transactions: int = Field(default=0, description="Toplam işlem sayısı")
    matched_count: int = Field(default=0, description="Eşleşen işlem sayısı")
    mismatched_count: int = Field(default=0, description="Eşleşmeyen işlem sayısı")
    match_percentage: float = Field(default=0.0, description="Eşleşme yüzdesi")
    total_commission_actual: Decimal = Field(default=Decimal("0"), description="Toplam gerçek komisyon")
    total_commission_expected: Decimal = Field(default=Decimal("0"), description="Toplam beklenen komisyon")
    total_commission_diff: Decimal = Field(default=Decimal("0"), description="Toplam fark")
    status: str = Field(default="", description="Kontrol durumu")
