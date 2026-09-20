"""Compte de test Lot C — approuvé pour QA prod/local."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from core.management.commands.create_apple_review_account import Command as AppleReviewCommand

DEFAULT_EMAIL = "test.lotc@timalove.local"
DEFAULT_PASSWORD = "AppleReview2026!"


class Command(BaseCommand):
    help = "Crée ou met à jour le compte de test Lot C (approuvé, profil complet)."

    def add_arguments(self, parser):
        parser.add_argument("--email", default=DEFAULT_EMAIL)
        parser.add_argument("--password", default=DEFAULT_PASSWORD)
        parser.add_argument("--first-name", default="Test")
        parser.add_argument("--last-name", default="LotC")

    def handle(self, *args, **options):
        inner = AppleReviewCommand()
        inner.stdout = self.stdout
        inner.style = self.style
        inner.handle(
            *args,
            email=options["email"],
            password=options["password"],
            first_name=options["first_name"],
            last_name=options["last_name"],
            photo_url=None,
            reset_partners=False,
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Compte test Lot C pret : {options['email']} / {options['password']}"
            )
        )
