"""Discover feed."""

from __future__ import annotations

from django.db.models import Exists, OuterRef, Q

from core.models import BlockedUser, Profile, Swipe
from core.models.choices import Gender, RegistrationStatus, UserRole


def opposite_gender(gender: str) -> str:
    return Gender.FEMALE if gender == Gender.MALE else Gender.MALE


def feed_for(viewer: Profile, limit: int = 20) -> list[Profile]:
    already = Swipe.objects.filter(swiper=viewer, swiped_id=OuterRef("pk"))
    blocked_by_me = BlockedUser.objects.filter(blocker=viewer, blocked_id=OuterRef("pk"))
    blocked_me = BlockedUser.objects.filter(blocker_id=OuterRef("pk"), blocked=viewer)

    qs = (
        Profile.objects.filter(
            registration_status=RegistrationStatus.APPROVED,
            is_hidden=False,
            role=UserRole.MEMBER,
        )
        .exclude(pk=viewer.pk)
        .exclude(banned_at__isnull=False)
        .annotate(
            already_swiped=Exists(already),
            is_blocked=Exists(blocked_by_me) | Exists(blocked_me),
        )
        .filter(already_swiped=False, is_blocked=False)
    )
    from core.controllers.profile_controller import apply_discover_filters

    qs = apply_discover_filters(qs, viewer)
    return list(qs.order_by("-is_boosted", "-last_active_at", "-created_at")[:limit])


def get_discover_profile(viewer: Profile, profile_id) -> Profile | None:
    try:
        p = Profile.objects.get(pk=profile_id)
    except Profile.DoesNotExist:
        return None
    if p.gender == viewer.gender or p.pk == viewer.pk:
        return None
    if p.registration_status != RegistrationStatus.APPROVED:
        return None
    return p


def should_blur_photos(viewer: Profile) -> bool:
    """Hommes free : blur jusqu'à abo (règle freemium historique)."""
    if viewer.gender != Gender.MALE:
        return False
    return not viewer.has_active_subscription
