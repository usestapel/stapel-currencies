"""Scheduled jobs of stapel-currencies.

Celery is optional: ``update_exchange_rates`` is a plain callable a cron job
or the ``update_exchange_rates`` management command can invoke. When celery is
installed it is also registered as a celery task under
:data:`UPDATE_EXCHANGE_RATES_TASK`. Schedule the daily rate refresh in a host
that runs celery beat::

    CELERY_BEAT_SCHEDULE = {
        "update-exchange-rates": {
            "task": "stapel_currencies.tasks.update_exchange_rates",
            "schedule": crontab(hour=16, minute=30),  # after the ECB publishes (~16:00 CET)
        },
    }

The task goes through the same ``RATE_PROVIDER`` seam as the
``update_exchange_rates`` management command.
"""
import logging

logger = logging.getLogger(__name__)

UPDATE_EXCHANGE_RATES_TASK = "stapel_currencies.tasks.update_exchange_rates"


def update_exchange_rates() -> int:
    """Fetch rates from the configured provider and update the database.

    Returns the number of updated currencies; a provider failure is
    logged and returns 0 (the next beat run retries) — stored rates keep
    serving conversions in the meantime.
    """
    from . import services
    from .providers import RateFetchError

    try:
        stats = services.update_exchange_rates()
    except RateFetchError as exc:
        logger.error("update_exchange_rates failed: %s", exc)
        return 0

    if stats["not_found"]:
        logger.info(
            "Currencies not in database: %s", ", ".join(stats["not_found"])
        )
    return len(stats["updated"])


try:
    from celery import shared_task
except ImportError:
    shared_task = None

if shared_task is not None:
    update_exchange_rates = shared_task(name=UPDATE_EXCHANGE_RATES_TASK)(update_exchange_rates)
