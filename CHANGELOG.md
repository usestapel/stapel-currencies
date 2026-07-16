# Changelog

All notable changes to stapel-currencies are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Pre-1.0 semver: **minor = breaking**, patch = compatible.

## [0.1.5] - 2026-07-17

### Changed
- `stapel-core` ceiling raised `>=0.10,<0.11` → `>=0.10,<0.12` (core 0.11
  fleet re-pin: default bus, nav, config-checks, error params/language —
  additive for modules). Suite green as-is.

## [0.1.2] - 2026-07-06

### Changed
- Pinned `stapel-core` to the `>=0.8,<0.9` window (library-standard §7.1: one
  minor window; floor `0.8.0` is published on PyPI — no pin into the void).
- CI: added the release-track job (library-standard §7.4) — installs the package
  the way an end user does (`pip install .`, dependencies resolved from PyPI
  strictly by the declared pins, no git-main core, no editable siblings), asserts
  `stapel-core` resolves inside the `0.8` window, and runs an import smoke.
  Advisory (continue-on-error) until the whole stapel graph is on PyPI; becomes
  the blocking precondition for a `vX.Y.Z` tag once it is.


## [0.1.1] - 2026-07-06

### Packaging
- Tests excluded from the built wheel/sdist (the `stapel_currencies.tests`
  subpackage is no longer listed in `[tool.setuptools] packages`). Added
  `[project.urls]`, completed the trove classifiers (MIT/OSI, Python 3.13,
  `Typing :: Typed`, OS Independent, `3 :: Only`, Development Status) and a
  `[tool.ruff]` lint section (single source shared with the git hooks/CI).


## [0.1.0] - 2026-07-04

Initial release. Ported from the `currencies` app of a legacy catalog codebase
(Currency model with ISO-code PK, ECB daily-rate refresh, default-currency
seeding, read-only currency API) onto the Stapel library standard.

### Added
- `Currency` model — ISO 4217 `code` PK, `display_name` translation key,
  `symbol`, `is_active`, and a **`Decimal` `value`** (rate vs the base
  currency; the source used floats).
- **Base currency is a setting, not hardcoded EUR**:
  `STAPEL_CURRENCIES["BASE_CURRENCY"]` (default `"EUR"`). `value` semantics
  = rate vs base; the source's `to_eur`/`from_eur` helpers became
  `to_base`/`from_base`, derived from the setting.
- **Rate source is a dotted-path provider seam**:
  `STAPEL_CURRENCIES["RATE_PROVIDER"]` (default
  `"stapel_currencies.providers.ECBRateProvider"`) resolving to a
  `RateProvider` ABC with `fetch_rates() -> dict[str, Decimal]` and
  `RateFetchError`. The ECB provider ports the `eurofxref-daily.xml` fetch
  and additionally **rebases the feed when the base currency is not EUR**.
- **comm Function `currencies.convert`** (new — the source had no
  service-to-service surface): `{"amount": "<decimal string>",
  "from_currency", "to_currency"} -> {"amount": "<decimal string>"}`,
  JSON schema in `schemas/functions/currencies.convert.json`, validated in
  tests. Strings on the wire, `Decimal` internally, results quantized to
  `CONVERSION_DECIMAL_PLACES` (default 2, ROUND_HALF_UP) — supports
  non-base -> non-base cross rates.
- `services.convert` / `services.update_exchange_rates` — shared domain
  logic behind the Function, the `update_exchange_rates` management
  command (`--dry-run`, renamed from the source's `load_exchange_rates`)
  and the Celery task `stapel_currencies.tasks.update_exchange_rates`;
  all three go through the provider seam.
- `DEFAULT_CURRENCIES` seed list is a setting (the source hardcoded it in
  the command); `load_default_currencies` reads it (`--force` upserts).
- Error keys via `register_service_errors`: `error.400.unknown_currency`,
  `error.400.invalid_amount`, `error.502.rate_fetch_failed`;
  `UnknownCurrencyError` carries the key to HTTP and comm callers.
- System checks `stapel_currencies.W001`/`W002` — unimportable /
  non-`RateProvider` `RATE_PROVIDER` warns instead of blocking deploys.
- Read-only `CurrencyViewSet` (list + retrieve by ISO code, active only);
  writes stay in the Django admin. Mounted by the host at `currencies/`.

### Changed (vs the legacy catalog)
- Rate updates no longer create-or-skip silently around unknown feed
  codes: unknown codes are reported and never auto-created.
- All float money math replaced with `Decimal`; API renders `value` as a
  decimal string.
