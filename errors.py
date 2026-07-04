"""i18n error keys of stapel-currencies.

Only ``error.<status>.<slug>`` keys leave this package — human-readable
strings are translations, never literals in responses.
"""
from stapel_core.django.api.errors import register_service_errors

ERR_400_UNKNOWN_CURRENCY = "error.400.unknown_currency"
ERR_400_INVALID_AMOUNT = "error.400.invalid_amount"
ERR_502_RATE_FETCH_FAILED = "error.502.rate_fetch_failed"

STAPEL_CURRENCIES_ERRORS = {
    ERR_400_UNKNOWN_CURRENCY: "Unknown or inactive currency code",
    ERR_400_INVALID_AMOUNT: "Amount is not a valid decimal number",
    ERR_502_RATE_FETCH_FAILED: "Exchange-rate source is unavailable",
}

register_service_errors(STAPEL_CURRENCIES_ERRORS)

__all__ = [
    "STAPEL_CURRENCIES_ERRORS",
    "ERR_400_UNKNOWN_CURRENCY",
    "ERR_400_INVALID_AMOUNT",
    "ERR_502_RATE_FETCH_FAILED",
]
