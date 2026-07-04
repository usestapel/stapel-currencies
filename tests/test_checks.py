"""System checks: RATE_PROVIDER misconfiguration surfaces as warnings."""
from django.test import override_settings

from stapel_currencies.checks import check_rate_provider


def test_default_configuration_is_clean():
    assert check_rate_provider(None) == []


@override_settings(
    STAPEL_CURRENCIES={"RATE_PROVIDER": "stapel_currencies.tests.fakes.StaticRateProvider"}
)
def test_custom_provider_is_clean():
    assert check_rate_provider(None) == []


@override_settings(STAPEL_CURRENCIES={"RATE_PROVIDER": "nope.does.NotExist"})
def test_unimportable_dotted_path_is_w001():
    issues = check_rate_provider(None)
    assert [issue.id for issue in issues] == ["stapel_currencies.W001"]
    # W-level: a broken provider degrades rate freshness, it must not
    # block deploys (conversion still works off stored rates).
    assert all(issue.level == 30 for issue in issues)  # checks.WARNING


@override_settings(
    STAPEL_CURRENCIES={"RATE_PROVIDER": "stapel_currencies.tests.fakes.NotAProvider"}
)
def test_non_provider_class_is_w002():
    issues = check_rate_provider(None)
    assert [issue.id for issue in issues] == ["stapel_currencies.W002"]
