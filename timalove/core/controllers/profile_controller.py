"""Profils, galerie (5 photos max) et filtres de découverte."""

from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.db.models import Max
from django.utils import timezone

from core.data.onboarding import INTERESTS, TRAITS
from core.models import Profile, ProfileGalleryPhoto
from core.models.choices import Gender, LastSeenVisibility, RegistrationStatus, RelationshipIntent, Religion, SubscriptionStatus, SubscriptionTier
from core.controllers.onboarding_controller import _clean_values, _read_image_bytes, dob_from_age

MAX_GALLERY_PHOTOS = 5

DEFAULT_FILTERS = {
    "age_min": 18,
    "age_max": 99,
    "gender": "",
    "religion": "",
    "country": "",
    "verified_only": False,
    "online_only": False,
}

DEFAULT_NOTIF_PREFS = {
    "likes": True,
    "matches": True,
    "messages": True,
    "push": True,
}

ALLOWED_PROFILE_FIELDS = {
    "first_name",
    "last_name",
    "phone",
    "city",
    "commune",
    "country",
    "residence_country",
    "religion",
    "relationship_intent",
    "life_project",
    "profession",
    "bio",
    "looking_for",
    "hide_age",
    "is_hidden",
    "last_seen_visibility",
    "notification_preferences",
    "gender",
    "interests",
    "personality_traits",
    "life_values",
}


def get_own(profile: Profile) -> Profile:
    return Profile.objects.prefetch_related("gallery_photos").get(pk=profile.pk)


def filters_for(profile: Profile) -> dict:
    raw = profile.discover_filters if isinstance(profile.discover_filters, dict) else {}
    out = dict(DEFAULT_FILTERS)
    out.update({k: raw[k] for k in DEFAULT_FILTERS if k in raw})
    try:
        out["age_min"] = max(18, min(99, int(out["age_min"] or 18)))
        out["age_max"] = max(out["age_min"], min(99, int(out["age_max"] or 60)))
    except (TypeError, ValueError):
        out["age_min"], out["age_max"] = 18, 99
    out["verified_only"] = bool(out.get("verified_only"))
    out["online_only"] = bool(out.get("online_only"))
    out["gender"] = out.get("gender") or ""
    out["religion"] = out.get("religion") or ""
    out["country"] = (out.get("country") or "").strip()
    return out


def gallery_urls(profile: Profile) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    primary = (profile.photo_url or "").strip()
    if primary:
        items.append({"id": "primary", "url": primary, "is_primary": True})
        seen.add(primary)
    for photo in profile.gallery_photos.all():
        url = (photo.photo_url or "").strip()
        if not url or url in seen:
            continue
        items.append({"id": str(photo.pk), "url": url, "is_primary": False})
        seen.add(url)
    for extra in (profile.photo_url_2, profile.photo_url_3):
        url = (extra or "").strip()
        if url and url not in seen:
            items.append({"id": "", "url": url, "is_primary": False})
            seen.add(url)
    return items


def completion_score(profile: Profile) -> int:
    checks = [
        bool((profile.first_name or "").strip()),
        bool((profile.bio or "").strip()) and len(profile.bio or "") >= 40,
        bool((profile.looking_for or "").strip()),
        bool((profile.profession or "").strip()),
        bool((profile.city or "").strip()),
        bool(profile.religion),
        bool(profile.photo_url),
        len(gallery_urls(profile)) >= 2,
        bool(profile.interests),
        bool(profile.personality_traits),
    ]
    return int(round(100 * sum(1 for c in checks if c) / len(checks)))


