# stapel-currencies — MODULE.md

Agent-facing map of this module: what it provides, its fork-free extension points, and
anti-patterns. Use it to classify a desired change as **app-layer override via an
extension point** vs **upstream contribution** (see `docs/stdlib-contribution-pipeline.md`
in the Stapel monorepo). Stapel modules never import each other; all cross-module
communication goes through `stapel-core` (comm bus, signals, registries). Everything
below is verifiable against the code in this repo.

- Package: `stapel-currencies` (PyPI), Python package `stapel_currencies`, Django app label `currencies`.
- Depends on `stapel-core` only (plus `requests` for the ECB provider and `celery` for the rate-refresh task).
- Provenance: ported from `legacy-catalog/currencies` with the base currency and rate
  source turned into seams and a comm Function added (see CHANGELOG 0.1.0).

## What this module provides

| Area | Contents |
|---|---|
| Models (`models.py`) | `Currency` — PK is the ISO 4217 `code`; `value` is a `Decimal` exchange rate relative to the configured base currency (base = 1); `display_name` (translation key), `symbol`, `is_active`. Helpers `to_base()` / `from_base()` derive from `BASE_CURRENCY`. |
| Services (`services.py`) | `convert(amount, from_currency, to_currency)` — cross-rate conversion via the base currency, quantized (`ROUND_HALF_UP`); `get_rate_provider()`; `update_exchange_rates(dry_run=False)` — fetches from the provider seam and updates the catalog; `UnknownCurrencyError`. |
| Providers (`providers.py`) | `RateProvider` ABC (the rate-source seam), `ECBRateProvider` default (ECB `eurofxref-daily.xml`, rebased when the base currency is not EUR), `RateFetchError`. |
| HTTP API (`urls.py`, `views.py`) | `CurrencyViewSet` — public read-only list/retrieve of active currencies (`api/`, `api/<code>/` relative to the host mount, e.g. `currencies/`). Writes go through the Django admin. |
| comm surface (`functions.py`, `schemas/`) | Function `currencies.convert` — decimal-string amounts on the wire, schema-validated. |
| Tasks & commands | Celery task `stapel_currencies.tasks.update_exchange_rates`; management commands `load_default_currencies` (seed from settings) and `update_exchange_rates` (same provider seam, `--dry-run`). |
| Public API (`__init__.py`, PEP 562 lazy) | `__all__ = ["ECBRateProvider", "RateFetchError", "RateProvider", "UnknownCurrencyError", "convert", "currencies_settings"]` |

Money/rate discipline: **strings on the wire, `Decimal` internally, floats never.**
Conversion results are quantized to `CONVERSION_DECIMAL_PLACES` (ROUND_HALF_UP);
intermediate cross-rate math keeps full precision.

## Admin categories (AS-5 `@access` review)

`models.py` has exactly one model, `Currency`, and it is left **undecorated**
(implicit `@access.standard` — business/domain table, matching the doc's `Category`
example): it is a curated reference/lookup catalog that staff read and correct by hand
through `CurrencyAdmin` (rate corrections, `is_active` toggling) — the opposite of
ops-junk nobody is expected to touch. It carries no token/secret/credential field, so
`@access.secret` does not apply either.

Checked the rest of the module for a hiding ops/secret candidate before concluding
zero-decorator: the ECB rate provider (`providers.py`) is a stateless, unauthenticated
HTTP GET against a public XML feed — no API key, no persisted request/response log, no
dedup/idempotency table. `update_exchange_rates` (`services.py`, the management command,
and the Celery task) mutates existing `Currency` rows in place and does not write any
audit/delivery-log or TTL-expiring row. There is no second model anywhere in the repo
(`grep -rn "models.Model"` returns only `Currency`). Nothing else to classify.

Disputed: none.

## Extension points (fork-free)

### Settings — `STAPEL_CURRENCIES` namespace (`conf.py`)

