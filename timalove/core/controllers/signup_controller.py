"""Inscription interactive — validation des étapes et création du compte."""

from __future__ import annotations

import json
import re
import urllib.error
import urllib.parse
import urllib.request
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction

from core.controllers import auth_controller, onboarding_controller
from core.controllers.auth_controller import (
    find_profile_by_phone,
    is_banned,
    is_synthetic_email,
    normalize_email,
    normalize_phone,
)
from core.data.countries import COUNTRIES_FR
from core.data.onboarding import encode_looking_for, looking_for_ids
from core.models import Profile
from core.models.choices import Gender, RegistrationStatus, RelationshipIntent, Religion

User = get_user_model()

EMAIL_STEPS = [
    "email",
    "password",
    "identity",
    "socio",
    "interests",
    "bios",
    "projet",
    "photos",
    "geo",
    "notif",
]
PHONE_STEPS = [
    "phone",
    "password",
    "identity",
    "socio",
    "interests",
    "bios",
    "projet",
    "photos",
    "geo",
    "notif",
]
OAUTH_STEPS = [
    "identity",
    "socio",
    "interests",
    "bios",
    "projet",
    "photos",
    "geo",
    "notif",
]

_INTENT_VALUES = {choice.value for choice in RelationshipIntent}
_RELIGION_VALUES = {Religion.MUSULMANE, Religion.CHRETIENNE, Religion.AUTRE}


def steps_for(channel: str) -> list[str]:
    if channel == "phone":
        return list(PHONE_STEPS)
    if channel == "oauth":
        return list(OAUTH_STEPS)
    return list(EMAIL_STEPS)


def profile_prefill(profile: Profile | None) -> dict:
    if profile is None:
        return {}
    email = profile.email or ""
    return {
        "channel": "oauth",
        "first_name": profile.first_name or "",
        "last_name": profile.last_name or "",
        "email": "" if is_synthetic_email(email) else email,
        "phone": profile.phone or "",
        "photo_url": profile.photo_url or "",
        "photo_url_2": profile.photo_url_2 or "",
        "age": profile.age,
        "gender": profile.gender or "",
        "religion": profile.religion or "",
        "country": profile.country or "",
        "bio": profile.bio or "",
        "looking_for": looking_for_ids(profile.looking_for),
        "interests": list(profile.interests or []),
        "personality_traits": list(profile.personality_traits or []),
        "life_values": list(profile.life_values or []),
        "relationship_intent": profile.relationship_intent or "",
        "life_project": profile.life_project or "",
        "city": profile.city or "",
        "commune": profile.commune or "",
        "residence_country": profile.residence_country or "",
        "latitude": str(profile.latitude) if profile.latitude is not None else "",
        "longitude": str(profile.longitude) if profile.longitude is not None else "",
    }


def check_identifier(data: dict, *, exclude_profile: Profile | None = None) -> dict[str, str]:
    errors: dict[str, str] = {}
    email = normalize_email(data.get("email"))
    phone = normalize_phone(data.get("phone"))
    if email and not is_synthetic_email(email):
        try:
            validate_email(email)
        except ValidationError:
            errors["email"] = "Indiquez un email valide."
        else:
            if is_banned(email=email):
                errors["email"] = "Inscription impossible avec cet email."
            elif _email_taken(email, exclude_profile):
                errors["email"] = "Un compte existe déjà avec cet email."
    if phone:
        if is_banned(phone=phone):
            errors["phone"] = "Inscription impossible avec ce numéro."
        elif _phone_taken(phone, exclude_profile):
            errors["phone"] = "Un compte existe déjà avec ce numéro."
    return errors


def validate_step(step: str, data: dict, *, channel: str = "email", profile: Profile | None = None) -> dict[str, str]:
    step = (step or "").strip()
    channel = (channel or "email").strip() or "email"
    if step == "email":
        return _validate_email(data, profile)
    if step == "phone":
        return _validate_phone(data, profile)
    if step == "password":
        return _validate_password(data, channel)
    if step == "identity":
        return _validate_identity(data, channel, profile)
    if step == "socio":
        return _validate_socio(data)
    if step in {"interests", "bios", "projet"}:
        return {}
    if step == "photos":
        return _validate_photos(data, profile)
    if step in {"geo", "notif"}:
        return {}
    return {"_form": "Étape inconnue."}


