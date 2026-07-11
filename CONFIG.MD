# CONFIG.MD — stapel-currencies

Config registry for **stapel-currencies** (`static-scaffold-and-config.md` §2).
One row per configuration key the module reads, its **source** (`env` = the
process environment / the `STAPEL_CURRENCIES` settings dict), what it is for,
whether it is required, and its default.

Every key is read through `currencies_settings`
(`stapel_currencies.conf.AppSettings`, namespace `STAPEL_CURRENCIES`).
Resolution order per key: `settings.STAPEL_CURRENCIES` dict → a flat Django
setting of the same name → environment variable → the default below.

## stapel-currencies

| Key | Source | Purpose | Required | Default |
|-----|--------|---------|----------|---------|
| BASE_CURRENCY | env | ISO 4217 code every Currency.value rate is relative to (base converts at rate 1). | no | USD |
| RATE_PROVIDER | env | dotted path to a RateProvider subclass — the exchange-rate source seam (REPLACE). | no | stapel_currencies.providers.ECBRateProvider |
| DEFAULT_CURRENCIES | env | seed list for the `load_default_currencies` command (code/display_name/symbol/value dicts). | no | 16 built-in currencies (USD base) |
| CONVERSION_DECIMAL_PLACES | env | decimal places conversion results are quantized to (ROUND_HALF_UP). | no | 2 |
