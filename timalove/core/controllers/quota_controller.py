"""Quotas freemium : messages, swipes / likes quotidiens, historique, likes reçus."""

from __future__ import annotations

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from core.controllers import site_settings_controller
from core.models import Message, Profile, Swipe
from core.models.choices import SwipeAction

LIKE_Q = Q(is_like=True) | Q(is_super_like=True)
UPGRADE_PATH = "/profil/?tab=settings&section=subscription"

SWIPE_LIMIT_MSG = "Limite de {n} profils par jour atteinte. Passez Premium pour continuer."
LIKE_LIMIT_MSG = "Limite de {n} likes par jour atteinte. Passez Premium pour continuer."
MESSAGE_LIMIT_CODE = "message_limit"
MESSAGE_LIMIT_MSG = (
    "Limite de {n} messages gratuits atteinte (toutes discussions confondues). "
    "Passez Premium pour continuer."
)


def is_freemium(profile: Profile | None) -> bool:
    if not getattr(settings, "FREEMIUM_LIMITS_ENABLED", True):
        return False
    if profile is None:
        return False
    if getattr(profile, "is_admin", False):
        return False
    return not profile.has_active_subscription


def upgrade_path() -> str:
    return UPGRADE_PATH


def messages_limit() -> int:
    return max(0, int(site_settings_controller.get("free_messages_limit", 3) or 3))


def swipes_per_day_limit() -> int:
    default = getattr(settings, "FREE_SWIPES_PER_DAY_DEFAULT", 20)
    return max(0, int(site_settings_controller.get("free_swipes_per_day", default) or default))


def likes_per_day_limit() -> int:
    default = getattr(settings, "FREE_LIKES_PER_DAY_DEFAULT", 10)
    return max(0, int(site_settings_controller.get("free_likes_per_day", default) or default))


def likes_visible_limit() -> int:
    default = getattr(settings, "FREE_LIKES_VISIBLE_DEFAULT", 1)
    return max(0, int(site_settings_controller.get("free_likes_visible", default) or default))


def day_start():
    return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)


def messages_sent_count(profile: Profile) -> int:
    return Message.objects.filter(sender=profile).count()


def messages_remaining(profile: Profile) -> int | None:
    if not is_freemium(profile):
        return None
    return max(0, messages_limit() - messages_sent_count(profile))


def daily_swipe_count(profile: Profile) -> int:
    return Swipe.objects.filter(swiper=profile, created_at__gte=day_start()).count()


def daily_like_count(profile: Profile) -> int:
    return (
        Swipe.objects.filter(swiper=profile, created_at__gte=day_start())
        .filter(LIKE_Q)
        .count()
    )


def history_locked(profile: Profile | None) -> bool:
    return False


def check_message(profile: Profile) -> tuple[bool, str]:
    if not is_freemium(profile):
        return True, ""
    if messages_sent_count(profile) >= messages_limit():
        return False, MESSAGE_LIMIT_MSG.format(n=messages_limit())
    return True, ""


def limit_code_for(profile: Profile) -> str:
    ok, _ = check_message(profile)
    return "" if ok else MESSAGE_LIMIT_CODE


def check_swipe(swiper: Profile, swiped_id, action: str) -> tuple[bool, str, str]:
    """Retourne (ok, message, code)."""
    if not is_freemium(swiper):
        return True, "", ""

    action = action if action in SwipeAction.values else SwipeAction.PASS
    existing = Swipe.objects.filter(swiper=swiper, swiped_id=swiped_id).first()
    already_like = bool(existing and (existing.is_like or existing.is_super_like))
    already_super = bool(existing and existing.is_super_like)
    counted_today = bool(existing and existing.created_at >= day_start())
    wants_like = action in {SwipeAction.LIKE, SwipeAction.SUPER_LIKE}

    if action == SwipeAction.LIKE and already_like:
        return True, "", ""
    if action == SwipeAction.SUPER_LIKE and already_super:
        return True, "", ""
    if action == SwipeAction.PASS and counted_today:
        return True, "", ""

    if not counted_today and daily_swipe_count(swiper) >= swipes_per_day_limit():
        return False, SWIPE_LIMIT_MSG.format(n=swipes_per_day_limit()), "swipe_limit"
    if wants_like and not already_like and daily_like_count(swiper) >= likes_per_day_limit():
        return False, LIKE_LIMIT_MSG.format(n=likes_per_day_limit()), "like_limit"
    return True, "", ""


def snapshot(profile: Profile | None) -> dict:
    if not profile or not is_freemium(profile):
        return {
            "is_freemium": False,
            "swipes_left": None,
            "likes_left": None,
            "messages_left": None,
            "history_locked": False,
            "likes_visible": None,
            "upgrade_path": UPGRADE_PATH,
        }
    return {
        "is_freemium": True,
        "swipes_left": max(0, swipes_per_day_limit() - daily_swipe_count(profile)),
        "likes_left": max(0, likes_per_day_limit() - daily_like_count(profile)),
        "messages_left": messages_remaining(profile),
        "history_locked": False,
        "likes_visible": likes_visible_limit(),
        "upgrade_path": UPGRADE_PATH,
    }
