"""Seed the currency catalog from ``STAPEL_CURRENCIES["DEFAULT_CURRENCIES"]``.

Idempotent: without ``--force`` it only runs against an empty table;
``--force`` upserts (update_or_create) the seed list over existing rows.
"""
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand, CommandError

from stapel_currencies.conf import currencies_settings
from stapel_currencies.models import Currency


class Command(BaseCommand):
    help = (
        "Load the default currency catalog from "
        "STAPEL_CURRENCIES['DEFAULT_CURRENCIES'] if the table is empty"
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Load even if the table is not empty (updates existing rows)",
        )

    def handle(self, *args, **options):
        force = options["force"]

        if not force and Currency.objects.exists():
            self.stdout.write(
                self.style.WARNING(
                    "Currencies table is not empty. Use --force to update."
                )
            )
            return

        created_count = 0
        updated_count = 0

        for currency_data in currencies_settings.DEFAULT_CURRENCIES:
            try:
                code = currency_data["code"]
                value = Decimal(str(currency_data["value"]))
            except (KeyError, InvalidOperation) as exc:
                raise CommandError(
                    f"invalid DEFAULT_CURRENCIES entry {currency_data!r}: {exc}"
                ) from exc
            _, created = Currency.objects.update_or_create(
                code=code,
                defaults={
                    "display_name": currency_data.get("display_name", ""),
                    "symbol": currency_data.get("symbol", ""),
                    "value": value,
                    "is_active": True,
                },
            )
            if created:
                created_count += 1
            else:
                updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully loaded currencies: {created_count} created, "
                f"{updated_count} updated"
            )
        )
