"""Settings namespace for stapel-currencies.

All configuration is read through ``currencies_settings`` (lazily, at call
time) — never via module-level ``os.getenv`` (values would freeze at import).
Resolution order per key: ``settings.STAPEL_CURRENCIES`` dict -> flat Django
setting of the same name -> environment variable -> default below.

Dotted-path keys listed in ``import_strings`` are resolved with
``import_string`` — the fork-free escape hatch for swappable behavior.
"""
from stapel_core.conf import AppSettings

# Seed list for the ``load_default_currencies`` management command.
# ``value`` is the exchange rate relative to ``BASE_CURRENCY`` — decimal
# strings, never floats. These are bootstrap placeholders that assume the
# default USD base; run ``update_exchange_rates`` (or schedule the Celery
# task) to replace them with live rates from the configured provider.
DEFAULT_CURRENCIES = [
    {"code": "USD", "display_name": "currency.usd", "symbol": "$", "value": "1.0"},
    {"code": "EUR", "display_name": "currency.eur", "symbol": "€", "value": "0.93"},
    {"code": "GBP", "display_name": "currency.gbp", "symbol": "£", "value": "0.79"},
    {"code": "CHF", "display_name": "currency.chf", "symbol": "CHF", "value": "0.87"},
    {"code": "PLN", "display_name": "currency.pln", "symbol": "zł", "value": "4.0"},
    {"code": "CZK", "display_name": "currency.czk", "symbol": "Kč", "value": "23.15"},
    {"code": "SEK", "display_name": "currency.sek", "symbol": "kr", "value": "10.65"},
    {"code": "NOK", "display_name": "currency.nok", "symbol": "kr", "value": "10.93"},
    {"code": "DKK", "display_name": "currency.dkk", "symbol": "kr", "value": "6.91"},
    {"code": "HUF", "display_name": "currency.huf", "symbol": "Ft", "value": "365.74"},
    {"code": "RON", "display_name": "currency.ron", "symbol": "lei", "value": "4.60"},
    {"code": "BGN", "display_name": "currency.bgn", "symbol": "лв", "value": "1.81"},
    {"code": "HRK", "display_name": "currency.hrk", "symbol": "kn", "value": "6.97"},
    {"code": "RSD", "display_name": "currency.rsd", "symbol": "дин.", "value": "108.33"},
    {"code": "UAH", "display_name": "currency.uah", "symbol": "₴", "value": "37.96"},
    {"code": "RUB", "display_name": "currency.rub", "symbol": "₽", "value": "92.59"},
]

currencies_settings = AppSettings(
    "STAPEL_CURRENCIES",
    defaults={
        # ISO 4217 code every Currency.value rate is relative to.
        # The base currency itself always converts with rate 1.
        "BASE_CURRENCY": "USD",
        # Dotted path to a stapel_currencies.providers.RateProvider
        # subclass — the exchange-rate source seam (single strategy,
        # REPLACE semantics).
        "RATE_PROVIDER": "stapel_currencies.providers.ECBRateProvider",
        # Seed list for the load_default_currencies command: list of
        # dicts with code / display_name / symbol / value keys
        # (value = rate vs BASE_CURRENCY as a decimal string).
        "DEFAULT_CURRENCIES": DEFAULT_CURRENCIES,
        # Decimal places conversion results are quantized to
        # (ROUND_HALF_UP).
        "CONVERSION_DECIMAL_PLACES": 2,
    },
    import_strings=("RATE_PROVIDER",),
)

__all__ = ["currencies_settings", "DEFAULT_CURRENCIES"]
