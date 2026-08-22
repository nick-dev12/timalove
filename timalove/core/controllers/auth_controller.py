"""Auth — inscription, connexion, reset."""

from __future__ import annotations

import uuid
from datetime import date

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from core.controllers import site_settings_controller
from core.models import BannedIdentity, Profile
from core.models.choices import Gender, RegistrationStatus, Religion, UserRole

User = get_user_model()


def normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    return email.strip().lower()


def normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = "".join(c for c in phone if c.isdigit() or c == "+")
    return digits or None


SYNTHETIC_EMAIL_DOMAINS = ("oauth.timalove.local", "phone.timalove.local")


def is_synthetic_email(email: str | None) -> bool:
    email_n = normalize_email(email) or ""
    return any(email_n.endswith("@" + domain) for domain in SYNTHETIC_EMAIL_DOMAINS)


def unique_username(base: str) -> str:
    candidate = (base or f"membre_{uuid.uuid4().hex[:10]}")[:150]
    if not User.objects.filter(username=candidate).exists():
        return candidate
    for index in range(2, 80):
        suffix = str(index)
        name = f"{candidate[: 150 - len(suffix)]}{suffix}"
        if not User.objects.filter(username=name).exists():
            return name
    return f"membre_{uuid.uuid4().hex[:12]}"


def is_banned(email: str | None = None, phone: str | None = None) -> bool:
    q = BannedIdentity.objects.all()
    email_n = normalize_email(email)
    phone_n = normalize_phone(phone)
    if email_n and q.filter(email_normalized=email_n).exists():
        return True
    if phone_n and q.filter(phone_normalized=phone_n).exists():
        return True
    return False


def login_user(request, identifier: str, password: str, mode: str = "email") -> tuple[bool, str]:
    mode = (mode or "email").strip().lower()
    if mode == "phone":
        return _login_with_phone(request, identifier, password)
    return _login_with_email(request, identifier, password)


def _finish_login(request, user) -> tuple[bool, str]:
    profile = getattr(user, "profile", None)
    if profile and profile.banned_at:
        return False, "Ce compte a été banni."
    login(request, user)
    if profile:
        from django.utils import timezone

        profile.is_online = True
        profile.last_active_at = timezone.now()
        profile.save(update_fields=["is_online", "last_active_at"])
    return True, "Connexion réussie."


def _login_with_email(request, email: str, password: str) -> tuple[bool, str]:
    email_n = normalize_email(email) or ""
    if is_banned(email=email_n):
        return False, "Ce compte a été banni."
    user = authenticate(request, username=email_n, password=password)
    if user is None:
        try:
            u = User.objects.get(email__iexact=email_n)
            user = authenticate(request, username=u.username, password=password)
        except User.DoesNotExist:
            user = None
    if user is None:
        return False, "Identifiants incorrects."
    return _finish_login(request, user)


def find_profile_by_phone(phone: str) -> Profile | None:
    raw = normalize_phone(phone)
    if not raw:
        return None
    digits = "".join(c for c in raw if c.isdigit())
    qs = Profile.objects.select_related("user").exclude(phone__isnull=True).exclude(phone="")
    profile = qs.filter(phone=raw).first()
    if profile:
        return profile
    if len(digits) >= 8:
        profile = qs.filter(phone__endswith=digits[-9:]).first()
        if profile:
            return profile
        return qs.filter(phone__endswith=digits[-8:]).first()
    return None


def _login_with_phone(request, phone: str, password: str) -> tuple[bool, str]:
    phone_n = normalize_phone(phone)
    if not phone_n:
        return False, "Indiquez un numéro de téléphone valide."
    if is_banned(phone=phone_n):
        return False, "Ce compte a été banni."
    profile = find_profile_by_phone(phone_n)
    if profile is None:
        return False, "Identifiants incorrects."
    user = authenticate(request, username=profile.user.username, password=password)
    if user is None:
        return False, "Identifiants incorrects."
    return _finish_login(request, user)


def is_profile_complete(profile: Profile | None) -> bool:
    if profile is None:
        return False
    return profile.is_profile_complete


def _split_display_name(full_name: str, email: str) -> tuple[str, str]:
    parts = [p for p in (full_name or "").strip().split() if p]
    if not parts:
        local = email.split("@")[0]
        return local[:1].upper() + local[1:], ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def verify_firebase_id_token(id_token: str, expected_provider: str) -> dict | None:
    from firebase_admin import auth as firebase_auth

    from core.controllers.firebase_app import get_firebase_app

    token = (id_token or "").strip()
    if not token:
        return None

    app = get_firebase_app()
    if app is None:
        return None

    decoded = firebase_auth.verify_id_token(token, app=app)
    provider = (decoded.get("firebase") or {}).get("sign_in_provider")
    if provider != expected_provider:
        return None
    return decoded


def verify_google_id_token(id_token: str) -> dict | None:
    return verify_firebase_id_token(id_token, "google.com")


