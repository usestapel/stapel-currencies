"""Models for stapel-currencies.

House rules (docs/library-standard.md §3.8):
- cross-service references are UUID fields, not FKs;
- the user model is only ``settings.AUTH_USER_MODEL``;
- index names must be <= 30 characters (models.E034);
- journal-style models get a read-only ModelAdmin.
"""
from decimal import Decimal

from django.db import models

from .conf import currencies_settings


class Currency(models.Model):
    """A currency with its exchange rate against the configured base.

    PK is the ISO 4217 currency code (e.g. EUR, USD, GBP). ``value`` is
    the exchange rate relative to ``STAPEL_CURRENCIES["BASE_CURRENCY"]``:
    1 unit of the base currency = ``value`` units of this currency. The
    base currency itself always converts with rate 1.
    """

    code = models.CharField(
        max_length=3,
        primary_key=True,
        help_text="ISO 4217 currency code (e.g., EUR, USD, GBP)",
    )
    display_name = models.CharField(
        max_length=100,
        help_text="Translation key for currency name (e.g., 'currency.eur')",
    )
    value = models.DecimalField(
        max_digits=20,
        decimal_places=8,
        default=Decimal("1"),
        help_text="Exchange rate relative to the configured base currency (base = 1)",
    )
    symbol = models.CharField(
        max_length=5,
        blank=True,
        default="",
        help_text="Currency symbol (e.g., €, $, £)",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "currencies"
        ordering = ["code"]

    def __str__(self):
        return f"{self.code} ({self.symbol})" if self.symbol else self.code

    def to_base(self, amount: Decimal) -> Decimal:
        """Convert *amount* from this currency to the base currency."""
        if self.code == currencies_settings.BASE_CURRENCY:
            return amount
        return amount / self.value

    def from_base(self, amount: Decimal) -> Decimal:
        """Convert a base-currency *amount* to this currency."""
        if self.code == currencies_settings.BASE_CURRENCY:
            return amount
        return amount * self.value
