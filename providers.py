"""Exchange-rate providers — the rate-source seam of stapel-currencies.

Subclass :class:`RateProvider` and point
``STAPEL_CURRENCIES["RATE_PROVIDER"]`` at the dotted path to swap the
rate source without forking::

    class AcmeRateProvider(RateProvider):
        name = "acme"

        def fetch_rates(self):
            return {"USD": Decimal("1.08"), ...}

    STAPEL_CURRENCIES = {"RATE_PROVIDER": "myproject.rates.AcmeRateProvider"}

The contract: ``fetch_rates()`` returns rates **relative to the configured
base currency** (``STAPEL_CURRENCIES["BASE_CURRENCY"]``) as ``Decimal``
values, and raises :class:`RateFetchError` when the source is unavailable
or unusable. Providers must read configuration lazily (at call time, via
``currencies_settings``), never at import.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation

import requests

from .conf import currencies_settings

logger = logging.getLogger(__name__)


class RateFetchError(Exception):
    """The rate source could not be fetched or produced no usable rates."""


class RateProvider(ABC):
    """Base class for exchange-rate sources (ECB by default)."""

    #: Short human-readable provider name ("ecb", "acme", ...).
    name: str = ""

    @abstractmethod
    def fetch_rates(self) -> dict[str, Decimal]:
        """Return ``{currency_code: rate}`` relative to the base currency.

        1 unit of ``STAPEL_CURRENCIES["BASE_CURRENCY"]`` = ``rate`` units
        of ``currency_code``. The base currency itself need not appear in
        the result. Raises :class:`RateFetchError` on failure.
        """


class ECBRateProvider(RateProvider):
    """Daily reference rates from the European Central Bank (free XML feed).

    The ECB publishes rates relative to EUR. When
    ``STAPEL_CURRENCIES["BASE_CURRENCY"]`` is not EUR, the feed is rebased:
    every rate is divided by the base currency's EUR rate and an ``EUR``
    entry is added — so the returned dict always honors the provider
    contract (rates vs the configured base).
    """

    name = "ecb"
    url = "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
    timeout = 30

    _XML_NAMESPACES = {
        "gesmes": "http://www.gesmes.org/xml/2002-08-01",
        "eurofxref": "http://www.ecb.int/vocabulary/2002-08-01/eurofxref",
    }

    def fetch_rates(self) -> dict[str, Decimal]:
        try:
            response = requests.get(self.url, timeout=self.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            raise RateFetchError(f"failed to fetch ECB rates: {exc}") from exc

        eur_rates = self._parse_ecb_xml(response.text)
        if not eur_rates:
            raise RateFetchError("no exchange rates found in ECB response")

        base = currencies_settings.BASE_CURRENCY
        if base == "EUR":
            return eur_rates
        return self._rebase(eur_rates, base)

    def _rebase(self, eur_rates: dict[str, Decimal], base: str) -> dict[str, Decimal]:
        if base not in eur_rates:
            raise RateFetchError(
                f"base currency {base!r} is not in the ECB feed; "
                "use a provider that quotes it"
            )
        base_rate = eur_rates[base]
        rebased = {
            code: rate / base_rate for code, rate in eur_rates.items() if code != base
        }
        rebased["EUR"] = Decimal(1) / base_rate
        return rebased

    def _parse_ecb_xml(self, xml_content: str) -> dict[str, Decimal]:
        """Parse the ECB XML feed into ``{code: Decimal rate}`` (vs EUR)."""
        try:
            root = ET.fromstring(xml_content)
        except ET.ParseError as exc:
            raise RateFetchError(f"failed to parse ECB XML: {exc}") from exc

        rates: dict[str, Decimal] = {}
        for cube in root.findall(".//eurofxref:Cube[@currency]", self._XML_NAMESPACES):
            code = cube.get("currency")
            rate = cube.get("rate")
            if not code or not rate:
                continue
            try:
                rates[code] = Decimal(rate)
            except InvalidOperation:
                logger.warning("ECB feed: unparseable rate %r for %s — skipped", rate, code)
                continue
        return rates


__all__ = ["RateProvider", "ECBRateProvider", "RateFetchError"]
