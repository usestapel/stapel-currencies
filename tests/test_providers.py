"""Rate providers: ECB XML parsing (requests mocked), rebasing, failures."""
from decimal import Decimal

import pytest
import requests
from django.test import override_settings

from stapel_currencies.providers import ECBRateProvider, RateFetchError

ECB_XML = """<?xml version="1.0" encoding="UTF-8"?>
<gesmes:Envelope xmlns:gesmes="http://www.gesmes.org/xml/2002-08-01"
                 xmlns="http://www.ecb.int/vocabulary/2002-08-01/eurofxref">
  <gesmes:subject>Reference rates</gesmes:subject>
  <Cube>
    <Cube time="2026-07-03">
      <Cube currency="USD" rate="1.08"/>
      <Cube currency="GBP" rate="0.85"/>
      <Cube currency="JPY" rate="169.53"/>
      <Cube currency="ZAR"/>
    </Cube>
  </Cube>
</gesmes:Envelope>
"""

ECB_XML_BAD_RATE = ECB_XML.replace('rate="0.85"', 'rate="n/a"')


class _FakeResponse:
    def __init__(self, text, status_ok=True):
        self.text = text
        self._status_ok = status_ok

    def raise_for_status(self):
        if not self._status_ok:
            raise requests.HTTPError("503 Service Unavailable")


def _mock_get(monkeypatch, text, status_ok=True):
    calls = []

    def fake_get(url, timeout=None):
        calls.append((url, timeout))
        return _FakeResponse(text, status_ok=status_ok)

    monkeypatch.setattr("stapel_currencies.providers.requests.get", fake_get)
    return calls


class TestECBRateProvider:
    @override_settings(STAPEL_CURRENCIES={"BASE_CURRENCY": "EUR"})
    def test_parses_rates_as_decimals(self, monkeypatch):
        # The ECB feed is natively EUR-relative — this is the no-rebase path.
        calls = _mock_get(monkeypatch, ECB_XML)
        rates = ECBRateProvider().fetch_rates()
        assert rates == {
            "USD": Decimal("1.08"),
            "GBP": Decimal("0.85"),
            "JPY": Decimal("169.53"),
        }
        assert all(isinstance(rate, Decimal) for rate in rates.values())
        assert calls == [(ECBRateProvider.url, 30)]

    @override_settings(STAPEL_CURRENCIES={"BASE_CURRENCY": "EUR"})
    def test_unparseable_rate_is_skipped(self, monkeypatch):
        _mock_get(monkeypatch, ECB_XML_BAD_RATE)
        rates = ECBRateProvider().fetch_rates()
        assert "GBP" not in rates
        assert rates["USD"] == Decimal("1.08")

    def test_network_error_raises_rate_fetch_error(self, monkeypatch):
        def fake_get(url, timeout=None):
            raise requests.ConnectionError("no route to host")

        monkeypatch.setattr("stapel_currencies.providers.requests.get", fake_get)
        with pytest.raises(RateFetchError):
            ECBRateProvider().fetch_rates()

    def test_http_error_raises_rate_fetch_error(self, monkeypatch):
        _mock_get(monkeypatch, ECB_XML, status_ok=False)
        with pytest.raises(RateFetchError):
            ECBRateProvider().fetch_rates()

    def test_malformed_xml_raises_rate_fetch_error(self, monkeypatch):
        _mock_get(monkeypatch, "this is not XML")
        with pytest.raises(RateFetchError, match="parse"):
            ECBRateProvider().fetch_rates()

    def test_empty_feed_raises_rate_fetch_error(self, monkeypatch):
        _mock_get(monkeypatch, "<Envelope/>")
        with pytest.raises(RateFetchError, match="no exchange rates"):
            ECBRateProvider().fetch_rates()


class TestECBRebasing:
    @override_settings(STAPEL_CURRENCIES={"BASE_CURRENCY": "USD"})
    def test_rates_are_rebased_to_the_configured_base(self, monkeypatch):
        _mock_get(monkeypatch, ECB_XML)
        rates = ECBRateProvider().fetch_rates()
        # vs USD: EUR = 1/1.08, GBP = 0.85/1.08; USD itself dropped.
        assert "USD" not in rates
        assert rates["EUR"] == Decimal(1) / Decimal("1.08")
        assert rates["GBP"] == Decimal("0.85") / Decimal("1.08")
        assert rates["JPY"] == Decimal("169.53") / Decimal("1.08")

    @override_settings(STAPEL_CURRENCIES={"BASE_CURRENCY": "XXX"})
    def test_base_missing_from_feed_raises(self, monkeypatch):
        _mock_get(monkeypatch, ECB_XML)
        with pytest.raises(RateFetchError, match="XXX"):
            ECBRateProvider().fetch_rates()
