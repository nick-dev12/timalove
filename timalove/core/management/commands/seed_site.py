from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.controllers import site_settings_controller
from core.models import Profile
from core.models.choices import Gender, RegistrationStatus, UserRole
from datetime import date


class Command(BaseCommand):
    help = "Seed site_settings + admin de démo"

    def add_arguments(self, parser):
        parser.add_argument("--email", default="admin@timalove.local")
        parser.add_argument("--password", default="AdminTimaLove2026!")

    def handle(self, *args, **options):
        created_settings = site_settings_controller.seed_defaults()
        self.stdout.write(f"Settings créés/existants: +{created_settings}")

        User = get_user_model()
        email = options["email"]
        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        if created:
            user.set_password(options["password"])
            user.save()
            Profile.objects.create(
                user=user,
                first_name="Tima",
                last_name="Admin",
                email=email,
                date_of_birth=date(1990, 1, 1),
                gender=Gender.FEMALE,
                city="Dakar",
                country="Sénégal",
                role=UserRole.ADMIN,
                registration_status=RegistrationStatus.APPROVED,
                is_verified=True,
            )
            self.stdout.write(self.style.SUCCESS(f"Admin créé: {email} / {options['password']}"))
        else:
            user.is_staff = True
            user.is_superuser = True
            user.set_password(options["password"])
            user.save()
            profile = getattr(user, "profile", None)
            if profile:
                profile.role = UserRole.ADMIN
                profile.save(update_fields=["role"])
            self.stdout.write(self.style.WARNING(f"Admin mis à jour: {email}"))
