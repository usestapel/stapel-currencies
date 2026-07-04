"""Refresh exchange rates from the configured ``RATE_PROVIDER``.

Same seam as the Celery task ``stapel_currencies.tasks.update_exchange_rates``
— this is the manual / plain-cron entry point.
"""
from django.core.management.base import BaseCommand

from stapel_currencies import services
from stapel_currencies.providers import RateFetchError


class Command(BaseCommand):
    help = (
        "Fetch exchange rates from STAPEL_CURRENCIES['RATE_PROVIDER'] "
        "(ECB by default) and update the currency catalog"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be updated without making changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        try:
            stats = services.update_exchange_rates(dry_run=dry_run)
        except RateFetchError as exc:
            self.stderr.write(self.style.ERROR(f"Failed to fetch exchange rates: {exc}"))
            return

        for code, old_value, new_value in stats["updated"]:
            if dry_run:
                self.stdout.write(f"  Would update {code}: {old_value} -> {new_value}")

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"DRY RUN: Would update {len(stats['updated'])} currencies"
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully updated {len(stats['updated'])} currencies"
                )
            )

        if stats["not_found"]:
            self.stdout.write(
                "Currencies not in database: " + ", ".join(stats["not_found"])
            )