def serialize_visit(profile: Profile) -> dict:
    location_parts = [p for p in (profile.commune, profile.city, profile.country) if p]
    photos = gallery_urls(profile)
    interest_labels = {i["id"]: i["label"] for i in INTERESTS}
    trait_labels = {t["id"]: t["label"] for t in TRAITS}
    return {
        "id": str(profile.pk),
        "first_name": profile.first_name or "Membre",
        "last_name": profile.last_name or "",
        "age": None if profile.hide_age else profile.age,
        "city": profile.city or "",
        "commune": profile.commune or "",
        "country": profile.country or "",
        "residence_country": profile.residence_country or "",
        "location": ", ".join(location_parts) if location_parts else "TimaLove",
        "photo_url": profile.primary_photo,
        "photos": photos,
        "is_verified": bool(profile.is_verified),
        "bio": (profile.bio or "").strip(),
        "looking_for": (profile.looking_for or "").strip(),
        "profession": (profile.profession or "").strip(),
        "religion": profile.get_religion_display() if profile.religion else "",
        "religion_value": profile.religion or "",
        "gender": profile.gender or "",
        "gender_label": profile.get_gender_display() if profile.gender else "",
        "relationship_intent": profile.relationship_intent or "",
        "relationship_intent_label": profile.get_relationship_intent_display() if profile.relationship_intent else "",
        "life_project": (profile.life_project or "").strip(),
        "phone": profile.phone or "",
        "is_online": bool(profile.is_online),
        "is_boosted": bool(profile.is_boosted),
        "member_since": profile.created_at.year if profile.created_at else None,
        "followers": int(profile.likes_received_count or 0),
        "likes_given": int(profile.likes_given_count or 0),
        "matches": int(profile.matches_count or 0),
        "interests": list(profile.interests or []),
        "interest_labels": [interest_labels.get(i, i) for i in (profile.interests or [])],
        "personality_traits": list(profile.personality_traits or []),
        "trait_labels": [trait_labels.get(t, t) for t in (profile.personality_traits or [])],
        "life_values": [str(v).strip() for v in (profile.life_values or []) if str(v).strip()],
        "completion": completion_score(profile),
        "hide_age": bool(profile.hide_age),
        "is_hidden": bool(profile.is_hidden),
    }


def notification_prefs_for(profile: Profile) -> dict:
    prefs = dict(DEFAULT_NOTIF_PREFS)
    raw = profile.notification_preferences if isinstance(profile.notification_preferences, dict) else {}
    for key in prefs:
        if key in raw:
            prefs[key] = bool(raw[key])
    return prefs


def settings_context(profile: Profile) -> dict:
    from core.controllers import payment_controller, site_settings_controller

    prices = site_settings_controller.get("subscription_prices") or {}
    plans = []
    vip_ids = {
        SubscriptionTier.VIP_1M,
        SubscriptionTier.VIP_2M,
        SubscriptionTier.VIP_FEMME_1W,
    }
    for value, label in SubscriptionTier.choices:
        if value == SubscriptionTier.FREE:
            continue
        amount = int(prices.get(value, 0))
        plans.append(
            {
                "id": value,
                "label": label,
                "price": amount,
                "price_label": f"{amount:,}".replace(",", "\u202f") + " FCFA",
                "is_vip": value in vip_ids,
            }
        )
    status = payment_controller.payment_status(profile)
    tier_labels = dict(SubscriptionTier.choices)
    status_labels = dict(SubscriptionStatus.choices)
    end = profile.subscription_end_date
    boost_end = profile.boost_end_date
    return {
        "payment_status": status,
        "tier_label": tier_labels.get(profile.subscription_tier, profile.subscription_tier),
        "status_label": status_labels.get(profile.subscription_status, profile.subscription_status),
        "subscription_end_display": timezone.localtime(end).strftime("%d/%m/%Y") if end else None,
        "boost_end_display": timezone.localtime(boost_end).strftime("%d/%m/%Y") if boost_end else None,
        "plans": plans,
        "visibilities": LastSeenVisibility.choices,
        "notif_prefs": notification_prefs_for(profile),
        "boost_price_label": "5\u202f000 FCFA",
    }


