"""Site settings — lecture / écriture KV."""

from __future__ import annotations

from typing import Any

from django.conf import settings

DEFAULTS: dict[str, Any] = {
    "registrations_enabled": True,
    "free_messages_limit": getattr(settings, "FREE_MESSAGES_LIMIT_DEFAULT", 5),
    "free_swipes_per_day": getattr(settings, "FREE_SWIPES_PER_DAY_DEFAULT", 20),
    "free_likes_per_day": getattr(settings, "FREE_LIKES_PER_DAY_DEFAULT", 20),
    "free_likes_visible": getattr(settings, "FREE_LIKES_VISIBLE_DEFAULT", 2),
    "free_history_visible": getattr(settings, "FREE_HISTORY_VISIBLE_DEFAULT", 5),
    "subscription_prices": {
        "premium_1m": 2990,
        "vip_1m": 8000,
        "pass_femme": 2000,
        "journee_amoureuse": 1000,
        "pass_amour": 4500,
        "eternite": 29900,
        "premium_10d": 6000,
        "premium_2m": 18000,
        "vip_2m": 32800,
        "vip_femme_1w": 5000,
    },
    "coaching_price_eur": 40,
    "email_notifications_enabled": True,
    "coaching_notification_email": "timaloveagence@gmail.com",
    "banned_words": [],
    "phone_masking_enabled": True,
    "whatsapp_number": "+33 6 13 03 14 55",
    "contact_email": "timaloveagence@gmail.com",
    "social_links": {
        "facebook": "",
        "instagram": "",
        "twitter": "",
        "youtube": "",
        "tiktok": "",
    },
    "maintenance_mode": False,
    "maintenance_message": "Maintenance en cours. Nous revenons très bientôt.",
}


def _as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on", "t"}
    return bool(value)


def _merged_subscription_prices(stored: Any) -> dict[str, int]:
    """Complète les clés manquantes (ex. import ancien) avec les tarifs par défaut."""
    merged: dict[str, int] = {}
    for key, value in (DEFAULTS.get("subscription_prices") or {}).items():
        try:
            merged[str(key)] = int(value)
        except (TypeError, ValueError):
            continue
    if isinstance(stored, dict):
        for key, value in stored.items():
            if value in (None, ""):
                continue
            try:
                merged[str(key)] = int(value)
            except (TypeError, ValueError):
                continue
    return merged


def get(key: str, default: Any = None) -> Any:
    from core.models import SiteSetting

    try:
        row = SiteSetting.objects.filter(key=key).first()
        value = DEFAULTS.get(key, default) if row is None else row.value
    except Exception:
        value = DEFAULTS.get(key, default)
    if key == "subscription_prices":
        return _merged_subscription_prices(value if isinstance(value, dict) else {})
    return value


def set_value(key: str, value: Any) -> None:
    from core.models import SiteSetting

    SiteSetting.objects.update_or_create(key=key, defaults={"value": value})


def get_all() -> dict[str, Any]:
    data = dict(DEFAULTS)
    from core.models import SiteSetting

    for row in SiteSetting.objects.all():
        if row.key == "subscription_prices":
            data[row.key] = _merged_subscription_prices(row.value)
        else:
            data[row.key] = row.value
    data["subscription_prices"] = _merged_subscription_prices(data.get("subscription_prices"))
    return data


def is_maintenance_mode() -> bool:
    return _as_bool(get("maintenance_mode", False), default=False)


def public_config() -> dict[str, Any]:
    return {
        "registrationsEnabled": _as_bool(get("registrations_enabled"), True),
        "subscriptionPrices": get("subscription_prices"),
        "coachingPriceEur": get("coaching_price_eur"),
        "whatsappNumber": get("whatsapp_number"),
        "contactEmail": get("contact_email"),
        "socialLinks": get("social_links"),
        "maintenanceMode": is_maintenance_mode(),
        "maintenanceMessage": get("maintenance_message"),
    }


def seed_defaults() -> int:
    from core.models import SiteSetting

    created = 0
    for key, value in DEFAULTS.items():
        _, was_created = SiteSetting.objects.get_or_create(key=key, defaults={"value": value})
        if was_created:
            created += 1
    # Normaliser les booléens éventuellement importés comme strings SQL
    for key in (
        "registrations_enabled",
        "email_notifications_enabled",
        "phone_masking_enabled",
        "maintenance_mode",
    ):
        row = SiteSetting.objects.filter(key=key).first()
        if row is not None and not isinstance(row.value, bool):
            row.value = _as_bool(row.value, DEFAULTS.get(key, False))
            row.save(update_fields=["value", "updated_at"])
    prices_row = SiteSetting.objects.filter(key="subscription_prices").first()
    stored = prices_row.value if prices_row is not None else {}
    merged = _merged_subscription_prices(stored)
    if merged != stored:
        set_value("subscription_prices", merged)
    return created


def disable_maintenance() -> None:
    set_value("maintenance_mode", False)