@transaction.atomic
def login_or_register_oauth(
    request,
    id_token: str,
    provider: str,
    *,
    hints: dict | None = None,
) -> tuple[bool, str, bool]:
    """Connecte ou crée un membre via un ID token Firebase (Google ou Apple)."""
    labels = {"google.com": "Google", "apple.com": "Apple"}
    label = labels.get(provider, "ce compte")
    uid_field = "google_uid" if provider == "google.com" else "apple_uid"
    hints = hints or {}

    try:
        decoded = verify_firebase_id_token(id_token, provider)
    except Exception as exc:
        print(f"[auth] {provider} token:", exc)
        return False, f"Connexion {label} impossible. Réessayez.", False

    if not decoded:
        return False, f"Jeton {label} invalide.", False

    uid = str(decoded.get("uid") or "")
    email = normalize_email(decoded.get("email") or hints.get("email"))
    if not email:
        email = f"{provider.split('.')[0]}.{uid[:16]}@oauth.timalove.local"
    if is_banned(email=email):
        return False, "Ce compte a été banni.", False

    given = (decoded.get("given_name") or hints.get("given_name") or "").strip()
    family = (decoded.get("family_name") or hints.get("family_name") or "").strip()
    if not given and not family:
        given, family = _split_display_name(
            decoded.get("name") or hints.get("display_name") or "",
            email,
        )
    picture = (decoded.get("picture") or "").strip() or None

    profile = None
    if uid:
        profile = Profile.objects.select_related("user").filter(**{uid_field: uid}).first()
    if profile is None:
        profile = Profile.objects.select_related("user").filter(email__iexact=email).first()

    created = False
    if profile is None:
        if not site_settings_controller.get("registrations_enabled", True):
            return False, "Les inscriptions sont temporairement fermées.", False
        if User.objects.filter(email__iexact=email).exists():
            user = User.objects.get(email__iexact=email)
        else:
            username = email if "@oauth.timalove.local" not in email else f"{provider.split('.')[0]}_{uid[:20]}"
            user = User(username=username[:150], email=email, first_name=given, last_name=family)
            user.set_unusable_password()
            user.save()
        profile = Profile.objects.create(
            user=user,
            first_name=given or "Membre",
            last_name=family,
            email=email,
            google_uid=uid if provider == "google.com" else None,
            apple_uid=uid if provider == "apple.com" else None,
            photo_url=picture,
            date_of_birth=None,
            gender="",
            city="",
            country="Sénégal",
            registration_status=RegistrationStatus.PENDING,
            role=UserRole.MEMBER,
            onboarding_completed=False,
            onboarding_step=1,
        )
        created = True
    else:
        user = profile.user
        updates: list[str] = []
        if uid and getattr(profile, uid_field) != uid:
            setattr(profile, uid_field, uid)
            updates.append(uid_field)
        if picture and not profile.photo_url:
            profile.photo_url = picture
            updates.append("photo_url")
        if updates:
            profile.save(update_fields=updates)

    if profile.banned_at:
        return False, "Ce compte a été banni.", False

    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    from django.utils import timezone

    profile.is_online = True
    profile.last_active_at = timezone.now()
    profile.save(update_fields=["is_online", "last_active_at"])

    needs_completion = not profile.is_profile_complete
    if created:
        return True, "Compte créé. Complétez votre profil pour continuer.", needs_completion
    return True, "Connexion réussie.", needs_completion


def login_or_register_google(request, id_token: str) -> tuple[bool, str, bool]:
    return login_or_register_oauth(request, id_token, "google.com")


def login_or_register_apple(
    request,
    id_token: str,
    *,
    hints: dict | None = None,
) -> tuple[bool, str, bool]:
    return login_or_register_oauth(request, id_token, "apple.com", hints=hints)


def complete_member_profile(profile: Profile, data: dict) -> tuple[bool, str]:
    dob = data.get("date_of_birth")
    if isinstance(dob, str) and dob:
        dob = date.fromisoformat(dob)
    if not dob:
        return False, "La date de naissance est requise."
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 18:
        return False, "Vous devez avoir au moins 18 ans."

    gender = data.get("gender") or ""
    if gender not in {Gender.MALE, Gender.FEMALE}:
        return False, "Veuillez indiquer votre genre."
    city = (data.get("city") or "").strip()
    if not city:
        return False, "La ville est requise."

    profile.date_of_birth = dob
    profile.gender = gender
    profile.city = city
    profile.country = data.get("country") or profile.country or "Sénégal"
    if data.get("first_name"):
        profile.first_name = data["first_name"].strip()
    if data.get("last_name"):
        profile.last_name = data["last_name"].strip()
    profile.registration_status = RegistrationStatus.APPROVED
    profile.save()
    return True, "Profil complété. Bienvenue sur TimaLove."


def logout_user(request) -> None:
    user = request.user
    if user.is_authenticated:
        profile = getattr(user, "profile", None)
        if profile:
            profile.is_online = False
            profile.save(update_fields=["is_online"])
    logout(request)


