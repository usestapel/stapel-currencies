"""Rate-update service: provider seam (dotted-path swap) and degradation."""
from decimal import Decimal

import pytest
from django.core.exceptions import ImproperlyConfigured
from django.test import override_settings

from stapel_currencies.models import Currency
from stapel_currencies.providers import ECBRateProvider, RateFetchError
from stapel_currencies.services import get_rate_provider, update_exchange_rates
from stapel_currencies.tests.fakes import StaticRateProvider

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalog():
    Currency.objects.create(code="EUR", display_name="currency.eur", value=Decimal("1"))
    Currency.objects.create(code="USD", display_name="currency.usd", value=Decimal("1.08"))
    Currency.objects.create(code="GBP", display_name="currency.gbp", value=Decimal("0.85"))


class TestProviderSeam:
    def test_default_provider_is_ecb(self):
        assert isinstance(get_rate_provider(), ECBRateProvider)

    @override_settings(
        STAPEL_CURRENCIES={"RATE_PROVIDER": "stapel_currencies.tests.fakes.StaticRateProvider"}
    )
    def test_provider_swapped_via_settings(self):
        assert isinstance(get_rate_provider(), StaticRateProvider)

    @override_settings(
        STAPEL_CURRENCIES={"RATE_PROVIDER": "stapel_currencies.tests.fakes.NotAProvider"}
    )
    def test_non_provider_class_is_rejected(self):
        with pytest.raises(ImproperlyConfigured):
            get_rate_provider()


class TestUpdateExchangeRates:
    @pytest.fixture(autouse=True)
    def static_provider(self, settings):
        settings.STAPEL_CURRENCIES = {
            "RATE_PROVIDER": "stapel_currencies.tests.fakes.StaticRateProvider"
        }

    def test_updates_known_currencies_and_reports_unknown(self):
        stats = update_exchange_rates()
        assert [(code, new) for code, _, new in stats["updated"]] == [
            ("GBP", Decimal("0.5")),
            ("USD", Decimal("2")),
        ]
        assert stats["not_found"] == ["XXX"]
        assert Currency.objects.get(code="USD").value == Decimal("2")
        assert Currency.objects.get(code="GBP").value == Decimal("0.5")
        # Currencies missing from the feed keep their stored rate.
        assert Currency.objects.get(code="EUR").value == Decimal("1")

    def test_unknown_codes_are_not_created(self):
        update_exchange_rates()
        assert not Currency.objects.filter(code="XXX").exists()

    def test_dry_run_writes_nothing(self):
        stats = update_exchange_rates(dry_run=True)
        assert len(stats["updated"]) == 2
        assert Currency.objects.get(code="USD").value == Decimal("1.08")

    def test_provider_failure_propagates(self, settings):
        settings.STAPEL_CURRENCIES = {
            "RATE_PROVIDER": "stapel_currencies.tests.fakes.FailingRateProvider"
        }
        with pytest.raises(RateFetchError):
            update_exchange_rates()
        assert Currency.objects.get(code="USD").value == Decimal("1.08")