def first_invalid_step(data: dict, *, channel: str, profile: Profile | None = None) -> tuple[str | None, dict[str, str]]:
    for step in steps_for(channel):
        errors = validate_step(step, data, channel=channel, profile=profile)
        if errors:
            return step, errors
    return None, {}


@transaction.atomic
def register_from_draft(data: dict) -> tuple[bool, str, Profile | None, dict[str, str], str | None]:
    channel = (data.get("channel") or "email").strip() or "email"
    if channel == "oauth":
        return False, "Ce compte doit être complété une fois connecté.", None, {"_form": "Session requise."}, "identity"

    step, errors = first_invalid_step(data, channel=channel)
    if errors:
        return False, next(iter(errors.values())), None, errors, step

    payload = _member_payload(data)
    ok, msg, profile = auth_controller.register_member(payload)
    if not ok or profile is None:
        field = "email" if "email" in (msg or "").lower() else "phone" if "numéro" in (msg or "").lower() else "_form"
        return False, msg, None, {field: msg}, field if field != "_form" else "email"

    _apply_profile_extras(profile, data)
    try:
        _save_draft_photos(profile, data)
    except ValueError as exc:
        return False, str(exc), None, {"photos": str(exc)}, "photos"
    onboarding_controller.save_location(profile, data, persist=True)
    profile.onboarding_completed = True
    profile.onboarding_step = 4
    profile.registration_status = RegistrationStatus.APPROVED
    profile.save()
    return True, "Compte créé. Bienvenue sur TimaLove.", profile, {}, None


@transaction.atomic
def complete_oauth_profile(profile: Profile, data: dict) -> tuple[bool, str, dict[str, str], str | None]:
    data = dict(data)
    data["channel"] = "oauth"
    step, errors = first_invalid_step(data, channel="oauth", profile=profile)
    if errors:
        return False, next(iter(errors.values())), errors, step

    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    profile.first_name = first_name
    profile.last_name = last_name
    profile.date_of_birth = onboarding_controller.dob_from_age(int(data.get("age")))
    phone = normalize_phone(data.get("phone"))
    if phone:
        profile.phone = phone
    email = normalize_email(data.get("email"))
    if email and not is_synthetic_email(email):
        if _email_taken(email, profile):
            return False, "Un compte existe déjà avec cet email.", {"email": "Un compte existe déjà avec cet email."}, "identity"
        profile.email = email
        if not profile.user.email:
            profile.user.email = email
            profile.user.save(update_fields=["email"])

    _apply_profile_extras(profile, data)
    try:
        _save_draft_photos(profile, data)
    except ValueError as exc:
        return False, str(exc), {"photos": str(exc)}, "photos"
    onboarding_controller.save_location(profile, data, persist=True)
    profile.onboarding_completed = True
    profile.onboarding_step = 4
    profile.registration_status = RegistrationStatus.APPROVED
    profile.save()
    profile.user.first_name = first_name
    profile.user.last_name = last_name
    profile.user.save(update_fields=["first_name", "last_name"])
    return True, "Profil complété. Bienvenue sur TimaLove.", {}, None


def reverse_geocode(latitude, longitude) -> dict:
    lat = onboarding_controller._parse_coord(latitude, Decimal("-90"), Decimal("90"))
    lng = onboarding_controller._parse_coord(longitude, Decimal("-180"), Decimal("180"))
    if lat is None or lng is None:
        return {"ok": False, "message": "Coordonnées invalides."}

    result = {
        "ok": True,
        "latitude": str(lat),
        "longitude": str(lng),
        "city": "",
        "country": "",
        "commune": "",
        "display": "",
    }
    url = "https://nominatim.openstreetmap.org/reverse?" + urllib.parse.urlencode(
        {
            "lat": str(lat),
            "lon": str(lng),
            "format": "json",
            "addressdetails": 1,
            "accept-language": "fr",
        }
    )
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "TimaLove/1.0 (https://timalove.local)"},
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            payload = json.loads(response.read().decode("utf-8") or "{}")
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, UnicodeDecodeError):
        return result

    address = payload.get("address") or {}
    city = (
        address.get("city")
        or address.get("town")
        or address.get("village")
        or address.get("municipality")
        or address.get("county")
        or ""
    )
    commune = (
        address.get("suburb")
        or address.get("city_district")
        or address.get("neighbourhood")
        or address.get("quarter")
        or address.get("municipality")
        or address.get("village")
        or ""
    )
    country = address.get("country") or ""
    result["city"] = str(city).strip()[:120]
    result["commune"] = str(commune).strip()[:180]
    result["country"] = str(country).strip()[:120]
    bits = [part for part in (result["commune"], result["city"], result["country"]) if part]
    unique: list[str] = []
    for bit in bits:
        if bit not in unique:
            unique.append(bit)
    result["display"] = " · ".join(unique)
    return result


