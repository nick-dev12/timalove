"""Score de compatibilité entre deux profils (pourcentage affiché dans l'explorer)."""

from __future__ import annotations

import math
from typing import Iterable

from core.data.onboarding import looking_for_ids
from core.models import Profile
from core.models.choices import RelationshipIntent


def _norm_set(items: Iterable[str] | None) -> set[str]:
    return {str(x).strip().lower() for x in (items or []) if str(x).strip()}


def _jaccard(a: set[str], b: set[str]) -> float | None:
    if not a and not b:
        return None
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0


def _intent_ratio(viewer: Profile, candidate: Profile) -> float | None:
    a = (viewer.relationship_intent or "").strip()
    b = (candidate.relationship_intent or "").strip()
    if not a or not b:
        return None
    if a == b:
        return 1.0
    soft = {RelationshipIntent.A_PRECISER, RelationshipIntent.RELATION_SERIEUSE, RelationshipIntent.MARIAGE}
    if a in soft and b in soft:
        return 0.65
    return 0.0


def _religion_ratio(viewer: Profile, candidate: Profile) -> float | None:
    a = (viewer.religion or "").strip()
    b = (candidate.religion or "").strip()
    if not a or not b:
        return None
    return 1.0 if a == b else 0.0


def _location_ratio(viewer: Profile, candidate: Profile) -> float | None:
    viewer_city = (viewer.city or "").strip().lower()
    cand_city = (candidate.city or "").strip().lower()
    if viewer_city and cand_city:
        return 1.0 if viewer_city == cand_city else 0.35

    viewer_country = (viewer.residence_country or viewer.country or "").strip().lower()
    cand_country = (candidate.residence_country or candidate.country or "").strip().lower()
    if viewer_country and cand_country:
        return 1.0 if viewer_country == cand_country else 0.2

    return None


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _distance_ratio(viewer: Profile, candidate: Profile) -> float | None:
    if viewer.latitude is None or viewer.longitude is None:
        return None
    if candidate.latitude is None or candidate.longitude is None:
        return None
    km = _haversine_km(
        float(viewer.latitude),
        float(viewer.longitude),
        float(candidate.latitude),
        float(candidate.longitude),
    )
    if km <= 15:
        return 1.0
    if km <= 50:
        return 0.85
    if km <= 120:
        return 0.6
    if km <= 300:
        return 0.35
    return 0.15


def _age_ratio(viewer: Profile, candidate: Profile) -> float | None:
    from core.controllers.profile_controller import filters_for

    age = candidate.age
    if age is None:
        return None
    filters = filters_for(viewer)
    age_min = int(filters.get("age_min") or 18)
    age_max = int(filters.get("age_max") or 99)
    if age < age_min or age > age_max:
        return 0.0
    mid = (age_min + age_max) / 2
    span = max(age_max - age_min, 1)
    dist = abs(age - mid) / (span / 2)
    return max(0.55, 1.0 - dist * 0.45)


def _looking_for_ratio(viewer: Profile, candidate: Profile) -> float | None:
    def one_way(source: Profile, target: Profile) -> float | None:
        targets = _norm_set(looking_for_ids(source.looking_for))
        if not targets:
            return None
        signals = _norm_set(target.interests) | _norm_set(target.personality_traits) | _norm_set(target.life_values)
        if not signals:
            return 0.0
        return len(targets & signals) / len(targets)

    a = one_way(viewer, candidate)
    b = one_way(candidate, viewer)
    if a is None and b is None:
        return None
    if a is None:
        return b
    if b is None:
        return a
    return (a + b) / 2


def _profile_richness(candidate: Profile) -> float:
    flags = [
        bool((candidate.bio or "").strip()),
        bool((candidate.profession or "").strip()),
        bool(candidate.relationship_intent),
        bool(candidate.religion),
        bool(candidate.interests),
        bool(candidate.personality_traits),
        bool(candidate.life_values),
        bool((candidate.looking_for or "").strip()),
        bool(candidate.is_verified),
    ]
    return sum(1 for f in flags if f) / len(flags)


def _solo_profile_score(candidate: Profile) -> int:
    """Invité non connecté : score indicatif basé sur la richesse du profil."""
    richness = _profile_richness(candidate)
    base = 62 + round(richness * 22)
    if candidate.is_verified:
        base += 3
    return max(58, min(88, base))


def _candidate_signal_ratio(viewer: Profile, candidate: Profile) -> float:
    """Signal toujours calculable pour différencier les profils entre eux."""
    parts: list[float] = []
    va, ca = viewer.age, candidate.age
    if va is not None and ca is not None:
        parts.append(max(0.3, 1.0 - abs(va - ca) / 22))
    parts.append(_profile_richness(candidate))
    tag_count = len(
        _norm_set(candidate.interests)
        | _norm_set(candidate.life_values)
        | _norm_set(candidate.personality_traits)
    )
    parts.append(min(1.0, tag_count / 6))
    loc = _location_ratio(viewer, candidate)
    if loc is not None:
        parts.append(loc)
    return sum(parts) / len(parts)


def compatibility_for_profile_id(viewer: Profile | None, profile_id) -> tuple[bool, str, int | None]:
    """Score pour un profil public éligible."""
    from core.models.choices import RegistrationStatus, UserRole

    try:
        candidate = Profile.objects.get(pk=profile_id)
    except Profile.DoesNotExist:
        return False, "Profil introuvable.", None

    if (
        candidate.registration_status != RegistrationStatus.APPROVED
        or candidate.is_hidden
        or candidate.role != UserRole.MEMBER
        or candidate.banned_at
        or not (candidate.photo_url or "").strip()
    ):
        return False, "Profil introuvable.", None

    return True, "", compatibility_percent(viewer, candidate)


def compatibility_percent(viewer: Profile | None, candidate: Profile) -> int:
    """Compatibilité 0–99 % entre le viewer et un profil candidat."""
    if viewer is None or viewer.pk == candidate.pk:
        return _solo_profile_score(candidate)

    weighted: list[tuple[float, float]] = [
        (22.0, _intent_ratio(viewer, candidate)),
        (14.0, _religion_ratio(viewer, candidate)),
        (16.0, _jaccard(_norm_set(viewer.life_values), _norm_set(candidate.life_values))),
        (14.0, _jaccard(_norm_set(viewer.interests), _norm_set(candidate.interests))),
        (10.0, _jaccard(_norm_set(viewer.personality_traits), _norm_set(candidate.personality_traits))),
        (10.0, _looking_for_ratio(viewer, candidate)),
        (12.0, _candidate_signal_ratio(viewer, candidate)),
        (8.0, _location_ratio(viewer, candidate)),
        (6.0, _distance_ratio(viewer, candidate)),
        (5.0, _age_ratio(viewer, candidate)),
    ]

    active = [(w, r) for w, r in weighted if r is not None]
    if not active:
        return _solo_profile_score(candidate)

    total_w = sum(w for w, _ in active)
    ratio = sum(w * r for w, r in active) / total_w

    bonus = 0.0
    if candidate.is_verified:
        bonus += 0.04
    bonus += _profile_richness(candidate) * 0.06

    intent = _intent_ratio(viewer, candidate)
    religion = _religion_ratio(viewer, candidate)
    location = _location_ratio(viewer, candidate)
    if intent == 1.0 and religion == 1.0:
        bonus += 0.06
    if location == 1.0:
        bonus += 0.04

    score = (ratio + bonus) * 100
    return max(52, min(99, round(score)))
