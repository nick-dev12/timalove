"""Onboarding 4 étapes — finalisation de compte."""

from __future__ import annotations

import base64
import re
import uuid
from decimal import Decimal, InvalidOperation
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.utils import timezone

from core.data.countries import COUNTRIES_FR
from core.data.onboarding import (
    FACE_MATCH_THRESHOLD,
    MIN_INTERESTS,
    MIN_TRAITS,
    encode_looking_for,
)

MAX_VALUES = 12
from core.models import Profile
from core.models.choices import Gender, RegistrationStatus, Religion

_DATA_URL_RE = re.compile(r"^data:image/(png|jpeg|jpg|webp);base64,(.+)$", re.I)


def age_from_dob(dob: date | None) -> int | None:
    if not dob:
        return None
    today = timezone.localdate()
    years = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        years -= 1
    return years


def dob_from_age(age: int) -> date:
    today = timezone.localdate()
    try:
        return date(today.year - age, today.month, today.day)
    except ValueError:
        return date(today.year - age, 2, 28)


def current_step(profile: Profile) -> int:
    if profile.onboarding_completed:
        return 4
    step = profile.onboarding_step or 1
    return min(max(step, 1), 4)


def _parse_coord(value, lo: Decimal, hi: Decimal) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    if number < lo or number > hi:
        return None
    return number.quantize(Decimal("0.000001"))


def save_location(profile: Profile, data: dict, *, persist: bool = True) -> tuple[bool, str]:
    lat = _parse_coord(data.get("latitude"), Decimal("-90"), Decimal("90"))
    lng = _parse_coord(data.get("longitude"), Decimal("-180"), Decimal("180"))
    if lat is None or lng is None:
        if profile.latitude is not None and profile.longitude is not None:
            return True, "Position déjà enregistrée."
        if persist:
            return False, "Impossible de lire votre position. Réessayez."
        return False, "Enregistrez votre position pour continuer."
    profile.latitude = lat
    profile.longitude = lng
    profile.location_updated_at = timezone.now()
    city = (data.get("city") or "").strip()
    commune = (data.get("commune") or "").strip()
    country = (data.get("country") or data.get("residence_country") or "").strip()
    update_fields = ["latitude", "longitude", "location_updated_at", "updated_at"]
    if city:
        profile.city = city[:120]
        update_fields.append("city")
    if commune:
        profile.commune = commune[:180]
        update_fields.append("commune")
    if country:
        profile.residence_country = country[:120]
        update_fields.append("residence_country")
    if persist:
        profile.save(update_fields=list(dict.fromkeys(update_fields)))
    return True, "Position enregistrée."


def _clean_values(value) -> list[str]:
    items = _as_str_list(value)
    out: list[str] = []
    seen: set[str] = set()
    for item in items:
        label = item[:40].strip()
        key = label.casefold()
        if not label or key in seen:
            continue
        seen.add(key)
        out.append(label)
        if len(out) >= MAX_VALUES:
            break
    return out


def save_step_1(profile: Profile, data: dict) -> tuple[bool, str]:
    last_name = (data.get("last_name") or "").strip()
    first_name = (data.get("first_name") or "").strip()
    if not last_name:
        return False, "Le nom est obligatoire."
    if not first_name:
        return False, "Le prénom est obligatoire."

    try:
        age = int(data.get("age") or 0)
    except (TypeError, ValueError):
        return False, "Indiquez un âge valide."
    if age < 18:
        return False, "Vous devez avoir au moins 18 ans."
    if age > 99:
        return False, "Vérifiez l’âge saisi."

    gender = data.get("gender") or ""
    if gender not in {Gender.MALE, Gender.FEMALE}:
        return False, "Choisissez Homme ou Femme."

    country = (data.get("country") or "").strip()
    if country not in COUNTRIES_FR:
        return False, "Sélectionnez votre pays d’origine dans la liste."

    religion = data.get("religion") or ""
    if religion not in {Religion.MUSULMANE, Religion.CHRETIENNE, Religion.AUTRE}:
        return False, "Sélectionnez votre religion."

    from core.controllers.auth_controller import normalize_phone

    phone = normalize_phone(data.get("phone"))
    if not phone or len(phone) < 8:
        return False, "Indiquez un numéro de téléphone valide."

    profile.last_name = last_name
    profile.first_name = first_name
    profile.date_of_birth = dob_from_age(age)
    profile.gender = gender
    profile.country = country
    if not (profile.city or "").strip():
        profile.city = country
    profile.religion = religion
    profile.phone = phone
    ok_loc, loc_msg = save_location(profile, data, persist=False)
    if not ok_loc:
        return False, loc_msg
    profile.onboarding_step = max(profile.onboarding_step or 1, 2)
    profile.save()
    profile.user.first_name = first_name
    profile.user.last_name = last_name
    profile.user.save(update_fields=["first_name", "last_name"])
    return True, "Belle entrée. Continuons."


