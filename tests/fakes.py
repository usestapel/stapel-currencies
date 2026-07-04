"""Test doubles for the RATE_PROVIDER dotted-path seam."""
from decimal import Decimal

from stapel_currencies.providers import RateFetchError, RateProvider


class StaticRateProvider(RateProvider):
    """Deterministic rates — swapped in via STAPEL_CURRENCIES['RATE_PROVIDER']."""

    name = "static"
    rates = {"USD": Decimal("2"), "GBP": Decimal("0.5"), "XXX": Decimal("42")}

    def fetch_rates(self):
        return dict(self.rates)


class FailingRateProvider(RateProvider):
    """Always raises — exercises the degradation paths."""

    name = "failing"

    def fetch_rates(self):
        raise RateFetchError("boom")


class NotAProvider:
    """Importable, but not a RateProvider subclass (checks.W002)."""
