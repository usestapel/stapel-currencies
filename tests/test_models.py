"""Currency model: string form and base-relative conversion helpers."""
from decimal import Decimal

import pytest
from django.test import override_settings

from stapel_currencies.models import Currency

pytestmark = pytest.mark.django_db


def test_str_with_symbol():
    assert str(Currency(code="EUR", symbol="€")) == "EUR (€)"


def test_str_without_symbol():
    assert str(Currency(code="CHF", symbol="")) == "CHF"


class TestBaseHelpers:
    def test_to_base_divides_by_rate(self):
        eur = Currency(code="EUR", value=Decimal("1.08"))
        assert eur.to_base(Decimal("108")) == Decimal("100")

    def test_from_base_multiplies_by_rate(self):
        eur = Currency(code="EUR", value=Decimal("1.08"))
        assert eur.from_base(Decimal("100")) == Decimal("108")

    def test_base_currency_is_identity_even_if_value_drifts(self):
        # The base currency converts 1:1 by definition; a drifted stored
        # value must not corrupt conversions.
        usd = Currency(code="USD", value=Decimal("0.9"))
        assert usd.to_base(Decimal("5")) == Decimal("5")
        assert usd.from_base(Decimal("5")) == Decimal("5")

    @override_settings(STAPEL_CURRENCIES={"BASE_CURRENCY": "USD"})
    def test_base_currency_is_a_setting(self):
        usd = Currency(code="USD", value=Decimal("1.08"))
        eur = Currency(code="EUR", value=Decimal("0.93"))
        # USD is now the base: identity for USD, rate math for EUR.
        assert usd.to_base(Decimal("7")) == Decimal("7")
        assert eur.from_base(Decimal("100")) == Decimal("93")


def test_decimal_value_survives_roundtrip():
    Currency.objects.create(code="USD", display_name="currency.usd", value=Decimal("1.08123456"))
    value = Currency.objects.get(code="USD").value
    assert isinstance(value, Decimal)
    assert value == Decimal("1.08123456")