@transaction.atomic
def register_member(data: dict) -> tuple[bool, str, Profile | None]:
    if not site_settings_controller.get("registrations_enabled", True):
        return False, "Les inscriptions sont temporairement fermées.", None

    email = normalize_email(data.get("email"))
    phone = normalize_phone(data.get("phone"))
    password = data.get("password") or ""
    if not password:
        return False, "Mot de passe requis.", None
    if len(password) < 8:
        return False, "Le mot de passe doit contenir au moins 8 caractères.", None
    if not email and not phone:
        return False, "Email ou numéro requis.", None
    if email and is_synthetic_email(email):
        email = None
    if is_banned(email=email, phone=phone):
        return False, "Inscription impossible.", None
    if email and User.objects.filter(email__iexact=email).exists():
        return False, "Un compte existe déjà avec cet email.", None
    if email and Profile.objects.filter(email__iexact=email).exists():
        return False, "Un compte existe déjà avec cet email.", None
    if phone and find_profile_by_phone(phone):
        return False, "Un compte existe déjà avec ce numéro.", None

    dob = data.get("date_of_birth")
    if isinstance(dob, str) and dob:
        dob = date.fromisoformat(dob)
    if not dob:
        return False, "Indiquez un âge valide.", None
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    if age < 18:
        return False, "Vous devez avoir au moins 18 ans.", None

    if email:
        username = unique_username(email)
        user_email = email
    else:
        digits = "".join(c for c in (phone or "") if c.isdigit())
        username = unique_username(f"tel_{digits[-12:]}" if digits else f"membre_{uuid.uuid4().hex[:10]}")
        user_email = ""

    user = User.objects.create_user(username=username, email=user_email, password=password)
    user.first_name = (data.get("first_name") or "").strip()
    user.last_name = (data.get("last_name") or "").strip()
    user.save()

    profile = Profile.objects.create(
        user=user,
        first_name=user.first_name or "Membre",
        last_name=user.last_name,
        email=email,
        phone=phone,
        date_of_birth=dob,
        gender=data.get("gender", Gender.FEMALE),
        city=data.get("city", ""),
        country=data.get("country") or data.get("origin") or "Sénégal",
        residence_country=data.get("residence_country"),
        religion=data.get("religion") or None,
        profession=data.get("profession"),
        bio=data.get("bio"),
        looking_for=data.get("looking_for"),
        photo_url=data.get("photo_url"),
        registration_status=RegistrationStatus.APPROVED,
        role=UserRole.MEMBER,
        onboarding_completed=True,
        onboarding_step=4,
    )
    return True, "Compte créé avec succès.", profile


def request_password_reset(email: str) -> tuple[bool, str, str | None]:
    email_n = normalize_email(email)
    if not email_n:
        return False, "Email requis.", None
    try:
        user = User.objects.get(email__iexact=email_n)
    except User.DoesNotExist:
        return True, "Si un compte existe, un email a été envoyé.", None
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    return True, "Si un compte existe, un email a été envoyé.", f"{uid}/{token}"


def verify_user_password(user, password: str) -> bool:
    if not password:
        return False
    if authenticate(username=user.username, password=password):
        return True
    email_n = normalize_email(user.email)
    if email_n and user.username != email_n and authenticate(username=email_n, password=password):
        return True
    return False


def change_password(profile: Profile, current_password: str, new_password: str, confirm_password: str) -> tuple[bool, str]:
    if profile.google_uid:
        return False, "Compte Google — le mot de passe est géré par Google."
    user = profile.user
    if not user.has_usable_password():
        return False, "Aucun mot de passe local configuré sur ce compte."
    if not verify_user_password(user, current_password):
        return False, "Mot de passe actuel incorrect."
    if len(new_password or "") < 8:
        return False, "Le nouveau mot de passe doit contenir au moins 8 caractères."
    if new_password != confirm_password:
        return False, "Les mots de passe ne correspondent pas."
    user.set_password(new_password)
    user.save(update_fields=["password"])
    return True, "Mot de passe mis à jour."


def change_email(profile: Profile, new_email: str, current_password: str) -> tuple[bool, str]:
    if profile.google_uid:
        return False, "Compte Google — l’email ne peut pas être modifié ici."
    if profile.apple_uid:
        return False, "Compte Apple — l’email ne peut pas être modifié ici."
    email_n = normalize_email(new_email)
    if not email_n:
        return False, "Email invalide."
    if is_synthetic_email(email_n):
        return False, "Veuillez saisir une adresse email valide."
    user = profile.user
    current = normalize_email(profile.email or user.email)
    if email_n == current:
        return False, "Cet email est déjà le vôtre."
    if not verify_user_password(user, current_password):
        return False, "Mot de passe incorrect."
    if User.objects.filter(email__iexact=email_n).exclude(pk=user.pk).exists():
        return False, "Cet email est déjà utilisé."
    if Profile.objects.filter(email__iexact=email_n).exclude(pk=profile.pk).exists():
        return False, "Cet email est déjà utilisé."
    old_email = normalize_email(user.email)
    if old_email and (user.username == old_email or normalize_email(user.username) == old_email):
        if User.objects.filter(username=email_n).exclude(pk=user.pk).exists():
            return False, "Cet email est déjà utilisé."
        user.username = email_n
    user.email = email_n
    user.save(update_fields=["email", "username"])
    profile.email = email_n
    profile.save(update_fields=["email", "updated_at"])
    return True, "Email mis à jour."