`currencies_settings = AppSettings("STAPEL_CURRENCIES", ...)` from `stapel_core.conf`.
Resolution order per key: `settings.STAPEL_CURRENCIES[key]` → flat Django setting of the
same name → environment variable → default. All keys are read **lazily at call time**
(never frozen at import); caches invalidate on `setting_changed`.

| Key | Default | What it customizes |
|---|---|---|
| `BASE_CURRENCY` | `"EUR"` | ISO 4217 code every `Currency.value` rate is relative to. The base currency always converts with rate 1 (even if its stored `value` drifts). Changing it reinterprets stored rates — re-run `update_exchange_rates` after switching. |
| `RATE_PROVIDER` | `"stapel_currencies.providers.ECBRateProvider"` | The exchange-rate source. In `import_strings` — resolved via `import_string`, must be a `RateProvider` subclass (enforced by `get_rate_provider()`). Single strategy, **REPLACE** semantics (dotted path), not a registry. |
| `DEFAULT_CURRENCIES` | 16 European currencies (`conf.DEFAULT_CURRENCIES`) | Seed list read by `load_default_currencies`: dicts with `code` / `display_name` / `symbol` / `value` (rate vs `BASE_CURRENCY`, as a decimal **string**). Replaces the default list wholesale. |
| `CONVERSION_DECIMAL_PLACES` | `2` | Decimal places conversion results are quantized to (ROUND_HALF_UP) — in `services.convert` and the `currencies.convert` Function. |

### Rate providers (dotted-path swap)

Implement the ABC `stapel_currencies.providers.RateProvider` and point the setting at
it — no fork:

```python
# myproject/rates.py
from decimal import Decimal
from stapel_currencies import RateProvider, RateFetchError

class OpenExchangeRatesProvider(RateProvider):
    name = "oxr"

    def fetch_rates(self) -> dict[str, Decimal]:
        # Return rates relative to STAPEL_CURRENCIES["BASE_CURRENCY"]:
        # 1 unit of base = rate units of the keyed currency.
        # Raise RateFetchError when the source is down/unusable.
        ...

# settings.py
STAPEL_CURRENCIES = {"RATE_PROVIDER": "myproject.rates.OpenExchangeRatesProvider"}
```

ABC contract:

| Method | Signature | Contract |
|---|---|---|
| `fetch_rates` | `() -> dict[str, Decimal]` | Rates **relative to the configured base currency** (`Decimal`, never float). The base itself need not appear. Raises `RateFetchError` on any failure — callers (command, Celery task) own the degradation policy. |

Rules for providers: read configuration lazily at call time via `currencies_settings`
(never at import); codes in the result that have no `Currency` row are *reported, not
created* — the catalog stays curated. `ECBRateProvider` shows the rebasing pattern for
sources that quote against a fixed currency (`url` / `timeout` are class attributes —
subclass to change).

Both entry points use the seam: the `update_exchange_rates` management command and the
`stapel_currencies.tasks.update_exchange_rates` Celery task (schedule it in the host's
`CELERY_BEAT_SCHEDULE`; the task returns 0 and logs on `RateFetchError` — stored rates
keep serving conversions).

### Swappable models

None. `Currency` has a fixed table; it references no user and no other service. Extend
currency-adjacent data in an app-layer model with a FK to `Currency` — do not fork to
add fields.

### Serializer seams (`views.py`)

`CurrencyViewSet` is a `ReadOnlyModelViewSet`; its seam is DRF's own: subclass, set
`serializer_class` (or override `get_serializer_class()`), and remount the URL in the
host project. There is no request serializer (the API is read-only), so the
`request_serializer_class`/`response_serializer_class` mixin pattern used by
request/response APIViews elsewhere in Stapel does not apply here — this is the
documented exception per library-standard §3.4.

| View | Route (name) | Serializer |
|---|---|---|
| `CurrencyViewSet` | `currency-list`, `currency-detail` | `CurrencySerializer` (`value` rendered as a decimal string) |

