"""Site settings — lecture / écriture KV."""

from __future__ import annotations

from typing import Any

from django.conf import settings

DEFAULTS: dict[str, Any] = {
    "registrations_enabled": True,
    "free_messages_limit": getattr(settings, "FREE_MESSAGES_LIMIT_DEFAULT", 3),
    "subscription_prices": {
        "premium_10d": 6000,
        "premium_1m": 10000,
        "premium_2m": 18000,
        "vip_1m": 25000,
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


def get(key: str, default: Any = None) -> Any:
    from core.models import SiteSetting

    try:
        row = SiteSetting.objects.filter(key=key).first()
        if row is None:
            return DEFAULTS.get(key, default)
        return row.value
    except Exception:
        return DEFAULTS.get(key, default)


def set_value(key: str, value: Any) -> None:
    from core.models import SiteSetting

    SiteSetting.objects.update_or_create(key=key, defaults={"value": value})


def get_all() -> dict[str, Any]:
    data = dict(DEFAULTS)
    from core.models import SiteSetting

    for row in SiteSetting.objects.all():
        data[row.key] = row.value
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
    return created


def disable_maintenance() -> None:
    set_value("maintenance_mode", False)