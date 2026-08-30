"""Quotas freemium : messages, swipes, likes, historique, likes reçus."""

from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from core.controllers import site_settings_controller
from core.models import Message, Profile, Swipe
from core.models.choices import Gender, SwipeAction

LIKE_Q = Q(is_like=True) | Q(is_super_like=True)
UPGRADE_PATH = "/profil/?tab=settings&section=subscription"

PERIOD_DAY = "day"
PERIOD_MONTH = "month"

MESSAGE_LIMIT_CODE = "message_limit"
HISTORY_LIMIT_MSG = "Passez au plan supérieur pour voir plus de profils dans votre historique."


def _as_bool(value: Any, default: bool = True) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "t"}
    return default


def _as_int(value: Any, default: int, *, minimum: int = 0, maximum: int = 9999) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def quota_settings() -> dict[str, Any]:
    from core.controllers import app_config_controller

    period_raw = str(site_settings_controller.get("quota_period", PERIOD_DAY) or PERIOD_DAY).strip().lower()
    period = PERIOD_MONTH if period_raw in {PERIOD_MONTH, "mois"} else PERIOD_DAY
    return {
        "enabled": app_config_controller.freemium_enabled(),
        "period": period,
        "period_label": "ce mois-ci" if period == PERIOD_MONTH else "aujourd’hui",
        "period_window": "par mois" if period == PERIOD_MONTH else "par jour",
        "messages_enabled": _as_bool(site_settings_controller.get("quota_messages_enabled"), True),
        "messages_limit": _as_int(
            site_settings_controller.get("free_messages_limit"),
            getattr(settings, "FREE_MESSAGES_LIMIT_DEFAULT", 5),
        ),
        "likes_enabled": _as_bool(site_settings_controller.get("quota_likes_enabled"), True),
        "likes_limit": _as_int(
            site_settings_controller.get("free_likes_per_day"),
            getattr(settings, "FREE_LIKES_PER_DAY_DEFAULT", 20),
        ),
        "swipes_enabled": _as_bool(site_settings_controller.get("quota_swipes_enabled"), True),
        "swipes_limit": _as_int(
            site_settings_controller.get("free_swipes_per_day"),
            getattr(settings, "FREE_SWIPES_PER_DAY_DEFAULT", 20),
        ),
        "likes_visible_enabled": _as_bool(
            site_settings_controller.get("quota_likes_visible_enabled"), True
        ),
        "likes_visible": _as_int(
            site_settings_controller.get("free_likes_visible"),
            getattr(settings, "FREE_LIKES_VISIBLE_DEFAULT", 2),
        ),
        "history_visible_enabled": _as_bool(
            site_settings_controller.get("quota_history_visible_enabled"), True
        ),
        "history_visible": _as_int(
            site_settings_controller.get("free_history_visible"),
            getattr(settings, "FREE_HISTORY_VISIBLE_DEFAULT", 5),
        ),
    }


def save_limits_from_post(post) -> dict[str, Any]:
    from core.controllers import app_config_controller

    period = (post.get("quota_period") or PERIOD_DAY).strip().lower()
    if period not in {PERIOD_DAY, PERIOD_MONTH}:
        period = PERIOD_DAY
    site_settings_controller.set_value("quota_period", period)
    site_settings_controller.set_value(
        "free_messages_limit", _as_int(post.get("free_messages_limit"), 5)
    )
    site_settings_controller.set_value(
        "free_swipes_per_day", _as_int(post.get("free_swipes_per_day"), 20)
    )
    site_settings_controller.set_value(
        "free_likes_per_day", _as_int(post.get("free_likes_per_day"), 20)
    )
    site_settings_controller.set_value(
        "free_likes_visible", _as_int(post.get("free_likes_visible"), 2)
    )
    site_settings_controller.set_value(
        "free_history_visible", _as_int(post.get("free_history_visible"), 5)
    )
    site_settings_controller.set_value(
        "quota_messages_enabled", post.get("quota_messages_enabled") == "on"
    )
    site_settings_controller.set_value(
        "quota_likes_enabled", post.get("quota_likes_enabled") == "on"
    )
    site_settings_controller.set_value(
        "quota_swipes_enabled", post.get("quota_swipes_enabled") == "on"
    )
    site_settings_controller.set_value(
        "quota_likes_visible_enabled", post.get("quota_likes_visible_enabled") == "on"
    )
    site_settings_controller.set_value(
        "quota_history_visible_enabled", post.get("quota_history_visible_enabled") == "on"
    )
    cfg = app_config_controller.get_app_config()
    cfg["freemium_limits_enabled"] = post.get("freemium_limits_enabled") == "on"
    app_config_controller.save_app_config(cfg)
    return quota_settings()


def is_freemium(profile: Profile | None) -> bool:
    from core.controllers import app_config_controller

    if not app_config_controller.freemium_enabled():
        return False
    if not getattr(settings, "FREEMIUM_LIMITS_ENABLED", True):
        return False
    if profile is None:
        return False
    if getattr(profile, "is_admin", False):
        return False
    if profile.gender == Gender.FEMALE:
        return False
    return not profile.has_active_subscription


def is_male_freemium(profile: Profile | None) -> bool:
    return bool(profile and is_freemium(profile) and profile.gender == Gender.MALE)


