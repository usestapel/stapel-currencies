"""Management commands: load_default_currencies and update_exchange_rates."""
from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.test import override_settings

from stapel_currencies.models import Currency

pytestmark = pytest.mark.django_db


def _run(command, *args):
    out, err = StringIO(), StringIO()
    call_command(command, *args, stdout=out, stderr=err)
    return out.getvalue(), err.getvalue()


class TestLoadDefaultCurrencies:
    def test_seeds_empty_table_from_setting_default(self):
        out, _ = _run("load_default_currencies")
        assert Currency.objects.count() == 16
        eur = Currency.objects.get(code="EUR")
        assert eur.display_name == "currency.eur"
        assert eur.symbol == "€"
        assert eur.value == Decimal("1.0")
        assert "16 created" in out

    def test_values_are_decimals(self):
        _run("load_default_currencies")
        assert Currency.objects.get(code="USD").value == Decimal("1.08")

    def test_non_empty_table_is_left_alone(self):
        Currency.objects.create(code="EUR", display_name="x", value=Decimal("9"))
        out, _ = _run("load_default_currencies")
        assert "Use --force" in out
        assert Currency.objects.count() == 1
        assert Currency.objects.get(code="EUR").value == Decimal("9")

    def test_force_upserts(self):
        Currency.objects.create(code="EUR", display_name="x", value=Decimal("9"))
        out, _ = _run("load_default_currencies", "--force")
        assert Currency.objects.count() == 16
        assert Currency.objects.get(code="EUR").value == Decimal("1.0")
        assert "15 created, 1 updated" in out

    @override_settings(
        STAPEL_CURRENCIES={
            "DEFAULT_CURRENCIES": [
                {"code": "CAD", "display_name": "currency.cad", "symbol": "$", "value": "1.47"},
            ]
        }
    )
    def test_seed_list_is_a_setting(self):
        _run("load_default_currencies")
        assert list(Currency.objects.values_list("code", flat=True)) == ["CAD"]
        assert Currency.objects.get(code="CAD").value == Decimal("1.47")

    @override_settings(
        STAPEL_CURRENCIES={"DEFAULT_CURRENCIES": [{"code": "CAD", "value": "not-a-number"}]}
    )
    def test_invalid_seed_entry_is_a_command_error(self):
        from django.core.management.base import CommandError

        with pytest.raises(CommandError, match="invalid DEFAULT_CURRENCIES entry"):
            _run("load_default_currencies")


class TestUpdateExchangeRatesCommand:
    @pytest.fixture(autouse=True)
    def catalog(self, settings):
        settings.STAPEL_CURRENCIES = {
            "RATE_PROVIDER": "stapel_currencies.tests.fakes.StaticRateProvider"
        }
        Currency.objects.create(code="USD", display_name="currency.usd", value=Decimal("1.08"))
        Currency.objects.create(code="GBP", display_name="currency.gbp", value=Decimal("0.85"))

    def test_updates_rates_via_provider_seam(self):
        out, _ = _run("update_exchange_rates")
        assert "Successfully updated 2 currencies" in out
        assert "Currencies not in database: XXX" in out
        assert Currency.objects.get(code="USD").value == Decimal("2")

    def test_dry_run_reports_without_writing(self):
        out, _ = _run("update_exchange_rates", "--dry-run")
        assert "Would update USD: 1.08000000 -> 2" in out
        assert "DRY RUN: Would update 2 currencies" in out
        assert Currency.objects.get(code="USD").value == Decimal("1.08")

    def test_provider_failure_is_reported_not_raised(self, settings):
        settings.STAPEL_CURRENCIES = {
            "RATE_PROVIDER": "stapel_currencies.tests.fakes.FailingRateProvider"
        }
        out, err = _run("update_exchange_rates")
        assert "Failed to fetch exchange rates: boom" in err
        assert "Successfully" not in out
