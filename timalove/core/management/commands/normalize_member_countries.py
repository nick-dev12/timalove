"""Normalise country / residence_country des profils membres."""

from django.core.management.base import BaseCommand

from core.data.country_normalize import normalize_country_for_storage
from core.models import Profile
from core.models.choices import UserRole


class Command(BaseCommand):
    help = "Normalise les champs pays des profils membres (variantes, villes → pays canonique)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Affiche les changements sans écrire en base.",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        updated = 0
        scanned = 0

        for profile in Profile.objects.filter(role=UserRole.MEMBER).only(
            "id", "country", "residence_country"
        ):
            scanned += 1
            changes: dict[str, str] = {}

            new_country = normalize_country_for_storage(profile.country)
            if new_country and new_country != (profile.country or "").strip():
                changes["country"] = new_country

            new_residence = normalize_country_for_storage(profile.residence_country)
            if new_residence and new_residence != (profile.residence_country or "").strip():
                changes["residence_country"] = new_residence

            if not changes:
                continue

            updated += 1
            if dry_run:
                self.stdout.write(
                    f"{profile.id}: country={profile.country!r} -> {changes.get('country', profile.country)!r}; "
                    f"residence={profile.residence_country!r} -> {changes.get('residence_country', profile.residence_country)!r}"
                )
                continue

            for field, value in changes.items():
                setattr(profile, field, value)
            profile.save(update_fields=[*changes.keys(), "updated_at"])

        mode = "simulation" if dry_run else "appliqué"
        self.stdout.write(self.style.SUCCESS(f"{updated}/{scanned} profils normalisés ({mode})."))