def upgrade_path() -> str:
    return UPGRADE_PATH


def messages_limit() -> int:
    return quota_settings()["messages_limit"]


def swipes_per_day_limit() -> int:
    return quota_settings()["swipes_limit"]


def likes_per_day_limit() -> int:
    return quota_settings()["likes_limit"]


def likes_visible_limit() -> int:
    return quota_settings()["likes_visible"]


def history_visible_limit() -> int:
    return quota_settings()["history_visible"]


def period_start():
    now = timezone.localtime()
    if quota_settings()["period"] == PERIOD_MONTH:
        return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def day_start():
    return period_start()


def messages_sent_count(profile: Profile) -> int:
    return Message.objects.filter(sender=profile, created_at__gte=period_start()).count()


def messages_remaining(profile: Profile) -> int | None:
    if not is_freemium(profile) or not quota_settings()["messages_enabled"]:
        return None
    return max(0, messages_limit() - messages_sent_count(profile))


def period_swipe_count(profile: Profile) -> int:
    return Swipe.objects.filter(swiper=profile, created_at__gte=period_start()).count()


def period_like_count(profile: Profile) -> int:
    return (
        Swipe.objects.filter(swiper=profile, created_at__gte=period_start())
        .filter(LIKE_Q)
        .count()
    )


def daily_swipe_count(profile: Profile) -> int:
    return period_swipe_count(profile)


def daily_like_count(profile: Profile) -> int:
    return period_like_count(profile)


def history_locked(profile: Profile | None) -> bool:
    """Historique partiellement visible — jamais verrouillé en entier."""
    return False


def history_limit_for(profile: Profile | None) -> int | None:
    if not is_male_freemium(profile):
        return None
    cfg = quota_settings()
    if not cfg["history_visible_enabled"]:
        return None
    return cfg["history_visible"]


def likes_visible_cap(profile: Profile | None) -> int | None:
    if not is_freemium(profile):
        return None
    cfg = quota_settings()
    if not cfg["likes_visible_enabled"]:
        return None
    return cfg["likes_visible"]


def check_message(profile: Profile) -> tuple[bool, str]:
    cfg = quota_settings()
    if not is_freemium(profile) or not cfg["messages_enabled"]:
        return True, ""
    limit = cfg["messages_limit"]
    if messages_sent_count(profile) >= limit:
        return False, (
            f"Limite de {limit} messages gratuits atteinte {cfg['period_label']}. "
            "Passez au plan supérieur pour continuer."
        )
    return True, ""


def limit_code_for(profile: Profile) -> str:
    ok, _ = check_message(profile)
    return "" if ok else MESSAGE_LIMIT_CODE


def check_swipe(swiper: Profile, swiped_id, action: str) -> tuple[bool, str, str]:
    """Retourne (ok, message, code)."""
    if not is_freemium(swiper):
        return True, "", ""

    cfg = quota_settings()
    action = action if action in SwipeAction.values else SwipeAction.PASS
    existing = Swipe.objects.filter(swiper=swiper, swiped_id=swiped_id).first()
    already_like = bool(existing and (existing.is_like or existing.is_super_like))
    already_super = bool(existing and existing.is_super_like)
    counted_in_period = bool(existing and existing.created_at >= period_start())
    wants_like = action in {SwipeAction.LIKE, SwipeAction.SUPER_LIKE}

    if action == SwipeAction.LIKE and already_like:
        return True, "", ""
    if action == SwipeAction.SUPER_LIKE and already_super:
        return True, "", ""
    if action == SwipeAction.PASS and counted_in_period:
        return True, "", ""

    if (
        cfg["likes_enabled"]
        and wants_like
        and not already_like
        and period_like_count(swiper) >= cfg["likes_limit"]
    ):
        return (
            False,
            f"Limite de {cfg['likes_limit']} likes {cfg['period_window']} atteinte. Passez au plan supérieur pour continuer.",
            "like_limit",
        )
    return True, "", ""


def snapshot(profile: Profile | None) -> dict:
    cfg = quota_settings()
    if not profile or not is_freemium(profile):
        return {
            "is_freemium": False,
            "swipes_left": None,
            "likes_left": None,
            "messages_left": None,
            "history_locked": False,
            "history_visible": None,
            "likes_visible": None,
            "period": cfg["period"],
            "period_label": cfg["period_label"],
            "show_explorer_quota": False,
            "upgrade_path": UPGRADE_PATH,
        }
    swipes_left = (
        max(0, cfg["swipes_limit"] - period_swipe_count(profile)) if cfg["swipes_enabled"] else None
    )
    likes_left = (
        max(0, cfg["likes_limit"] - period_like_count(profile)) if cfg["likes_enabled"] else None
    )
    return {
        "is_freemium": True,
        "swipes_left": swipes_left,
        "likes_left": likes_left,
        "messages_left": messages_remaining(profile),
        "history_locked": False,
        "history_visible": history_limit_for(profile),
        "likes_visible": likes_visible_cap(profile),
        "period": cfg["period"],
        "period_label": cfg["period_label"],
        "show_explorer_quota": swipes_left is not None or likes_left is not None,
        "upgrade_path": UPGRADE_PATH,
    }
