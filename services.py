"""Domain services of stapel-currencies: conversion and rate updates.

Decimal discipline: strings on the wire (comm / HTTP), ``Decimal``
internally, floats never. Conversion results are quantized to
``STAPEL_CURRENCIES["CONVERSION_DECIMAL_PLACES"]`` with ROUND_HALF_UP;
intermediate cross-rate math keeps full precision.
"""
from __future__ import annotations

import logging
from decimal import ROUND_HALF_UP, Decimal

from django.core.exceptions import ImproperlyConfigured

from .conf import currencies_settings
from .errors import ERR_400_UNKNOWN_CURRENCY
from .models import Currency
from .providers import RateProvider

logger = logging.getLogger(__name__)


class UnknownCurrencyError(Exception):
    """Raised for a currency code that is missing or inactive.

    Carries the machine-readable error key
    (``error.400.unknown_currency``) both as ``.error_key`` and in the
    message, so HTTP views and comm callers surface the same code.
    """

    def __init__(self, code: str):
        self.code = code
        self.error_key = ERR_400_UNKNOWN_CURRENCY
        super().__init__(f"{self.error_key}: unknown or inactive currency {code!r}")


def _get_active_currency(code: str) -> Currency:
    try:
        return Currency.objects.get(code=code, is_active=True)
    except Currency.DoesNotExist:
        raise UnknownCurrencyError(code) from None


def convert(amount: Decimal, from_currency: str, to_currency: str) -> Decimal:
    """Convert *amount* between two currencies via the base-currency cross rate.

    Both codes must exist and be active — otherwise
    :class:`UnknownCurrencyError`. The result is quantized to
    ``CONVERSION_DECIMAL_PLACES`` (ROUND_HALF_UP).
    """
    quantum = Decimal(1).scaleb(-int(currencies_settings.CONVERSION_DECIMAL_PLACES))
    if from_currency == to_currency:
        # Still validate the code — converting an unknown currency to
        # itself must not silently succeed.
        _get_active_currency(from_currency)
        return amount.quantize(quantum, rounding=ROUND_HALF_UP)

    source = _get_active_currency(from_currency)
    target = _get_active_currency(to_currency)
    result = target.from_base(source.to_base(amount))
    return result.quantize(quantum, rounding=ROUND_HALF_UP)


def get_rate_provider() -> RateProvider:
    """Instantiate the configured ``RATE_PROVIDER`` (dotted-path seam)."""
    provider_cls = currencies_settings.RATE_PROVIDER
    if not (isinstance(provider_cls, type) and issubclass(provider_cls, RateProvider)):
        raise ImproperlyConfigured(
            "STAPEL_CURRENCIES['RATE_PROVIDER'] must point to a "
            f"stapel_currencies.providers.RateProvider subclass, got {provider_cls!r}"
        )
    return provider_cls()


def update_exchange_rates(dry_run: bool = False) -> dict:
    """Fetch rates from the configured provider and update Currency rows.

    Returns ``{"updated": [(code, old_value, new_value), ...],
    "not_found": [codes...]}``. Codes in the feed without a Currency row
    are reported, not created — the currency catalog is curated via
    ``DEFAULT_CURRENCIES`` / the admin, not by the rate source.

    Propagates :class:`stapel_currencies.providers.RateFetchError`;
    callers (command, Celery task) decide how loudly to fail.
    """
    provider = get_rate_provider()
    rates = provider.fetch_rates()

    updated: list[tuple[str, Decimal, Decimal]] = []
    not_found: list[str] = []
    for code, rate in sorted(rates.items()):
        try:
            currency = Currency.objects.get(code=code)
        except Currency.DoesNotExist:
            not_found.append(code)
            continue
        old_value = currency.value
        if not dry_run:
            currency.value = rate
            currency.save(update_fields=["value"])
        updated.append((code, old_value, rate))

    logger.info(
        "%s %d exchange rates from provider %r (%d codes not in database)",
        "Would update" if dry_run else "Updated",
        len(updated),
        provider.name or type(provider).__name__,
        len(not_found),
    )
    return {"updated": updated, "not_found": not_found}


__all__ = [
    "UnknownCurrencyError",
    "convert",
    "get_rate_provider",
    "update_exchange_rates",
]