### Events & functions (comm surface)

Transport-agnostic via `stapel_core.comm` (in-process in a monolith, bus in
microservices — same code). JSON Schemas live in `schemas/functions/` and are enforced
in tests (`VALIDATE_SCHEMAS: true`).

**Emits / consumes:** none.

**Functions provided:**

| Function | Payload | Returns | Schema |
|---|---|---|---|
| `currencies.convert` | `{"amount": "<decimal string>", "from_currency": "USD", "to_currency": "EUR"}` | `{"amount": "<decimal string>"}` (quantized) | `schemas/functions/currencies.convert.json` |

Failure contract: an unknown/inactive code raises through the comm layer carrying
`error.400.unknown_currency`; an unparseable amount carries `error.400.invalid_amount`
(the schema already rejects both shapes at the boundary).

### System checks (`checks.py`)

W-level on purpose — a broken rate provider degrades rate *freshness*, conversion keeps
working off stored rates, so it must not block deploys:

| ID | Meaning |
|---|---|
| `stapel_currencies.W001` | `RATE_PROVIDER` dotted path fails to import. |
| `stapel_currencies.W002` | `RATE_PROVIDER` resolves to something that is not a `RateProvider` subclass. |

### Error keys (`errors.py`)

`error.400.unknown_currency`, `error.400.invalid_amount`, `error.502.rate_fetch_failed`
— registered via `register_service_errors`; human-readable strings are translations,
never literals in responses.

## Anti-patterns

- **Don't fork to change the rate source.** Subclass `RateProvider` in the app layer
  and point `STAPEL_CURRENCIES["RATE_PROVIDER"]` at the dotted path.
- **Don't hardcode EUR.** The base currency is `STAPEL_CURRENCIES["BASE_CURRENCY"]`;
  use `Currency.to_base()/from_base()` / `services.convert()` — never `to_eur`-style
  helpers or literal `"EUR"` comparisons in app code.
- **No floats in money paths.** `value` is a `DecimalField`; comm payload amounts are
  decimal strings. A float anywhere between the wire and the DB is a review error.
- **Don't write currencies through the HTTP API** — it is read-only by design. The
  write surface is the Django admin, `DEFAULT_CURRENCIES` +
  `load_default_currencies`, and the rate-update task/command.
- **Don't create Currency rows from a rate feed.** `update_exchange_rates` updates
  existing rows and reports unknown codes; the catalog is curated, not feed-driven.
- **Don't import other `stapel-*` modules.** Callers use the `currencies.convert`
  Function by string name (`stapel_core.comm.call`) — that is how `stapel-listings`
  computes `price_base` without importing this package.
- **Don't read settings at import time** (`os.getenv`, module-level constants from
  settings). Go through `currencies_settings` at call time.

## App-layer override vs upstream contribution — rule of thumb

**App-layer override** (host-owned, no fork) when the change fits a seam above: another
rate source (`RATE_PROVIDER`), a different base currency (`BASE_CURRENCY` + re-run the
update), a custom seed catalog (`DEFAULT_CURRENCIES`), different rounding
(`CONVERSION_DECIMAL_PLACES`), a different list/detail payload (subclass the ViewSet +
remount), scheduling policy for the refresh task, extra currency-adjacent data (app-layer
model with a FK).

**Upstream contribution** (Stapel-owned, via the contribution pipeline) when the change
alters module-owned contracts: new fields/indexes on `Currency` (migrations live here),
changes to the `RateProvider` ABC surface, changes to the `currencies.convert` schema or
new comm functions/events, new endpoints, new error keys, conversion/quantization
semantics, bug fixes anywhere in this repo.

Litmus test: if you'd have to monkeypatch or edit code inside `stapel_currencies/` —
it's upstream. If a setting, subclass, or comm call gets you there — it's app-layer.
