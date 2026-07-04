"""comm Function ``currencies.convert`` — in-process call with schema validation.

The conftest enables ``VALIDATE_SCHEMAS``, so every payload here is checked
against the committed contract in ``schemas/functions/currencies.convert.json``.
"""
from decimal import Decimal

import pytest
from stapel_core.comm import call
from stapel_core.comm.exceptions import FunctionCallError, SchemaValidationError

from stapel_currencies.errors import ERR_400_UNKNOWN_CURRENCY
from stapel_currencies.models import Currency

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalog():
    Currency.objects.create(code="EUR", display_name="currency.eur", value=Decimal("1"))
    Currency.objects.create(code="USD", display_name="currency.usd", value=Decimal("1.08"))
    Currency.objects.create(code="GBP", display_name="currency.gbp", value=Decimal("0.85"))


class TestConvertFunction:
    def test_convert_currency_to_base(self):
        result = call(
            "currencies.convert",
            {"amount": "100", "from_currency": "USD", "to_currency": "EUR"},
        )
        assert result == {"amount": "92.59"}

    def test_convert_cross_rate(self):
        result = call(
            "currencies.convert",
            {"amount": "100.00", "from_currency": "USD", "to_currency": "GBP"},
        )
        assert result == {"amount": "78.70"}

    def test_amount_is_a_string_on_the_wire(self):
        result = call(
            "currencies.convert",
            {"amount": "1", "from_currency": "EUR", "to_currency": "USD"},
        )
        assert isinstance(result["amount"], str)
        assert result["amount"] == "1.08"

    def test_negative_amounts_convert(self):
        result = call(
            "currencies.convert",
            {"amount": "-100", "from_currency": "EUR", "to_currency": "USD"},
        )
        assert result == {"amount": "-108.00"}

    def test_unknown_currency_error_key_reaches_the_caller(self):
        with pytest.raises(FunctionCallError) as exc_info:
            call(
                "currencies.convert",
                {"amount": "1", "from_currency": "ZZZ", "to_currency": "EUR"},
            )
        assert ERR_400_UNKNOWN_CURRENCY in str(exc_info.value)


class TestAmountDefenseInDepth:
    def test_unparseable_amount_raises_error_key_even_past_the_schema(self):
        # The schema already rejects non-decimal strings; the handler
        # still refuses garbage when invoked directly (defense in depth).
        from stapel_currencies.errors import ERR_400_INVALID_AMOUNT
        from stapel_currencies.functions import convert_function

        with pytest.raises(ValueError) as exc_info:
            convert_function(
                {"amount": "abc", "from_currency": "USD", "to_currency": "EUR"}
            )
        assert ERR_400_INVALID_AMOUNT in str(exc_info.value)


class TestConvertSchema:
    def test_missing_key_is_rejected(self):
        with pytest.raises(SchemaValidationError):
            call("currencies.convert", {"amount": "1", "from_currency": "USD"})

    def test_numeric_amount_is_rejected(self):
        # Strings on the wire — a JSON number is a contract violation.
        with pytest.raises(SchemaValidationError):
            call(
                "currencies.convert",
                {"amount": 100, "from_currency": "USD", "to_currency": "EUR"},
            )

    def test_non_decimal_amount_string_is_rejected(self):
        with pytest.raises(SchemaValidationError):
            call(
                "currencies.convert",
                {"amount": "ten", "from_currency": "USD", "to_currency": "EUR"},
            )

    def test_lowercase_code_is_rejected(self):
        with pytest.raises(SchemaValidationError):
            call(
                "currencies.convert",
                {"amount": "1", "from_currency": "usd", "to_currency": "EUR"},
            )

    def test_extra_key_is_rejected(self):
        with pytest.raises(SchemaValidationError):
            call(
                "currencies.convert",
                {
                    "amount": "1",
                    "from_currency": "USD",
                    "to_currency": "EUR",
                    "rate": "1.0",
                },
            )
