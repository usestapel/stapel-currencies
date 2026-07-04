"""Admin for the currency catalog — the staff-facing write surface.

The HTTP API is read-only by design; creating currencies, toggling
``is_active`` and correcting rates by hand happens here.
"""
from django.contrib import admin

from .models import Currency


@admin.register(Currency)
class CurrencyAdmin(admin.ModelAdmin):
    list_display = ["code", "display_name", "symbol", "value", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["code", "display_name"]
    ordering = ["code"]
