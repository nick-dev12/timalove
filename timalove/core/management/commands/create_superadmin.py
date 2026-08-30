from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from core.controllers import site_settings_controller
from core.models import Profile
from core.models.choices import Gender, RegistrationStatus, UserRole
from datetime import date


class Command(BaseCommand):
    help = "Crée ou réinitialise le super administrateur TimaLove (espace privé + Django admin)"

    def add_arguments(self, parser):
        parser.add_argument("--email", default="admin@timalove.local")
        parser.add_argument("--password", default="AdminTimaLove2026!")
        parser.add_argument("--first-name", default="Super")
        parser.add_argument("--last-name", default="Admin")

    def handle(self, *args, **options):
        site_settings_controller.seed_defaults()

        email = options["email"].strip().lower()
        password = options["password"]
        User = get_user_model()

        user, created = User.objects.get_or_create(
            username=email,
            defaults={"email": email, "is_staff": True, "is_superuser": True},
        )
        user.email = email
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        profile, profile_created = Profile.objects.get_or_create(
            user=user,
            defaults={
                "first_name": options["first_name"],
                "last_name": options["last_name"],
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
            profile.email = email
            if not (profile.photo_url or "").strip():
                profile.photo_url = "/static/images/logo.webp"
            profile.save(
                update_fields=[
                    "role",
                    "registration_status",
                    "is_verified",
                    "email",
                    "photo_url",
                    "updated_at",
                ]
            )

        action = "créé" if created or profile_created else "mis à jour"
        self.stdout.write(self.style.SUCCESS(f"Super admin {action} avec succès."))
        self.stdout.write("")
        self.stdout.write("Accès espace privé TimaLove :")
        self.stdout.write("  URL      : /espace-prive/connexion/")
        self.stdout.write(f"  Email    : {email}")
        self.stdout.write(f"  Mot de passe : {password}")
        self.stdout.write("")
        self.stdout.write("Django admin (ORM brut) :")
        self.stdout.write("  URL      : /admin/")
        self.stdout.write(f"  Email    : {email}")
        self.stdout.write(f"  Mot de passe : {password}")
