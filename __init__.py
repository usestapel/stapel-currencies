"""stapel-currencies — Currencies and exchange rates for the Stapel framework.

Public API (lazily exported, PEP 562 — importing this package never pulls
in Django or requires configured settings):

- ``currencies_settings`` — resolved app settings (``stapel_currencies.conf``).
- ``RateProvider`` / ``ECBRateProvider`` — the exchange-rate source seam.
- ``RateFetchError`` — raised when the rate source is unavailable.
- ``UnknownCurrencyError`` — raised for a missing/inactive currency code.
- ``convert`` — cross-rate conversion via the configured base currency.
"""

__all__ = [
    "ECBRateProvider",
    "RateFetchError",
    "RateProvider",
    "UnknownCurrencyError",
    "convert",
    "currencies_settings",
]

# name -> submodule that defines it. Resolution is deferred until first
# attribute access so that `import stapel_currencies` stays Django-free.
_LAZY_EXPORTS = {
    "currencies_settings": ".conf",
    "RateProvider": ".providers",
    "ECBRateProvider": ".providers",
    "RateFetchError": ".providers",
    "UnknownCurrencyError": ".services",
    "convert": ".services",
}


def __getattr__(name):
    if name in _LAZY_EXPORTS:
        from importlib import import_module

        value = getattr(import_module(_LAZY_EXPORTS[name], __name__), name)
        globals()[name] = value  # cache for subsequent lookups
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(set(globals()) | set(__all__))
