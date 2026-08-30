"""Discover feed."""

from __future__ import annotations

from django.db.models import Exists, OuterRef, Q

from core.controllers import swipe_controller
from core.models import BlockedUser, Profile
from core.models.choices import Gender, RegistrationStatus, UserRole


def opposite_gender(gender: str) -> str:
    return Gender.FEMALE if gender == Gender.MALE else Gender.MALE


def feed_for(viewer: Profile, limit: int = 20) -> list[Profile]:
    blocked_by_me = BlockedUser.objects.filter(blocker=viewer, blocked_id=OuterRef("pk"))
    blocked_me = BlockedUser.objects.filter(blocker_id=OuterRef("pk"), blocked=viewer)

    qs = (
        Profile.objects.filter(
            registration_status=RegistrationStatus.APPROVED,
            is_hidden=False,
            is_shadowbanned=False,
            role=UserRole.MEMBER,
        )
        .exclude(pk=viewer.pk)
        .exclude(banned_at__isnull=False)
        .annotate(is_blocked=Exists(blocked_by_me) | Exists(blocked_me))
        .filter(is_blocked=False)
    )
    from core.controllers.profile_controller import apply_discover_filters

    qs = apply_discover_filters(qs, viewer)
    qs = swipe_controller.apply_feed_exclusions(qs, viewer)
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
    from core.controllers import quota_controller

    if not quota_controller.is_freemium(viewer):
        return False
    if viewer.gender != Gender.MALE:
        return False
    return True
