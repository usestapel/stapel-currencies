"""Conversion service: cross-rate math, quantization, unknown-currency errors."""
from decimal import Decimal

import pytest
from django.test import override_settings

from stapel_currencies.errors import ERR_400_UNKNOWN_CURRENCY
from stapel_currencies.models import Currency
from stapel_currencies.services import UnknownCurrencyError, convert

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalog(settings):
    # This module's fixture rates are all relative to EUR — pin the base
    # explicitly rather than relying on whatever STAPEL_CURRENCIES defaults to.
    settings.STAPEL_CURRENCIES = {"BASE_CURRENCY": "EUR"}
    Currency.objects.create(code="EUR", display_name="currency.eur", value=Decimal("1"))
    Currency.objects.create(code="USD", display_name="currency.usd", value=Decimal("1.08"))
    Currency.objects.create(code="GBP", display_name="currency.gbp", value=Decimal("0.85"))
    Currency.objects.create(
        code="OLD", display_name="currency.old", value=Decimal("2"), is_active=False
    )


class TestConversionMath:
    def test_base_to_currency(self):
        assert convert(Decimal("100"), "EUR", "USD") == Decimal("108.00")

    def test_currency_to_base(self):
        assert convert(Decimal("108"), "USD", "EUR") == Decimal("100.00")

    def test_cross_rate_non_base_to_non_base(self):
        # 100 USD -> 92.592... EUR -> 78.7037... GBP -> 78.70
        assert convert(Decimal("100"), "USD", "GBP") == Decimal("78.70")

    def test_cross_rate_reverse(self):
        # 100 GBP -> 117.647... EUR -> 127.058... USD
        assert convert(Decimal("100"), "GBP", "USD") == Decimal("127.06")

    def test_same_currency_is_identity_quantized(self):
        assert convert(Decimal("10.567"), "USD", "USD") == Decimal("10.57")

    def test_returns_decimal(self):
        assert isinstance(convert(Decimal("1"), "EUR", "USD"), Decimal)

    def test_rounding_half_up(self):
        # 1 EUR -> 0.85 GBP; 0.005 quantized half-up at 2 places -> 0.01
        Currency.objects.filter(code="GBP").update(value=Decimal("0.005"))
        assert convert(Decimal("1"), "EUR", "GBP") == Decimal("0.01")


class TestQuantizationSetting:
    @override_settings(
        STAPEL_CURRENCIES={"BASE_CURRENCY": "EUR", "CONVERSION_DECIMAL_PLACES": 4}
    )
    def test_decimal_places_is_a_setting(self):
        assert convert(Decimal("100"), "USD", "GBP") == Decimal("78.7037")

    @override_settings(
        STAPEL_CURRENCIES={"BASE_CURRENCY": "EUR", "CONVERSION_DECIMAL_PLACES": 0}
    )
    def test_zero_decimal_places(self):
        assert convert(Decimal("100"), "USD", "GBP") == Decimal("79")


class TestBaseCurrencySetting:
    @override_settings(STAPEL_CURRENCIES={"BASE_CURRENCY": "USD"})
    def test_conversion_relative_to_configured_base(self):
        # Rates are now interpreted vs USD: 1 USD = 0.93 EUR-value etc.
        Currency.objects.filter(code="USD").update(value=Decimal("1"))
        Currency.objects.filter(code="EUR").update(value=Decimal("0.93"))
        assert convert(Decimal("100"), "USD", "EUR") == Decimal("93.00")
        assert convert(Decimal("93"), "EUR", "USD") == Decimal("100.00")


class TestUnknownCurrency:
    def test_unknown_source_raises_with_error_key(self):
        with pytest.raises(UnknownCurrencyError) as exc_info:
            convert(Decimal("1"), "ZZZ", "EUR")
        assert exc_info.value.error_key == ERR_400_UNKNOWN_CURRENCY
        assert ERR_400_UNKNOWN_CURRENCY in str(exc_info.value)
        assert exc_info.value.code == "ZZZ"

    def test_unknown_target_raises(self):
        with pytest.raises(UnknownCurrencyError):
            convert(Decimal("1"), "EUR", "ZZZ")

    def test_inactive_currency_is_unknown(self):
        with pytest.raises(UnknownCurrencyError):
            convert(Decimal("1"), "OLD", "EUR")

    def test_same_unknown_currency_still_raises(self):
        with pytest.raises(UnknownCurrencyError):
            convert(Decimal("1"), "ZZZ", "ZZZ")
