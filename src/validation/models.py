"""Data models for cash flow transactions.

Pydantic models for validating bank POS transaction data.
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
    commission_rate: Optional[Decimal] = Field(None, description="Komisyon oranı", ge=0, le=1)
    commission_amount: Decimal = Field(default=Decimal("0"), description="Komisyon tutarı", ge=0)
    net_amount: Decimal = Field(..., description="Net tutar", ge=0)
    transaction_type: str = Field(default="successful_sale", description="İşlem tipi")
    installment_count: int = Field(default=1, description="Taksit sayısı", ge=1)
    installment_number: int = Field(default=1, description="Taksit numarası", ge=1)
    
    # Optional fields for additional tracking
    transaction_id: Optional[str] = Field(None, description="İşlem ID")
    card_type: Optional[str] = Field(None, description="Kart tipi")
    blocked_amount: Decimal = Field(default=Decimal("0"), description="Bloke tutar", ge=0)

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
                "bank_name": "Ziraat Bankası",
                "transaction_date": "2026-01-15",
                "settlement_date": "2026-01-17",
                "gross_amount": "1000.00",
                "commission_rate": "0.0175",
                "commission_amount": "17.50",
                "net_amount": "982.50",
                "transaction_type": "successful_sale",
                "installment_count": 1,
                "installment_number": 1,
            }
        }
    }


class BankSummary(BaseModel):
    """Bank-level summary / Banka düzeyinde özet."""

    bank_name: str = Field(..., description="Banka adı")
    period: str = Field(..., description="Dönem (YYYY-MM)")
    total_gross: Decimal = Field(default=Decimal("0"), description="Toplam brüt")
    total_commission: Decimal = Field(default=Decimal("0"), description="Toplam komisyon")
    total_net: Decimal = Field(default=Decimal("0"), description="Toplam net")
    blocked_amount: Decimal = Field(default=Decimal("0"), description="Bloke tutar")
    transaction_count: int = Field(default=0, description="İşlem sayısı", ge=0)

    @property
    def commission_percentage(self) -> Decimal:
        """Calculate average commission percentage."""
        if self.total_gross == 0:
            return Decimal("0")
        return (self.total_commission / self.total_gross) * 100

    model_config = {
        "json_schema_extra": {
            "example": {
                "bank_name": "Ziraat Bankası",
                "period": "2026-01",
                "total_gross": "50000.00",
                "total_commission": "875.00",
                "total_net": "49125.00",
                "blocked_amount": "0.00",
                "transaction_count": 150,
            }
        }
    }
