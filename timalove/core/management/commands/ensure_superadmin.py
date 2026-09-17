"""Garantit l'existence du super admin (sans écraser le mot de passe par défaut)."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.controllers import site_settings_controller
from core.management.commands.create_superadmin import Command as CreateSuperadminCommand
from core.models import Profile
from core.models.choices import Gender, RegistrationStatus, UserRole
from datetime import date


class Command(BaseCommand):
    help = (
        "Crée le super admin s'il manque, ou répare rôle / accès Django admin. "
        "N'écrase pas le mot de passe sauf avec --reset-password."
    )

    def add_arguments(self, parser):
        parser.add_argument("--email", default="admin@timalove.local")
        parser.add_argument("--password", default="AdminTimaLove2026!")
        parser.add_argument(
            "--reset-password",
            action="store_true",
            help="Réinitialise le mot de passe (réparation d'urgence).",
        )

    def _create_kwargs(self, options: dict) -> dict:
        return {
            "email": options["email"],
            "password": options["password"],
            "first_name": options.get("first_name", "Super"),
            "last_name": options.get("last_name", "Admin"),
        }

    def handle(self, *args, **options):
        if options.get("reset_password"):
            CreateSuperadminCommand().handle(**self._create_kwargs(options))
            return

        site_settings_controller.seed_defaults()
        email = options["email"].strip().lower()
        User = get_user_model()

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.filter(username__iexact=email).first()

        if user is None:
            CreateSuperadminCommand().handle(**self._create_kwargs(options))
            self.stdout.write(
                self.style.SUCCESS(f"Super admin créé (manquant) : {email}")
            )
            return

        user.email = email
        user.is_active = True
        user.is_staff = True
        user.is_superuser = True
        user.save(update_fields=["email", "is_active", "is_staff", "is_superuser"])

        profile, profile_created = Profile.objects.get_or_create(
            user=user,
            defaults={
                "first_name": "Super",
                "last_name": "Admin",
                "email": email,
                "date_of_birth": date(1990, 1, 1),
                "gender": Gender.FEMALE,
                "city": "Dakar",
                "country": "Sénégal",
                "role": UserRole.SUPER_ADMIN,
                "registration_status": RegistrationStatus.APPROVED,
                "is_verified": True,
                "photo_url": "/static/images/logo.webp",
            },
        )
        if not profile_created:
            profile.role = UserRole.SUPER_ADMIN
            profile.registration_status = RegistrationStatus.APPROVED
            profile.is_verified = True
            profile.banned_at = None
            profile.email = email
            profile.save(
                update_fields=[
                    "role",
                    "registration_status",
                    "is_verified",
                    "banned_at",
                    "email",
                    "updated_at",
                ]
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Super admin vérifié (compte existant, mot de passe inchangé) : {email}"
            )
        )
        self.stdout.write(
            "  Pour réinitialiser le mot de passe : "
            "python manage.py create_superadmin --email "
            f"{email} --password '***'"
        )