def update_profile(profile: Profile, data: dict) -> Profile:
    payload = dict(data)
    age = payload.pop("age", None)
    if age not in (None, ""):
        try:
            profile.date_of_birth = dob_from_age(int(age))
        except (TypeError, ValueError):
            pass
    if "notification_preferences" in payload:
        incoming = payload["notification_preferences"]
        if isinstance(incoming, dict):
            merged = notification_prefs_for(profile)
            for key in DEFAULT_NOTIF_PREFS:
                if key in incoming:
                    merged[key] = bool(incoming[key])
            payload["notification_preferences"] = merged
        else:
            payload.pop("notification_preferences")
    if "last_seen_visibility" in payload:
        vis = payload["last_seen_visibility"]
        if vis not in LastSeenVisibility.values:
            payload.pop("last_seen_visibility")
    if "relationship_intent" in payload:
        intent = payload.get("relationship_intent") or ""
        if intent and intent not in RelationshipIntent.values:
            payload.pop("relationship_intent")
        else:
            payload["relationship_intent"] = intent
    if "life_project" in payload:
        payload["life_project"] = str(payload.get("life_project") or "").strip()[:800]
    if "commune" in payload:
        payload["commune"] = str(payload.get("commune") or "").strip()[:180]
    if "life_values" in payload:
        payload["life_values"] = _clean_values(payload.get("life_values"))
    for key, value in payload.items():
        if key in ALLOWED_PROFILE_FIELDS:
            setattr(profile, key, value)
    profile.save()
    return profile


def update_filters(profile: Profile, data: dict) -> dict:
    current = filters_for(profile)
    gender = data.get("gender") or ""
    if gender not in {"", "all", Gender.MALE, Gender.FEMALE}:
        gender = current["gender"]
    religion = data.get("religion") or ""
    if religion and religion not in {c.value for c in Religion}:
        religion = current["religion"]
    try:
        age_min = max(18, min(99, int(data.get("age_min") or current["age_min"])))
        age_max = max(age_min, min(99, int(data.get("age_max") or current["age_max"])))
    except (TypeError, ValueError):
        age_min, age_max = current["age_min"], current["age_max"]
    filters = {
        "age_min": age_min,
        "age_max": age_max,
        "gender": gender,
        "religion": religion,
        "country": (data.get("country") or "").strip()[:120],
        "verified_only": bool(data.get("verified_only")),
        "online_only": bool(data.get("online_only")),
    }
    profile.discover_filters = filters
    profile.save(update_fields=["discover_filters", "updated_at"])
    return filters


def _sync_legacy_slots(profile: Profile) -> None:
    urls = [item["url"] for item in gallery_urls(profile)]
    profile.photo_url = urls[0] if urls else profile.photo_url
    profile.photo_url_2 = urls[1] if len(urls) > 1 else None
    profile.photo_url_3 = urls[2] if len(urls) > 2 else None
    profile.save(update_fields=["photo_url", "photo_url_2", "photo_url_3", "updated_at"])


def _next_position(profile: Profile) -> int:
    current = profile.gallery_photos.aggregate(m=Max("position")).get("m")
    return int(current or 0) + 1


def _store_file(profile: Profile, *, upload=None, data_url: str = "", kind: str = "gallery") -> str:
    payload, ext = _read_image_bytes(upload, data_url)
    folder = Path(settings.MEDIA_ROOT) / "profile-photos"
    folder.mkdir(parents=True, exist_ok=True)
    filename = f"{profile.id}_{kind}_{uuid.uuid4().hex[:10]}.{ext}"
    dest = folder / filename
    dest.write_bytes(payload)
    return f"{settings.MEDIA_URL}profile-photos/{filename}"


@transaction.atomic
def add_gallery_photo(profile: Profile, *, upload=None, data_url: str = "") -> dict:
    count = len(gallery_urls(profile))
    if count >= MAX_GALLERY_PHOTOS:
        raise ValueError(f"Vous pouvez ajouter jusqu’à {MAX_GALLERY_PHOTOS} photos.")
    url = _store_file(profile, upload=upload, data_url=data_url, kind="gallery")
    if not (profile.photo_url or "").strip():
        profile.photo_url = url
        profile.save(update_fields=["photo_url", "updated_at"])
        return {"id": "primary", "url": url, "is_primary": True}
    obj = ProfileGalleryPhoto.objects.create(
        profile=profile,
        position=_next_position(profile),
        photo_url=url,
    )
    _sync_legacy_slots(profile)
    return {"id": str(obj.pk), "url": url, "is_primary": False}


