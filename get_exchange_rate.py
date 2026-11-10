"""Fetch Frankfurter reference exchange rates; no currency conversion here."""

from datetime import date
import math
import re

import requests


def _normalize_currency(value: str, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z]{3}", value.strip()):
        raise ValueError(f"{name} must be a three-letter currency code, such as USD")
    return value.strip().upper()

def get_exchange_rate(
    base_currency: str,
    target_currency: str,
) -> dict:
    """Return target-currency units per one base-currency unit and the rate date.

    Rates are reference rates, not live trading quotes or bank conversion offers.
    ValueError indicates invalid/unsupported currencies or an unavailable pair.
    RuntimeError indicates an API, network, or response-validation failure.
    """
    base = _normalize_currency(base_currency, "base_currency")
    target = _normalize_currency(target_currency, "target_currency")
    url = f"https://api.frankfurter.dev/v2/rate/{base.lower()}/{target.lower()}"

    try:
        response = requests.get(url, timeout=10)
    except requests.Timeout as exc:
        raise RuntimeError("Exchange-rate request timed out after 10 seconds") from exc
    except requests.RequestException as exc:
        raise RuntimeError("Unable to connect to the exchange-rate API") from exc

    try:
        if response.status_code in (400, 404, 422):
            raise ValueError(f"Unsupported currencies or unavailable exchange-rate pair: {base}/{target}")
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(f"Exchange-rate API returned HTTP {response.status_code}") from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("Exchange-rate API returned invalid JSON") from exc
    finally:
        response.close()

    if not isinstance(data, dict):
        raise RuntimeError("Exchange-rate API returned an unexpected response format")
    if data.get("base") != base or data.get("quote") != target:
        raise RuntimeError("Exchange-rate response does not match the requested currency pair")

    rate = data.get("rate")
    if isinstance(rate, bool) or not isinstance(rate, (int, float)):
        raise RuntimeError("Exchange-rate API returned a nonnumeric rate")
    try:
        valid_rate = math.isfinite(rate) and rate > 0
    except OverflowError:
        valid_rate = False
    if not valid_rate:
        raise RuntimeError("Exchange-rate API returned a nonpositive or nonfinite rate")

    rate_date = data.get("date")
    if not isinstance(rate_date, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", rate_date):
        raise RuntimeError("Exchange-rate API returned a missing or invalid rate date")
    try:
        date.fromisoformat(rate_date)
    except ValueError as exc:
        raise RuntimeError("Exchange-rate API returned an invalid calendar date") from exc

    return {
        "base_currency": base,
        "target_currency": target,
        "exchange_rate": rate,
        "rate_date": rate_date,
        "provider": "Frankfurter",
    }