def save_signup_location(data: dict, *, profile: Profile | None = None) -> dict:
    geo = reverse_geocode(data.get("latitude"), data.get("longitude"))
    if not geo.get("ok"):
        return geo
    if profile is not None:
        payload = {
            "latitude": geo["latitude"],
            "longitude": geo["longitude"],
            "city": geo.get("city") or data.get("city"),
            "country": geo.get("country") or data.get("country"),
            "commune": geo.get("commune") or data.get("commune"),
        }
        ok, msg = onboarding_controller.save_location(profile, payload, persist=True)
        geo["message"] = msg
        if not ok:
            geo["ok"] = False
    return geo


def _validate_email(data: dict, profile: Profile | None) -> dict[str, str]:
    email = normalize_email(data.get("email"))
    if not email:
        return {"email": "Indiquez votre email."}
    try:
        validate_email(email)
    except ValidationError:
        return {"email": "Indiquez un email valide."}
    if is_synthetic_email(email):
        return {"email": "Indiquez un email personnel."}
    taken = check_identifier({"email": email}, exclude_profile=profile)
    if taken:
        return taken
    return {}


def _validate_phone(data: dict, profile: Profile | None) -> dict[str, str]:
    phone = normalize_phone(data.get("phone"))
    if not phone or len(re.sub(r"\D", "", phone)) < 8:
        return {"phone": "Indiquez un numéro de téléphone valide."}
    taken = check_identifier({"phone": phone}, exclude_profile=profile)
    if taken:
        return taken
    return {}


def _validate_password(data: dict, channel: str) -> dict[str, str]:
    if channel == "oauth":
        return {}
    password = data.get("password") or ""
    if len(password) < 8:
        return {"password": "Le mot de passe doit contenir au moins 8 caractères."}
    return {}


def _validate_identity(data: dict, channel: str, profile: Profile | None) -> dict[str, str]:
    errors: dict[str, str] = {}
    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    if not first_name:
        errors["first_name"] = "Le prénom est obligatoire."
    if not last_name:
        errors["last_name"] = "Le nom est obligatoire."
    try:
        age = int(data.get("age") or 0)
    except (TypeError, ValueError):
        age = 0
    if age < 18:
        errors["age"] = "Vous devez avoir au moins 18 ans."
    elif age > 99:
        errors["age"] = "Vérifiez l’âge saisi."

    phone = normalize_phone(data.get("phone")) or (normalize_phone(profile.phone) if profile else None)
    if channel != "phone" and (not phone or len(re.sub(r"\D", "", phone)) < 8):
        errors["phone"] = "Indiquez un numéro de téléphone valide."
    elif phone:
        taken = check_identifier({"phone": phone}, exclude_profile=profile)
        errors.update(taken)

    email = normalize_email(data.get("email"))
    if email and not is_synthetic_email(email):
        try:
            validate_email(email)
        except ValidationError:
            errors["email"] = "Indiquez un email valide."
        else:
            errors.update(check_identifier({"email": email}, exclude_profile=profile))
    return errors


def _validate_socio(data: dict) -> dict[str, str]:
    errors: dict[str, str] = {}
    if (data.get("gender") or "") not in {Gender.MALE, Gender.FEMALE}:
        errors["gender"] = "Choisissez Homme ou Femme."
    if (data.get("religion") or "") not in _RELIGION_VALUES:
        errors["religion"] = "Sélectionnez votre religion."
    country = (data.get("country") or "").strip()
    if country not in COUNTRIES_FR:
        errors["country"] = "Sélectionnez votre pays d’origine dans la liste."
    return errors


