"""Feed public style explorer (scroll vertical type TikTok)."""

from __future__ import annotations

import random
import uuid

from django.db.models import Case, IntegerField, Q, Value, When
from django.http import Http404

from core.controllers import matching_controller, swipe_controller
from core.data.onboarding import INTERESTS, TRAITS, looking_for_free_text, looking_for_ids, looking_for_labels, life_value_labels
from core.models import Profile, Swipe
from core.models.choices import RegistrationStatus, UserRole

PAGE_SIZE = 8
PHOTOS_PER_CARD = 8


def _chip_catalog(catalog: list[dict], selected_raw) -> list[dict]:
    selected = {str(item).strip().lower() for item in (selected_raw or []) if str(item).strip()}
    return [
        {
            "id": item["id"],
            "label": item["label"],
            "icon": item.get("icon", ""),
            "selected": item["id"].lower() in selected or item["label"].lower() in selected,
        }
        for item in catalog
    ]


def _public_place(value: str | None) -> str:
    text = (value or "").strip()
    if not text or "@" in text:
        return ""
    return text


def _location_label(profile: Profile) -> str:
    parts = [p for p in (_public_place(profile.commune), _public_place(profile.city), _public_place(profile.country)) if p]
    return ", ".join(parts) if parts else "TimaLove"


def collect_photos(profile: Profile, limit: int = PHOTOS_PER_CARD) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for raw in (profile.photo_url, profile.photo_url_2, profile.photo_url_3):
        url = (raw or "").strip()
        if url and url not in seen:
            urls.append(url)
            seen.add(url)
    gallery = getattr(profile, "_prefetched_objects_cache", {}).get("gallery_photos")
    extras = gallery if gallery is not None else profile.gallery_photos.all()
    for item in extras:
        if len(urls) >= limit:
            break
        url = (item.photo_url or "").strip()
        if url and url not in seen:
            urls.append(url)
            seen.add(url)
    return urls[:limit]


def compatibility_score(profile: Profile, viewer: Profile | None = None) -> int:
    """Score affiché — compatibilité réelle si viewer connecté."""
    return matching_controller.compatibility_percent(viewer, profile)


def _eligible_queryset():
    return (
        Profile.objects.filter(
            registration_status=RegistrationStatus.APPROVED,
            is_hidden=False,
            role=UserRole.MEMBER,
        )
        .exclude(banned_at__isnull=False)
        .exclude(photo_url__isnull=True)
        .exclude(photo_url="")
    )


def serialize_card(
    profile: Profile,
    *,
    liked: bool = False,
    super_liked: bool = False,
    viewer=None,
) -> dict:
    photos = collect_photos(profile)
    city = _public_place(profile.city)
    country = _public_place(profile.country)
    location_parts = [p for p in (city, country) if p]
    return {
        "id": str(profile.pk),
        "first_name": profile.first_name or "Membre",
        "age": None if profile.hide_age else profile.age,
        "city": city,
        "country": country,
        "location": ", ".join(location_parts) if location_parts else "TimaLove",
        "photo_url": photos[0] if photos else profile.primary_photo,
        "photos": photos,
        "is_verified": bool(profile.is_verified),
        "bio": (profile.bio or "")[:140],
        "profession": (profile.profession or "").strip(),
        "profile_url": f"/explorer/profil/{profile.pk}/",
        "liked": liked,
        "super_liked": super_liked,
    }


def public_feed(*, offset: int = 0, limit: int = PAGE_SIZE, seed: str | None = None, viewer=None) -> tuple[list[dict], bool]:
    """Retourne (cartes, has_more) en ordre aléatoire stable via seed session."""
    offset = max(0, offset)
    limit = min(max(1, limit), 20)
    qs = _eligible_queryset()
    if viewer is not None:
        qs = qs.exclude(pk=viewer.pk)
        from core.controllers.profile_controller import apply_discover_filters

        qs = apply_discover_filters(qs, viewer)
        qs = swipe_controller.apply_feed_exclusions(qs, viewer)
    ids = list(qs.values_list("pk", flat=True))
    rng = random.Random(seed or "timalove")
    rng.shuffle(ids)

    chunk = ids[offset : offset + limit + 1]
    has_more = len(chunk) > limit
    page_ids = chunk[:limit]
    by_id = Profile.objects.prefetch_related("gallery_photos").in_bulk(page_ids)
    profiles = [by_id[i] for i in page_ids if i in by_id]
    liked_ids: set = set()
    super_ids: set = set()
    if viewer is not None and page_ids:
        for swiped_id, is_like, is_super in Swipe.objects.filter(
            swiper=viewer, swiped_id__in=page_ids
        ).filter(Q(is_like=True) | Q(is_super_like=True)).values_list(
            "swiped_id", "is_like", "is_super_like"
        ):
            if is_like:
                liked_ids.add(swiped_id)
            if is_super:
                super_ids.add(swiped_id)
    return [
        serialize_card(p, liked=p.pk in liked_ids, super_liked=p.pk in super_ids, viewer=viewer)
        for p in profiles
    ], has_more


