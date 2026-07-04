"""comm surface of stapel-currencies.

Every Function carries a JSON schema in ``schemas/`` — tests run with
``VALIDATE_SCHEMAS`` on, so a payload drifting from its schema fails
loudly. Registration happens on import from ``apps.py:ready()``; re-imports
are no-ops. Other modules call by name, no import of this package needed:

    from stapel_core.comm import call

    call("currencies.convert", {
        "amount": "100.00", "from_currency": "USD", "to_currency": "EUR",
    })
    # -> {"amount": "92.59"}
"""
import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from stapel_core.comm import function

from .errors import ERR_400_INVALID_AMOUNT

_SCHEMAS_DIR = Path(__file__).resolve().parent / "schemas" / "functions"


def _schema(name: str) -> dict:
    """Load a committed contract — one source of truth, no inline copy."""
    return json.loads((_SCHEMAS_DIR / f"{name}.json").read_text(encoding="utf-8"))


@function("currencies.convert", schema=_schema("currencies.convert"))
def convert_function(payload: dict) -> dict:
    """Convert an amount between currencies via the base-currency cross rate.

    Payload: ``{"amount": "<decimal string>", "from_currency": "USD",
    "to_currency": "EUR"}``. Returns ``{"amount": "<decimal string>"}``
    quantized to ``CONVERSION_DECIMAL_PLACES``. Amounts are strings on the
    wire, ``Decimal`` internally — floats never touch money.

    Raises ``UnknownCurrencyError`` (carries ``error.400.unknown_currency``)
    for a missing/inactive code and ``ValueError`` with
    ``error.400.invalid_amount`` for an unparseable amount.
    """
    from . import services

    try:
        amount = Decimal(payload["amount"])
    except InvalidOperation:
        raise ValueError(
            f"{ERR_400_INVALID_AMOUNT}: {payload['amount']!r} is not a decimal"
        ) from None

    result = services.convert(amount, payload["from_currency"], payload["to_currency"])
    return {"amount": str(result)}
