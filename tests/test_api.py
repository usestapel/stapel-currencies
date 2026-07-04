"""HTTP API: read-only currency catalog (writes go through the admin)."""
from decimal import Decimal

import pytest

from stapel_currencies.models import Currency

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def catalog():
    Currency.objects.create(
        code="EUR", display_name="currency.eur", symbol="€", value=Decimal("1")
    )
    Currency.objects.create(
        code="USD", display_name="currency.usd", symbol="$", value=Decimal("1.08")
    )
    Currency.objects.create(
        code="OLD", display_name="currency.old", value=Decimal("2"), is_active=False
    )


class TestCurrencyList:
    def test_lists_active_currencies_only(self, api_client):
        resp = api_client.get("/currencies/api/")
        assert resp.status_code == 200
        codes = [item["code"] for item in resp.json()]
        assert codes == ["EUR", "USD"]

    def test_value_is_a_decimal_string(self, api_client):
        resp = api_client.get("/currencies/api/")
        usd = next(item for item in resp.json() if item["code"] == "USD")
        assert usd["value"] == "1.08000000"
        assert usd["symbol"] == "$"
        assert usd["display_name"] == "currency.usd"


class TestCurrencyRetrieve:
    def test_retrieve_by_iso_code(self, api_client):
        resp = api_client.get("/currencies/api/USD/")
        assert resp.status_code == 200
        assert resp.json()["code"] == "USD"

    def test_optional_trailing_slash(self, api_client):
        assert api_client.get("/currencies/api/USD").status_code == 200

    def test_inactive_currency_is_404(self, api_client):
        assert api_client.get("/currencies/api/OLD/").status_code == 404

    def test_unknown_currency_is_404(self, api_client):
        assert api_client.get("/currencies/api/ZZZ/").status_code == 404


class TestApiIsReadOnly:
    def test_post_is_rejected(self, api_client):
        resp = api_client.post("/currencies/api/", {"code": "XXX"}, format="json")
        assert resp.status_code == 405

    def test_put_is_rejected(self, api_client):
        resp = api_client.put("/currencies/api/USD/", {"value": "9"}, format="json")
        assert resp.status_code == 405

    def test_delete_is_rejected(self, api_client):
        assert api_client.delete("/currencies/api/USD/").status_code == 405
