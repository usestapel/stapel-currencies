"""Celery is not a dependency of stapel-currencies.

The rate refresh is a plain callable (cron, the management command); celery
only adds a task registration when it is installed. The package used to
import celery at module level and declare it to satisfy that import.
"""
import subprocess
import sys
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent

_TASKS_WITHOUT_CELERY = (
    "import sys; sys.modules['celery'] = None; "
    "import django; from django.conf import settings; "
    "settings.configure(INSTALLED_APPS=['django.contrib.contenttypes', 'stapel_currencies'], "
    "DATABASES={'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': ':memory:'}}); "
    "django.setup(); "
    "from stapel_currencies import tasks; "
    "print(callable(tasks.update_exchange_rates), hasattr(tasks.update_exchange_rates, 'delay'))"
)


def test_celery_is_not_a_declared_dependency():
    deps = tomllib.loads((REPO / "pyproject.toml").read_text())["project"]["dependencies"]
    assert not [d for d in deps if d.split(">")[0].split("=")[0].strip() == "celery"]


def test_the_rate_job_imports_and_is_plain_without_celery(tmp_path):
    proc = subprocess.run(
        [sys.executable, "-c", _TASKS_WITHOUT_CELERY],
        cwd=str(tmp_path), capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    assert proc.stdout.strip() == "True False"


def test_with_celery_it_is_a_named_task():
    from stapel_currencies.tasks import UPDATE_EXCHANGE_RATES_TASK, update_exchange_rates

    assert UPDATE_EXCHANGE_RATES_TASK == "stapel_currencies.tasks.update_exchange_rates"
    assert update_exchange_rates.name == UPDATE_EXCHANGE_RATES_TASK