def get_public_profile(profile_id, viewer=None) -> dict | None:
    """Détail public d'un profil visitable depuis l'explorer."""
    try:
        uid = uuid.UUID(str(profile_id))
    except (TypeError, ValueError):
        return None

    profile = (
        _eligible_queryset()
        .prefetch_related("gallery_photos")
        .filter(pk=uid)
        .first()
    )
    if not profile:
        return None

    photos = collect_photos(profile, limit=12)

    religion_label = profile.get_religion_display() if profile.religion else ""
    intent_label = profile.get_relationship_intent_display() if profile.relationship_intent else ""
    gender_label = profile.get_gender_display() if profile.gender else ""
    interest_map = {i["id"]: i["label"] for i in INTERESTS}
    trait_map = {t["id"]: t["label"] for t in TRAITS}

    return {
        "id": str(profile.pk),
        "first_name": profile.first_name or "Membre",
        "last_name": (profile.last_name or "").strip(),
        "full_name": profile.display_name,
        "age": None if profile.hide_age else profile.age,
        "city": _public_place(profile.city),
        "commune": _public_place(profile.commune),
        "country": _public_place(profile.country),
        "residence_country": profile.residence_country or "",
        "location": _location_label(profile),
        "photo_url": profile.primary_photo,
        "photos": photos or ([profile.primary_photo] if profile.primary_photo else []),
        "is_verified": bool(profile.is_verified),
        "compatibility": compatibility_score(profile, viewer),
        "bio": (profile.bio or "").strip(),
        "looking_for": (profile.looking_for or "").strip(),
        "looking_for_ids": looking_for_ids(profile.looking_for),
        "looking_for_labels": looking_for_labels(profile.looking_for),
        "looking_for_text": looking_for_free_text(profile.looking_for),
        "profession": (profile.profession or "").strip(),
        "religion": religion_label,
        "gender": profile.gender or "",
        "gender_label": gender_label,
        "relationship_intent": profile.relationship_intent or "",
        "relationship_intent_label": intent_label,
        "life_project": (profile.life_project or "").strip(),
        "is_online": bool(profile.is_online),
        "is_boosted": bool(profile.is_boosted),
        "member_since": profile.created_at.year if profile.created_at else None,
        "followers": int(profile.likes_received_count or 0),
        "following": int(profile.likes_given_count or 0),
        "favorites": int(profile.matches_count or 0),
        "interest_labels": [
            interest_map.get(i, i) for i in (profile.interests or [])
        ],
        "trait_labels": [
            trait_map.get(t, t) for t in (profile.personality_traits or [])
        ],
        "interest_chips": _chip_catalog(INTERESTS, profile.interests),
        "trait_chips": _chip_catalog(TRAITS, profile.personality_traits),
        "life_values": [str(v).strip() for v in (profile.life_values or []) if str(v).strip()],
        "life_value_labels": life_value_labels(profile.life_values),
    }


def get_public_profile_or_404(profile_id, viewer=None) -> dict:
    data = get_public_profile(profile_id, viewer=viewer)
    if not data:
        raise Http404("Profil introuvable")
    return data


def search_profiles(query: str, *, viewer=None, limit: int = 8) -> list[dict]:
    """Recherche live : prénom, ville, profession — photo + nom pour l’autocomplete."""
    q = " ".join((query or "").split())
    if len(q) < 2:
        return []

    qs = _eligible_queryset()
    if viewer is not None:
        qs = qs.exclude(pk=viewer.pk)
        from core.controllers.profile_controller import apply_discover_filters

        qs = apply_discover_filters(qs, viewer)
        qs = swipe_controller.apply_feed_exclusions(qs, viewer)

    qs = (
        qs.filter(
            Q(first_name__icontains=q)
            | Q(city__icontains=q)
            | Q(profession__icontains=q)
        )
        .annotate(
            rank=Case(
                When(first_name__istartswith=q, then=Value(0)),
                When(first_name__icontains=q, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("rank", "first_name")[: max(1, min(limit, 12))]
    )

    results = []
    for profile in qs:
        name = (profile.first_name or "Membre").strip() or "Membre"
        results.append(
            {
                "id": str(profile.pk),
                "first_name": name,
                "age": None if profile.hide_age else profile.age,
                "photo_url": profile.primary_photo or "",
                "city": profile.city or "",
                "profile_url": f"/explorer/profil/{profile.pk}/",
                "initial": name[:1].upper(),
            }
        )
    return results
