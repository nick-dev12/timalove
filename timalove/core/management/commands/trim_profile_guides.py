"""Plafonne traits (3), valeurs (3) et qualités recherchées (4) sur tous les profils."""

from django.core.management.base import BaseCommand

from core.controllers.profile_controller import trim_all_guide_fields


class Command(BaseCommand):
    help = "Supprime les traits, valeurs et qualités recherchées au-delà des plafonds."

    def add_arguments(self, parser):
        parser.add_argument(
            "--include-staff",
            action="store_true",
            help="Inclut aussi les profils admin / staff.",
        )

    def handle(self, *args, **options):
        updated, scanned = trim_all_guide_fields(members_only=not options.get("include_staff"))
        self.stdout.write(
            self.style.SUCCESS(
                f"{updated}/{scanned} profils ajustes (traits max 3, valeurs max 3, qualites max 4)."
            )
        )
