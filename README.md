# stapel-currencies

[![CI](https://github.com/usestapel/stapel-currencies/actions/workflows/ci.yml/badge.svg)](https://github.com/usestapel/stapel-currencies/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/usestapel/stapel-currencies/graph/badge.svg)](https://codecov.io/gh/usestapel/stapel-currencies)
[![PyPI](https://img.shields.io/pypi/v/stapel-currencies.svg)](https://pypi.org/project/stapel-currencies/)

> Currencies and exchange rates — configurable base currency, pluggable rate
> providers (ECB by default), cross-rate conversion as a comm Function

Part of the [Stapel framework](https://github.com/usestapel) — composable Django apps
that deploy as a monolith or as microservices without changing module code.

## Install

```bash
pip install stapel-currencies
```

```python
# settings.py
INSTALLED_APPS = [
    # ...
    "stapel_currencies",
]

# urls.py
path("currencies/", include("stapel_currencies.urls"))
```

Seed the catalog and pull live rates:

```bash
python manage.py migrate
python manage.py load_default_currencies
python manage.py update_exchange_rates          # ECB by default; --dry-run supported
```

Or schedule the Celery task:

```python
CELERY_BEAT_SCHEDULE = {
    "update-exchange-rates": {
        "task": "stapel_currencies.tasks.update_exchange_rates",
        "schedule": crontab(hour=16, minute=30),  # ECB publishes ~16:00 CET
    },
}
```

## Converting

```python
from decimal import Decimal
from stapel_core.comm import call

call("currencies.convert", {
    "amount": "100.00",          # decimal strings on the wire
    "from_currency": "USD",
    "to_currency": "GBP",        # non-base pairs go via the base cross rate
})
# -> {"amount": "78.70"}

# In-process, same math:
from stapel_currencies import convert
convert(Decimal("100"), "USD", "GBP")  # Decimal("78.70")
```

## Settings

All configuration lives in the `STAPEL_CURRENCIES` namespace (dict setting, flat
setting, or env var — resolved lazily):

| Key | Default | Meaning |
|---|---|---|
| `BASE_CURRENCY` | `"USD"` | ISO code all stored rates are relative to (base = 1). |
| `RATE_PROVIDER` | `"stapel_currencies.providers.ECBRateProvider"` | Dotted path to a `RateProvider` subclass — the rate-source seam. |
| `DEFAULT_CURRENCIES` | 16 major world currencies | Seed list for `load_default_currencies`. |
| `CONVERSION_DECIMAL_PLACES` | `2` | Quantization of conversion results (ROUND_HALF_UP). |

## HTTP API

Read-only (writes happen via the Django admin and the rate-update task):

| Route | Meaning |
|---|---|
| `GET currencies/api/` | Active currencies (code, display_name, value, symbol, is_active). |
| `GET currencies/api/<code>/` | One currency by ISO code. |

## comm surface

| Kind | Name | Contract |
|---|---|---|
| Function | `currencies.convert` | `{"amount": "<decimal str>", "from_currency", "to_currency"}` -> `{"amount": "<decimal str>"}` — [schema](schemas/functions/currencies.convert.json) |

## Extension points

See [MODULE.md](MODULE.md) — the agent-facing map of every fork-free seam (settings,
the `RateProvider` ABC with a custom-provider recipe, serializer seam, comm surface,
system checks).

## Development

```bash
pip install -e . && pip install pytest pytest-django pytest-cov ruff jsonschema
./setup-hooks.sh
pytest tests/
```

## License

MIT
