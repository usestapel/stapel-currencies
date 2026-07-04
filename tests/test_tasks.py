"""Celery task: same RATE_PROVIDER seam, degrades to 0 on provider failure."""
from decimal import Decimal

import pytest
from django.test import override_settings

from stapel_currencies.models import Currency
from stapel_currencies.tasks import update_exchange_rates

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalog():
    Currency.objects.create(code="USD", display_name="currency.usd", value=Decimal("1.08"))
    Currency.objects.create(code="GBP", display_name="currency.gbp", value=Decimal("0.85"))


@override_settings(
    STAPEL_CURRENCIES={"RATE_PROVIDER": "stapel_currencies.tests.fakes.StaticRateProvider"}
)
def test_task_updates_rates_and_returns_count():
    assert update_exchange_rates() == 2
    assert Currency.objects.get(code="USD").value == Decimal("2")
    assert Currency.objects.get(code="GBP").value == Decimal("0.5")


@override_settings(
    STAPEL_CURRENCIES={"RATE_PROVIDER": "stapel_currencies.tests.fakes.FailingRateProvider"}
)
def test_task_returns_zero_on_provider_failure():
    assert update_exchange_rates() == 0
    assert Currency.objects.get(code="USD").value == Decimal("1.08")


def test_task_is_registered_with_celery():
    assert update_exchange_rates.name == "stapel_currencies.tasks.update_exchange_rates"
