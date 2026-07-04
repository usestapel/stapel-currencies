"""Package-level public API (PEP 562 lazy exports) and import hygiene."""
import os
import subprocess
import sys

import stapel_currencies


class TestLazyExports:
    def test_all_declares_public_api(self):
        assert stapel_currencies.__all__ == [
            "ECBRateProvider",
            "RateFetchError",
            "RateProvider",
            "UnknownCurrencyError",
            "convert",
            "currencies_settings",
        ]

    def test_settings_resolve(self):
        from stapel_currencies.conf import currencies_settings

        assert stapel_currencies.currencies_settings is currencies_settings

    def test_provider_seam_exports_resolve(self):
        from stapel_currencies.providers import ECBRateProvider, RateProvider

        assert stapel_currencies.RateProvider is RateProvider
        assert stapel_currencies.ECBRateProvider is ECBRateProvider

    def test_service_exports_resolve(self):
        from stapel_currencies.services import UnknownCurrencyError, convert

        assert stapel_currencies.convert is convert
        assert stapel_currencies.UnknownCurrencyError is UnknownCurrencyError

    def test_unknown_attribute_raises(self):
        try:
            stapel_currencies.nonexistent_export
        except AttributeError as exc:
            assert "nonexistent_export" in str(exc)
        else:
            raise AssertionError("expected AttributeError")


class TestImportWithoutDjangoSettings:
    def test_package_import_is_django_free(self):
        """`import stapel_currencies` must not import Django nor require settings."""
        env = {k: v for k, v in os.environ.items() if k != "DJANGO_SETTINGS_MODULE"}
        code = (
            "import sys\n"
            "import stapel_currencies\n"
            'polluted = [m for m in sys.modules if m == "django" or m.startswith("django.")]\n'
            'assert not polluted, f"django imported at package import time: {polluted}"\n'
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            env=env,
            cwd=os.path.dirname(sys.executable),
        )
        assert result.returncode == 0, result.stderr
