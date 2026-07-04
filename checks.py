"""Django system checks for stapel-currencies configuration.

Policy (docs/library-standard.md §3.7): E-level for configuration the
service cannot run with; W-level for entries that degrade lazily. The
rate provider is W-level on purpose: conversion works off stored rates
even when the provider is broken — a bad ``RATE_PROVIDER`` degrades rate
freshness, it must not block deploys. IDs:

- ``stapel_currencies.W001`` — ``RATE_PROVIDER`` dotted path fails to import.
- ``stapel_currencies.W002`` — ``RATE_PROVIDER`` resolves to something that
  is not a ``RateProvider`` subclass.
"""
from __future__ import annotations

import inspect

from django.core import checks


@checks.register("stapel_currencies")
def check_rate_provider(app_configs, **kwargs):
    from .conf import currencies_settings
    from .providers import RateProvider

    try:
        provider = currencies_settings.RATE_PROVIDER
    except ImportError as exc:
        return [
            checks.Warning(
                f"STAPEL_CURRENCIES['RATE_PROVIDER'] cannot be imported: {exc}",
                hint=(
                    "Fix the dotted path or install the missing dependency; "
                    "update_exchange_rates will fail until it resolves."
                ),
                id="stapel_currencies.W001",
            )
        ]
    if not (inspect.isclass(provider) and issubclass(provider, RateProvider)):
        return [
            checks.Warning(
                f"STAPEL_CURRENCIES['RATE_PROVIDER'] resolves to {provider!r}, "
                "which is not a stapel_currencies.providers.RateProvider subclass.",
                hint="Implement the RateProvider ABC (see MODULE.md).",
                id="stapel_currencies.W002",
            )
        ]
    return []


__all__ = ["check_rate_provider"]
