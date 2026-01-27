"""Future Value Calculator for investment projections.

Calculates potential future value of amounts if deposited in bank accounts.
"""

from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from decimal import Decimal, ROUND_HALF_UP


@dataclass
class DepositRate:
    """Bank deposit interest rate."""
    bank_name: str
    rate_annual: float  # Annual interest rate (e.g., 0.45 for 45%)
    term_months: int  # Term in months
    min_amount: float = 0.0
    max_amount: Optional[float] = None
    effective_date: Optional[str] = None
    
    @property
    def rate_monthly(self) -> float:
        """Monthly interest rate."""
        return self.rate_annual / 12


# Turkish bank deposit rates (approximate as of 2025)
DEPOSIT_RATES = [
    DepositRate("Ziraat Bankası", 0.42, 3),
    DepositRate("Ziraat Bankası", 0.40, 6),
    DepositRate("Ziraat Bankası", 0.38, 12),
    DepositRate("Halkbank", 0.43, 3),
    DepositRate("Halkbank", 0.41, 6),
    DepositRate("Halkbank", 0.39, 12),
    DepositRate("Vakıfbank", 0.42, 3),
    DepositRate("Vakıfbank", 0.40, 6),
    DepositRate("Vakıfbank", 0.38, 12),
    DepositRate("Garanti BBVA", 0.40, 3),
    DepositRate("Garanti BBVA", 0.38, 6),
    DepositRate("Garanti BBVA", 0.36, 12),
    DepositRate("Akbank", 0.41, 3),
    DepositRate("Akbank", 0.39, 6),
    DepositRate("Akbank", 0.37, 12),
    DepositRate("İş Bankası", 0.40, 3),
    DepositRate("İş Bankası", 0.38, 6),
    DepositRate("İş Bankası", 0.36, 12),
    DepositRate("YKB", 0.41, 3),
    DepositRate("YKB", 0.39, 6),
    DepositRate("YKB", 0.37, 12),
    DepositRate("QNB Finansbank", 0.42, 3),
    DepositRate("QNB Finansbank", 0.40, 6),
    DepositRate("QNB Finansbank", 0.38, 12),
]


class FutureValueCalculator:
    """Calculate future value of investments."""
    
    def __init__(self, deposit_rates: list[DepositRate] = None):
        self.deposit_rates = deposit_rates or DEPOSIT_RATES
    
    def get_rates_for_bank(self, bank_name: str) -> list[DepositRate]:
        """Get available deposit rates for a specific bank."""
        return [r for r in self.deposit_rates if r.bank_name.lower() in bank_name.lower() 
                or bank_name.lower() in r.bank_name.lower()]
    
    def get_all_banks(self) -> list[str]:
        """Get list of all available banks."""
        return sorted(set(r.bank_name for r in self.deposit_rates))
    
    def calculate_simple_interest(
        self, 
        principal: float, 
        annual_rate: float, 
        months: int
    ) -> dict:
        """Calculate simple interest future value.
        
        Args:
            principal: Initial amount
            annual_rate: Annual interest rate (e.g., 0.42 for 42%)
            months: Investment period in months
            
        Returns:
            dict with future_value, interest_earned, effective_rate
        """
        # Simple interest: I = P * r * t
        years = months / 12
        interest = principal * annual_rate * years
        future_value = principal + interest
        effective_rate = interest / principal if principal > 0 else 0
        
        return {
            "principal": round(principal, 2),
            "future_value": round(future_value, 2),
            "interest_earned": round(interest, 2),
            "annual_rate": annual_rate,
            "months": months,
            "effective_rate": round(effective_rate, 4),
        }
    
    def calculate_compound_interest(
        self, 
        principal: float, 
        annual_rate: float, 
        months: int,
        compounds_per_year: int = 12
    ) -> dict:
        """Calculate compound interest future value.
        
        Args:
            principal: Initial amount
            annual_rate: Annual interest rate
            months: Investment period in months
            compounds_per_year: Number of compounding periods per year
            
        Returns:
            dict with future_value, interest_earned, effective_rate
        """
        # Compound interest: A = P(1 + r/n)^(nt)
        years = months / 12
        n = compounds_per_year
        future_value = principal * ((1 + annual_rate / n) ** (n * years))
        interest = future_value - principal
        effective_rate = interest / principal if principal > 0 else 0
        
        return {
            "principal": round(principal, 2),
            "future_value": round(future_value, 2),
            "interest_earned": round(interest, 2),
            "annual_rate": annual_rate,
            "months": months,
            "compounds_per_year": compounds_per_year,
            "effective_rate": round(effective_rate, 4),
        }
    
    def calculate_best_option(
        self, 
        principal: float, 
        target_months: int = 12
    ) -> list[dict]:
        """Find best deposit options for given amount and period.
        
        Returns list of options sorted by interest earned (descending).
        """
        options = []
        
        for rate in self.deposit_rates:
            if rate.term_months <= target_months:
                # Calculate how many times we can renew
                num_renewals = target_months // rate.term_months
                remaining_months = target_months % rate.term_months
                
                # Compound for each renewal
                current_principal = principal
                total_interest = 0
                
                for _ in range(num_renewals):
                    result = self.calculate_simple_interest(
                        current_principal, rate.rate_annual, rate.term_months
                    )
                    total_interest += result["interest_earned"]
                    current_principal = result["future_value"]
                
                options.append({
                    "bank_name": rate.bank_name,
                    "term_months": rate.term_months,
                    "annual_rate": rate.rate_annual,
                    "num_renewals": num_renewals,
                    "principal": principal,
                    "future_value": round(current_principal, 2),
                    "total_interest": round(total_interest, 2),
                    "effective_annual_rate": round(total_interest / principal / (target_months / 12), 4),
                })
        
        # Sort by total interest (descending)
        options.sort(key=lambda x: x["total_interest"], reverse=True)
        return options
    
    def project_monthly_deposits(
        self,
        monthly_amounts: list[tuple[str, float]],  # [(month_name, amount), ...]
        annual_rate: float,
        projection_months: int = 12
    ) -> dict:
        """Project future value of monthly cash flows.
        
        Args:
            monthly_amounts: List of (month_name, amount) tuples
            annual_rate: Annual interest rate
            projection_months: How many months to project
            
        Returns:
            dict with projections per month and total
        """
        monthly_rate = annual_rate / 12
        projections = []
        total_principal = 0
        total_future_value = 0
        
        for i, (month, amount) in enumerate(monthly_amounts):
            # Months remaining from this deposit to projection end
            months_to_grow = projection_months - i
            if months_to_grow <= 0:
                continue
                
            future_value = amount * ((1 + monthly_rate) ** months_to_grow)
            interest = future_value - amount
            
            projections.append({
                "month": month,
                "deposit_amount": round(amount, 2),
                "months_to_grow": months_to_grow,
                "future_value": round(future_value, 2),
                "interest_earned": round(interest, 2),
            })
            
            total_principal += amount
            total_future_value += future_value
        
        return {
            "projections": projections,
            "total_principal": round(total_principal, 2),
            "total_future_value": round(total_future_value, 2),
            "total_interest": round(total_future_value - total_principal, 2),
            "annual_rate": annual_rate,
            "projection_months": projection_months,
        }
