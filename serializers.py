"""Serializers for the stapel-currencies API."""
from rest_framework import serializers

from .models import Currency


class CurrencySerializer(serializers.ModelSerializer):
    """``value`` is rendered as a decimal string — floats never touch money."""

    class Meta:
        model = Currency
        fields = ["code", "display_name", "value", "symbol", "is_active"]