def save_step_2(profile: Profile, data: dict) -> tuple[bool, str]:
    interests = _as_str_list(data.get("interests"))
    traits = _as_str_list(data.get("personality_traits") or data.get("traits"))
    if len(interests) < MIN_INTERESTS:
        return False, "Choisissez au moins un centre d’intérêt parmi les options proposées."
    if len(traits) < MIN_TRAITS:
        return False, "Choisissez au moins un trait de caractère parmi les options proposées."
    values = _clean_values(data.get("life_values") or data.get("values"))
    profile.interests = interests
    profile.personality_traits = traits
    profile.life_values = values
    profile.onboarding_step = max(profile.onboarding_step or 1, 3)
    profile.save(
        update_fields=[
            "interests",
            "personality_traits",
            "life_values",
            "onboarding_step",
            "updated_at",
        ]
    )
    return True, "C’est vous, déjà. Encore un peu."


def save_step_3(profile: Profile, data: dict) -> tuple[bool, str]:
    profile.bio = (data.get("bio") or "").strip()
    profile.looking_for = encode_looking_for(data.get("looking_for")) or None
    profile.onboarding_step = max(profile.onboarding_step or 1, 4)
    profile.save(update_fields=["bio", "looking_for", "onboarding_step", "updated_at"])
    return True, "Dernière étape."


def save_step_4(profile: Profile, data: dict) -> tuple[bool, str]:
    photo = (data.get("photo_url") or profile.photo_url or "").strip()
    verification = (data.get("verification_photo_url") or profile.verification_photo_url or "").strip()
    if not photo:
        return False, "Ajoutez une photo de profil."
    if not verification:
        return False, "Prenez une photo de vérification en direct."

    score = data.get("face_match_score")
    try:
        score = float(score) if score is not None and score != "" else profile.face_match_score
    except (TypeError, ValueError):
        score = profile.face_match_score

    if score is not None and score < FACE_MATCH_THRESHOLD:
        return False, "Les visages ne correspondent pas assez. Reprenez le selfie face caméra."

    profile.photo_url = photo
    profile.verification_photo_url = verification
    profile.face_match_score = score
    if score is not None and score >= FACE_MATCH_THRESHOLD:
        profile.is_verified = True
    profile.onboarding_step = 4
    profile.onboarding_completed = True
    profile.registration_status = RegistrationStatus.APPROVED
    profile.save()
    return True, "Bienvenue dans TimaLove."


def save_image(profile: Profile, *, kind: str, upload: UploadedFile | None = None, data_url: str = "") -> str:
    if kind not in {"profile", "profile2", "verification"}:
        raise ValueError("Type d’image invalide.")

    payload, ext = _read_image_bytes(upload, data_url)
    folder = Path(settings.MEDIA_ROOT) / "profile-photos"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{profile.id}_{kind}_{uuid.uuid4().hex[:10]}.{ext}"
    dest = folder / filename
    dest.write_bytes(payload)
    url = f"{settings.MEDIA_URL}profile-photos/{filename}"
    if kind == "profile":
        profile.photo_url = url
        profile.save(update_fields=["photo_url", "updated_at"])
    elif kind == "profile2":
        profile.photo_url_2 = url
        profile.save(update_fields=["photo_url_2", "updated_at"])
    else:
        profile.verification_photo_url = url
        profile.save(update_fields=["verification_photo_url", "updated_at"])
    return url


def _read_image_bytes(upload: UploadedFile | None, data_url: str) -> tuple[bytes, str]:
    if upload:
        content = upload.read()
        name = (upload.name or "photo.jpg").lower()
        ext = "jpg"
        if name.endswith(".png"):
            ext = "png"
        elif name.endswith(".webp"):
            ext = "webp"
        if len(content) > 6 * 1024 * 1024:
            raise ValueError("Image trop lourde (6 Mo max).")
        return content, ext

    match = _DATA_URL_RE.match((data_url or "").strip())
    if not match:
        raise ValueError("Image invalide.")
    ext = "jpg" if match.group(1).lower() in {"jpeg", "jpg"} else match.group(1).lower()
    raw = base64.b64decode(match.group(2))
    if len(raw) > 6 * 1024 * 1024:
        raise ValueError("Image trop lourde (6 Mo max).")
    return raw, ext


def _as_str_list(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",")]
        return [p for p in parts if p]
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    return []