def _validate_interests(data: dict) -> dict[str, str]:
    errors: dict[str, str] = {}
    interests = onboarding_controller._as_str_list(data.get("interests"))
    traits = onboarding_controller._as_str_list(data.get("personality_traits") or data.get("traits"))
    if len(interests) < MIN_INTERESTS:
        errors["interests"] = "Choisissez au moins un centre d’intérêt."
    if len(traits) < MIN_TRAITS:
        errors["personality_traits"] = "Choisissez au moins un trait de caractère."
    return errors


def _validate_projet(data: dict) -> dict[str, str]:
    intent = (data.get("relationship_intent") or "").strip()
    if intent not in _INTENT_VALUES:
        return {"relationship_intent": "Indiquez votre intention."}
    return {}


def _validate_photos(data: dict, profile: Profile | None) -> dict[str, str]:
    photo = (
        (data.get("photo_data_url") or data.get("photo_url") or "")
        or (profile.photo_url if profile else "")
        or ""
    )
    if not str(photo).strip():
        return {"photos": "Ajoutez au moins une photo de profil."}
    return {}


def _member_payload(data: dict) -> dict:
    age = int(data.get("age"))
    return {
        "first_name": (data.get("first_name") or "").strip(),
        "last_name": (data.get("last_name") or "").strip(),
        "email": normalize_email(data.get("email")),
        "phone": normalize_phone(data.get("phone")),
        "password": data.get("password") or "",
        "date_of_birth": onboarding_controller.dob_from_age(age),
        "gender": data.get("gender"),
        "city": (data.get("city") or "").strip(),
        "country": (data.get("country") or "").strip() or "Sénégal",
        "residence_country": (data.get("residence_country") or data.get("geo_country") or "").strip() or None,
        "religion": data.get("religion") or None,
        "bio": (data.get("bio") or "").strip() or None,
        "looking_for": encode_looking_for(data.get("looking_for")) or None,
        "photo_url": None,
    }


def _apply_profile_extras(profile: Profile, data: dict) -> None:
    profile.interests = onboarding_controller._as_str_list(data.get("interests"))
    profile.personality_traits = onboarding_controller._as_str_list(
        data.get("personality_traits") or data.get("traits")
    )
    profile.life_values = onboarding_controller._clean_values(data.get("life_values") or data.get("values"))
    profile.bio = (data.get("bio") or "").strip() or profile.bio
    profile.looking_for = encode_looking_for(data.get("looking_for")) or profile.looking_for
    intent = (data.get("relationship_intent") or "").strip()
    if intent in _INTENT_VALUES:
        profile.relationship_intent = intent
    profile.life_project = (data.get("life_project") or "").strip()[:800]
    commune = (data.get("commune") or "").strip()
    if commune:
        profile.commune = commune[:180]
    city = (data.get("city") or "").strip()
    if city:
        profile.city = city[:120]
    geo_country = (data.get("residence_country") or data.get("geo_country") or "").strip()
    if geo_country:
        profile.residence_country = geo_country[:120]
    profile.save()


def _save_draft_photos(profile: Profile, data: dict) -> None:
    first = (data.get("photo_data_url") or data.get("photo_url") or "").strip()
    second = (data.get("photo_data_url_2") or data.get("photo_url_2") or "").strip()
    if first:
        _store_photo(profile, first, "profile")
    if second:
        _store_photo(profile, second, "profile2")


def _store_photo(profile: Profile, value: str, kind: str) -> None:
    if value.startswith("data:"):
        onboarding_controller.save_image(profile, kind=kind, data_url=value)
        return
    if value.startswith("http://") or value.startswith("https://") or value.startswith("/"):
        if kind == "profile":
            profile.photo_url = value
            profile.save(update_fields=["photo_url", "updated_at"])
        else:
            profile.photo_url_2 = value
            profile.save(update_fields=["photo_url_2", "updated_at"])


def _email_taken(email: str, exclude: Profile | None = None) -> bool:
    profiles = Profile.objects.filter(email__iexact=email)
    users = User.objects.filter(email__iexact=email)
    if exclude is not None:
        profiles = profiles.exclude(pk=exclude.pk)
        users = users.exclude(pk=exclude.user_id)
    return profiles.exists() or users.exists()


def _phone_taken(phone: str, exclude: Profile | None = None) -> bool:
    found = find_profile_by_phone(phone)
    if found is None:
        return False
    if exclude is not None and found.pk == exclude.pk:
        return False
    return True
