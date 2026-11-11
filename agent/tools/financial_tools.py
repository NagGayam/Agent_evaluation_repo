"""Local financial calculations; no API calls or MCP dependencies."""

import math


def _validate_number(name: str, value: float, *, allow_zero: bool) -> None:
    """Require a finite int/float, excluding booleans and numeric strings."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise ValueError(f"{name} must be a finite number")
    if value < 0 or (value == 0 and not allow_zero):
        requirement = "nonnegative" if allow_zero else "positive"
        raise ValueError(f"{name} must be {requirement}")


def calculate_emi(
    principal: float,
    annual_interest_rate: float,
    tenure_months: int,
) -> dict:
    """Calculate fixed-rate monthly EMI, total repayment and total interest.

    annual_interest_rate is a percentage: 10 means 10% per year.
    Assume monthly payments and no additional fees. Calculate totals before
    rounding the returned amounts to two decimal places.
    """
    _validate_number("principal", principal, allow_zero=False)
    _validate_number("annual_interest_rate", annual_interest_rate, allow_zero=True)
    if isinstance(tenure_months, bool) or not isinstance(tenure_months, int) or tenure_months <= 0:
        raise ValueError("tenure_months must be a positive integer")

    monthly_rate = annual_interest_rate / 1200
    try:
        if monthly_rate == 0:
            monthly_emi = principal / tenure_months
        else:
            # Equivalent to P*r*(1+r)**n / ((1+r)**n - 1), but avoids
            # overflowing the power and losing precision for small rates.
            denominator = -math.expm1(-tenure_months * math.log1p(monthly_rate))
            monthly_emi = principal * (monthly_rate / denominator)

        total_repayment = monthly_emi * tenure_months
        total_interest = max(0.0, total_repayment - principal)
    except (OverflowError, ZeroDivisionError) as exc:
        raise ValueError("Inputs exceed the supported calculation range") from exc
    if not all(math.isfinite(value) for value in (monthly_emi, total_repayment, total_interest)):
        raise ValueError("Inputs exceed the supported calculation range")

    return {
        "monthly_emi": round(monthly_emi, 2),
        "total_repayment": round(total_repayment, 2),
        "total_interest": round(total_interest, 2),
    }


def convert_currency(
    amount: float,
    exchange_rate: float,
) -> dict:
    """Convert using target-currency units per one source-currency unit.

    The caller supplies the rate; this function does not fetch live rates.
    For example, amount=100 and rate=85 produces 8500 target-currency units.
    """
    _validate_number("amount", amount, allow_zero=True)
    _validate_number("exchange_rate", exchange_rate, allow_zero=False)
    converted_amount = amount * exchange_rate
    if not math.isfinite(converted_amount):
        raise ValueError("Inputs exceed the supported calculation range")
    return {
        "amount": amount,
        "exchange_rate": exchange_rate,
        "converted_amount": round(converted_amount, 2),
    }