@transaction.atomic
def set_primary_photo(profile: Profile, photo_id: str) -> str:
    if photo_id == "primary":
        return profile.photo_url or ""
    photo = ProfileGalleryPhoto.objects.filter(profile=profile, pk=photo_id).first()
    if not photo:
        raise ValueError("Photo introuvable.")
    previous = (profile.photo_url or "").strip()
    profile.photo_url = photo.photo_url
    profile.save(update_fields=["photo_url", "updated_at"])
    if previous and previous != photo.photo_url:
        photo.photo_url = previous
        photo.save(update_fields=["photo_url"])
    else:
        photo.delete()
    _sync_legacy_slots(profile)
    return profile.photo_url or ""


@transaction.atomic
def delete_gallery_photo(profile: Profile, photo_id: str) -> None:
    if photo_id == "primary":
        rest = list(profile.gallery_photos.order_by("position"))
        if rest:
            profile.photo_url = rest[0].photo_url
            rest[0].delete()
            profile.save(update_fields=["photo_url", "updated_at"])
        else:
            profile.photo_url = None
            profile.save(update_fields=["photo_url", "updated_at"])
        _sync_legacy_slots(profile)
        return
    deleted, _ = ProfileGalleryPhoto.objects.filter(profile=profile, pk=photo_id).delete()
    if not deleted:
        raise ValueError("Photo introuvable.")
    _sync_legacy_slots(profile)


def set_avatar(profile: Profile, *, upload=None, data_url: str = "") -> str:
    url = _store_file(profile, upload=upload, data_url=data_url, kind="avatar")
    profile.photo_url = url
    profile.save(update_fields=["photo_url", "updated_at"])
    return url


def dob_bounds(age_min: int, age_max: int) -> tuple[date, date]:
    today = timezone.localdate()

    def shifted(years: int) -> date:
        try:
            return today.replace(year=today.year - years)
        except ValueError:
            return today.replace(year=today.year - years, day=28)

    youngest = shifted(age_min)
    oldest = shifted(age_max + 1)
    return oldest, youngest


def apply_discover_filters(qs, viewer: Profile):
    filters = filters_for(viewer)
    gender = filters.get("gender") or ""
    if gender in {Gender.MALE, Gender.FEMALE}:
        qs = qs.filter(gender=gender)
    elif gender != "all" and viewer.gender:
        opposite = Gender.FEMALE if viewer.gender == Gender.MALE else Gender.MALE
        qs = qs.filter(gender=opposite)
    if filters.get("religion"):
        qs = qs.filter(religion=filters["religion"])
    if filters.get("country"):
        qs = qs.filter(country__iexact=filters["country"])
    if filters.get("verified_only"):
        qs = qs.filter(is_verified=True)
    if filters.get("online_only"):
        qs = qs.filter(is_online=True)
    if filters["age_min"] > 18 or filters["age_max"] < 99:
        oldest, youngest = dob_bounds(filters["age_min"], filters["age_max"])
        qs = qs.filter(date_of_birth__gt=oldest, date_of_birth__lte=youngest)
    return qs


@transaction.atomic
def set_gallery(profile: Profile, photos: list[dict]) -> list[ProfileGalleryPhoto]:
    """Compat ancienne API — 5 photos maximum."""
    ProfileGalleryPhoto.objects.filter(profile=profile).delete()
    created = []
    for index, item in enumerate(photos[:MAX_GALLERY_PHOTOS], start=1):
        obj = ProfileGalleryPhoto.objects.create(
            profile=profile,
            position=int(item.get("position") or index),
            photo_url=item["photo_url"],
        )
        created.append(obj)
    _sync_legacy_slots(profile)
    return created


def landing_members(limit: int = 6) -> list[Profile]:
    qs = (
        Profile.objects.filter(
            registration_status=RegistrationStatus.APPROVED,
            is_hidden=False,
            role="member",
        )
        .exclude(photo_url__isnull=True)
        .exclude(photo_url="")
        .order_by("-is_boosted", "-created_at")[:limit]
    )
    return list(qs)


def delete_account(profile: Profile) -> None:
    user = profile.user
    profile.delete()
    user.delete()
