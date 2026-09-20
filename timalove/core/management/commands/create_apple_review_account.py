"""Compte démo App Store — profil approuvé, matchs et conversations."""

from __future__ import annotations

from datetime import date

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from core.controllers import message_controller, site_settings_controller, swipe_controller
from core.data.onboarding import encode_looking_for
from core.models import Profile
from core.models.choices import Gender, RegistrationStatus, RelationshipIntent, Religion, UserRole

DEFAULT_EMAIL = "apple.review@timalove.local"
DEFAULT_PASSWORD = "AppleReview2026!"
DEFAULT_PHOTO = "https://mytimalove.com/static/images/logo.webp"

PARTNERS = (
    {
        "email": "awa.demo@timalove.local",
        "first_name": "Awa",
        "last_name": "Demo",
        "city": "Dakar",
    },
    {
        "email": "fatou.demo@timalove.local",
        "first_name": "Fatou",
        "last_name": "Demo",
        "city": "Thiès",
    },
)


class Command(BaseCommand):
    help = "Crée ou met à jour le compte démo Apple Review (approuvé, matchs, messages guidés)."

    def add_arguments(self, parser):
        parser.add_argument("--email", default=DEFAULT_EMAIL)
        parser.add_argument("--password", default=DEFAULT_PASSWORD)
        parser.add_argument("--first-name", default="Amadou")
        parser.add_argument("--last-name", default="Review")
        parser.add_argument("--photo-url", default=DEFAULT_PHOTO)
        parser.add_argument(
            "--reset-partners",
            action="store_true",
            help="Recrée les profils partenaires démo et leurs matchs.",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        site_settings_controller.seed_defaults()

        email = options["email"].strip().lower()
        password = options["password"]
        photo_url = (options["photo_url"] or DEFAULT_PHOTO).strip()
        User = get_user_model()

        reviewer = self._upsert_member(
            User,
            email=email,
            password=password,
            first_name=options["first_name"],
            last_name=options["last_name"],
            gender=Gender.MALE,
            photo_url=photo_url,
            city="Dakar",
            bio=(
                "Compte démo App Store. Je cherche une union sérieuse orientée mariage, "
                "avec des valeurs familiales fortes."
            ),
            life_project="Construire un foyer stable et sincère d'ici 18 à 24 mois.",
        )

        partners: list[Profile] = []
        if options["reset_partners"]:
            for spec in PARTNERS:
                partners.append(
                    self._upsert_member(
                        User,
                        email=spec["email"],
                        password=password,
                        first_name=spec["first_name"],
                        last_name=spec["last_name"],
                        gender=Gender.FEMALE,
                        photo_url=photo_url,
                        city=spec["city"],
                        bio=f"Profil démo pour la review App Store — {spec['first_name']}.",
                        life_project="Mariage dans un cadre respectueux et familial.",
                    )
                )
        else:
            for spec in PARTNERS:
                profile = Profile.objects.filter(email=spec["email"]).select_related("user").first()
                if profile is None:
                    partners.append(
                        self._upsert_member(
                            User,
                            email=spec["email"],
                            password=password,
                            first_name=spec["first_name"],
                            last_name=spec["last_name"],
                            gender=Gender.FEMALE,
                            photo_url=photo_url,
                            city=spec["city"],
                            bio=f"Profil démo pour la review App Store — {spec['first_name']}.",
                            life_project="Mariage dans un cadre respectueux et familial.",
                        )
                    )
                else:
                    partners.append(profile)

        awa = partners[0]
        fatou = partners[1]

        self._ensure_match(reviewer, awa)
        self._ensure_match(reviewer, fatou)

        match_awa = message_controller.get_active_match(reviewer, awa.id)
        if match_awa:
            match_awa.messages.all().delete()
            match_awa.guided_intro_completed = False
            match_awa.save(update_fields=["guided_intro_completed", "updated_at"])
            prompt = message_controller.GUIDED_INTRO_PROMPTS[0]
            ok, msg, _ = message_controller.send_text(reviewer, awa.id, prompt)
            if not ok:
                self.stdout.write(self.style.WARNING(f"Message guidé Awa : {msg}"))
            message_controller.send_text(
                awa,
                reviewer.id,
                "Bonjour Amadou, merci pour votre message. Mon projet de vie est aussi orienté mariage.",
            )

        match_fatou = message_controller.get_active_match(reviewer, fatou.id)
        if match_fatou:
            match_fatou.messages.all().delete()
            match_fatou.guided_intro_completed = False
            match_fatou.save(update_fields=["guided_intro_completed", "updated_at"])

        self.stdout.write(self.style.SUCCESS("Compte démo Apple Review prêt."))
        self.stdout.write("")
        self.stdout.write("Identifiants App Store Connect -> App Review Information :")
        self.stdout.write(f"  Email        : {email}")
        self.stdout.write(f"  Mot de passe : {password}")
        self.stdout.write("")
        self.stdout.write("Parcours review (3 min) :")
        self.stdout.write("  1. Onboarding natif + charte (1er lancement)")
        self.stdout.write("  2. Connexion -> Parcours (liste curated, pas swipe)")
        self.stdout.write(f"  3. Messages -> {awa.first_name} (conversation active)")
        self.stdout.write(f"  4. Messages -> {fatou.first_name} (questions guidees obligatoires)")
        self.stdout.write("  5. Onglet Moi (intention mariage + religions)")
        self.stdout.write("  6. Onglet Interets (Recus / Envoyes)")
        self.stdout.write("")
        self.stdout.write("Production : ajoutez l'email à QUOTA_EXEMPT_EMAILS dans .env")
        self.stdout.write(f"  QUOTA_EXEMPT_EMAILS={email},gooteste@gmail.com")

    def _upsert_member(
        self,
        User,
        *,
        email: str,
        password: str,
        first_name: str,
        last_name: str,
        gender: str,
        photo_url: str,
        city: str,
        bio: str,
        life_project: str,
    ) -> Profile:
        user, _created = User.objects.get_or_create(
            username=email,
            defaults={"email": email, "first_name": first_name, "last_name": last_name},
        )
        user.email = email
        user.first_name = first_name
        user.last_name = last_name
        user.set_password(password)
        user.save()

        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
            },
        )
        profile.first_name = first_name
        profile.last_name = last_name
        profile.email = email
        profile.date_of_birth = date(1993, 6, 15)
        profile.gender = gender
        profile.city = city
        profile.country = "Sénégal"
        profile.residence_country = "Sénégal"
        profile.religion = Religion.MUSULMANE
        profile.relationship_intent = RelationshipIntent.MARIAGE
        profile.life_values = ["famille", "foi", "sincerite", "respect"]
        profile.looking_for = encode_looking_for(["serieux", "familial", "projet_famille"])
        profile.bio = bio
        profile.life_project = life_project
        profile.photo_url = photo_url
        profile.registration_status = RegistrationStatus.APPROVED
        profile.role = UserRole.MEMBER
        profile.onboarding_completed = True
        profile.onboarding_step = 4
        profile.is_verified = True
        profile.rejection_reason = ""
        profile.save()
        return profile

    def _ensure_match(self, a: Profile, b: Profile) -> None:
        swipe_controller.record_swipe(a, b.id, "like")
        swipe_controller.record_swipe(b, a.id, "like")
