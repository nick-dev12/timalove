"""Site settings — lecture / écriture KV."""

from __future__ import annotations

from typing import Any

from django.conf import settings

DEFAULT_PLAN_FEATURES: dict[str, list[str]] = {
    "premium": [
        "Messagerie illimitée",
        "5× plus visible dans l'explorer",
        "Historique et likes reçus complets",
    ],
    "vip": [
        "Messagerie illimitée",
        "Liker n'importe quel profil",
        "Accepter ou bloquer une discussion",
        "Profils complets (> 70 %) en priorité",
        "10× plus visible dans l'explorer",
        "Badge VIP doré",
    ],
    "pass_femme": [
        "Tous les avantages Premium et VIP",
        "Suggestions de profils ×10",
        "Badge doré",
        "Photos et audio illimités",
        "Accepter ou refuser une discussion",
    ],
}

DEFAULT_IN_APP_PACKS: dict[str, dict[str, Any]] = {
    "boost_7d": {
        "label": "Boost 7 jours",
        "description": "Profil mis en avant pendant 7 jours",
        "price": 5000,
        "pack_type": "boost",
        "quantity": 1,
        "duration_days": 7,
        "active": True,
    },
    "boost_3pack": {
        "label": "Pack 3 Boosts",
        "description": "3 boosts de 7 jours chacun",
        "price": 12000,
        "pack_type": "boost",
        "quantity": 3,
        "duration_days": 7,
        "active": True,
    },
    "super_like_5": {
        "label": "5 Super-Likes",
        "description": "Pack de 5 super-likes",
        "price": 2500,
        "pack_type": "super_like",
        "quantity": 5,
        "duration_days": 0,
        "active": True,
    },
    "super_like_15": {
        "label": "15 Super-Likes",
        "description": "Pack de 15 super-likes",
        "price": 6000,
        "pack_type": "super_like",
        "quantity": 15,
        "duration_days": 0,
        "active": True,
    },
    "rewind_3": {
        "label": "3 Rewinds",
        "description": "Revenir en arrière sur 3 profils passés",
        "price": 1500,
        "pack_type": "rewind",
        "quantity": 3,
        "duration_days": 0,
        "active": True,
    },
    "rewind_10": {
        "label": "10 Rewinds",
        "description": "Revenir en arrière sur 10 profils passés",
        "price": 4000,
        "pack_type": "rewind",
        "quantity": 10,
        "duration_days": 0,
        "active": True,
    },
}

PACK_TYPES = ("boost", "super_like", "rewind")
PLAN_AUDIENCES = ("male", "female", "all")
PLAN_TIER_KINDS = ("premium", "vip", "pass_femme")

DEFAULT_PLAN_DURATION_DAYS: dict[str, int] = {
    "journee_amoureuse": 1,
    "pass_amour": 30,
    "eternite": 36500,
    "premium_10d": 10,
    "premium_1m": 30,
    "premium_2m": 60,
    "vip_1m": 30,
    "vip_2m": 60,
    "vip_femme_1w": 7,
    "pass_femme": 15,
}

DEFAULT_SUBSCRIPTION_PLANS: dict[str, dict[str, Any]] = {
    "premium_1m": {
        "label": "Premium",
        "price": 2990,
        "duration_label": "1 mois",
        "duration_days": 30,
        "tier_kind": "premium",
        "active": True,
        "audience": "male",
        "is_featured": True,
        "badge": "Le plus populaire",
        "features": DEFAULT_PLAN_FEATURES["premium"],
    },
    "vip_1m": {
        "label": "VIP",
        "price": 8000,
        "duration_label": "1 mois",
        "duration_days": 30,
        "tier_kind": "vip",
        "active": True,
        "audience": "male",
        "is_featured": False,
        "badge": "",
        "features": DEFAULT_PLAN_FEATURES["vip"],
    },
    "pass_femme": {
        "label": "Accès Premium VIP",
        "price": 2000,
        "duration_label": "15 jours",
        "duration_days": 15,
        "tier_kind": "pass_femme",
        "active": True,
        "audience": "female",
        "is_featured": True,
        "badge": "Offre femmes",
        "features": DEFAULT_PLAN_FEATURES["pass_femme"],
    },
}

DEFAULTS: dict[str, Any] = {
    "registrations_enabled": True,
    "free_messages_limit": getattr(settings, "FREE_MESSAGES_LIMIT_DEFAULT", 5),
    "free_swipes_per_day": getattr(settings, "FREE_SWIPES_PER_DAY_DEFAULT", 20),
    "free_likes_per_day": getattr(settings, "FREE_LIKES_PER_DAY_DEFAULT", 20),
    "free_likes_visible": getattr(settings, "FREE_LIKES_VISIBLE_DEFAULT", 2),
    "free_history_visible": getattr(settings, "FREE_HISTORY_VISIBLE_DEFAULT", 5),
    "quota_period": "day",
    "quota_messages_enabled": True,
    "quota_likes_enabled": True,
    "quota_swipes_enabled": True,
    "quota_likes_visible_enabled": True,
    "quota_history_visible_enabled": True,
    "subscription_plans": DEFAULT_SUBSCRIPTION_PLANS,
    "in_app_packs": DEFAULT_IN_APP_PACKS,
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
    "admin_security": {"require_2fa": False},
    "app_config": {
        "default_search_radius_km": 50,
        "max_search_radius_km": 200,
        "video_chat_enabled": False,
        "text_messages_enabled": True,
        "voice_messages_enabled": True,
        "image_messages_enabled": True,
        "voice_call_enabled": True,
        "selfie_verification_enabled": False,
        "freemium_limits_enabled": True,
        "force_update_enabled": False,
        "force_update_ios": "1.0.0",
        "force_update_android": "1.0.0",
        "force_update_web": "1.0.0",
        "force_update_message": "Une mise à jour de l'application est requise pour continuer.",
        "force_update_url_ios": "https://apps.apple.com/",
        "force_update_url_android": "https://play.google.com/store",
    },
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


def _infer_tier_kind(plan_id: str) -> str:
    if plan_id in {"pass_femme", "vip_femme_1w"}:
        return "pass_femme"
    if "vip" in plan_id:
        return "vip"
    return "premium"


def _default_duration_days(plan_id: str) -> int:
    return int(DEFAULT_PLAN_DURATION_DAYS.get(plan_id, 30))


def _parse_features(raw: Any, tier_kind: str, base: list[str] | None = None) -> list[str]:
    if isinstance(raw, list):
        items = [str(item).strip() for item in raw if str(item).strip()]
        if items:
            return items
    if isinstance(raw, str) and raw.strip():
        items = [line.strip() for line in raw.replace("\r", "").split("\n") if line.strip()]
        if items:
            return items
    if base:
        return list(base)
    return list(DEFAULT_PLAN_FEATURES.get(tier_kind, DEFAULT_PLAN_FEATURES["premium"]))


def _normalize_plan_meta(raw: dict[str, Any], plan_id: str, base: dict[str, Any] | None = None) -> dict[str, Any]:
    base = dict(base or {})
    label = str(raw.get("label") or base.get("label") or plan_id).strip()
    duration = str(raw.get("duration_label") or base.get("duration_label") or "1 mois").strip()
    try:
        price = int(raw.get("price", base.get("price", 0)))
    except (TypeError, ValueError):
        price = int(base.get("price", 0))
    try:
        duration_days = int(raw.get("duration_days", base.get("duration_days", _default_duration_days(plan_id))))
    except (TypeError, ValueError):
        duration_days = _default_duration_days(plan_id)
    active = _as_bool(raw.get("active", base.get("active", True)), True)
    audience = str(raw.get("audience") or base.get("audience") or "all")
    if audience not in PLAN_AUDIENCES:
        audience = "all"
    tier_kind = str(raw.get("tier_kind") or base.get("tier_kind") or _infer_tier_kind(plan_id))
    if tier_kind not in PLAN_TIER_KINDS:
        tier_kind = _infer_tier_kind(plan_id)
    is_featured = _as_bool(raw.get("is_featured", base.get("is_featured", False)), False)
    badge = str(raw.get("badge") or base.get("badge") or "").strip()
    features = _parse_features(
        raw.get("features"),
        tier_kind,
        base.get("features") if base else None,
    )
    return {
        "label": label,
        "price": max(0, price),
        "duration_label": duration,
        "duration_days": max(1, duration_days),
        "tier_kind": tier_kind,
        "active": active,
        "audience": audience,
        "is_featured": is_featured,
        "badge": badge,
        "features": features,
    }


def _merged_subscription_plans(stored: Any) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for key, meta in DEFAULT_SUBSCRIPTION_PLANS.items():
        merged[key] = _normalize_plan_meta(meta, key, meta)
    if isinstance(stored, dict):
        for key, raw in stored.items():
            plan_id = str(key)
            if not isinstance(raw, dict):
                continue
            base = merged.get(plan_id, DEFAULT_SUBSCRIPTION_PLANS.get(plan_id, {}))
            merged[plan_id] = _normalize_plan_meta(raw, plan_id, base)
    for plan_id, meta in merged.items():
        default_meta = DEFAULT_SUBSCRIPTION_PLANS.get(plan_id)
        if not default_meta:
            continue
        kind = meta.get("tier_kind") or default_meta.get("tier_kind") or "premium"
        meta["features"] = list(DEFAULT_PLAN_FEATURES.get(kind, DEFAULT_PLAN_FEATURES["premium"]))
        meta["label"] = default_meta["label"]
        meta["audience"] = default_meta["audience"]
        meta["duration_days"] = default_meta["duration_days"]
        meta["duration_label"] = default_meta["duration_label"]
    return merged


def _merged_subscription_prices(stored: Any) -> dict[str, int]:
    """Complète les clés manquantes (ex. import ancien) avec les tarifs par défaut."""
    plans = get_subscription_plans()
    merged: dict[str, int] = {plan_id: int(meta.get("price", 0)) for plan_id, meta in plans.items()}
    for key, value in (DEFAULTS.get("subscription_prices") or {}).items():
        try:
            merged.setdefault(str(key), int(value))
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


def get_subscription_plans() -> dict[str, dict[str, Any]]:
    from core.models import SiteSetting

    try:
        row = SiteSetting.objects.filter(key="subscription_plans").first()
        stored = row.value if row is not None else DEFAULT_SUBSCRIPTION_PLANS
    except Exception:
        stored = DEFAULT_SUBSCRIPTION_PLANS
    return _merged_subscription_plans(stored)


def save_subscription_plans(plans: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged = _merged_subscription_plans(plans)
    set_value("subscription_plans", merged)
    prices = {plan_id: int(meta.get("price", 0)) for plan_id, meta in merged.items()}
    set_value("subscription_prices", prices)
    return merged


def active_subscription_plans_list() -> list[dict[str, Any]]:
    return [
        {"id": plan_id, **meta}
        for plan_id, meta in get_subscription_plans().items()
        if meta.get("active", True)
    ]


def subscription_tier_choices_for_admin() -> list[tuple[str, str]]:
    from core.models.choices import SubscriptionTier

    return [(tier.value, tier.label) for tier in SubscriptionTier if tier != SubscriptionTier.FREE]


def validate_plan_id(plan_id: str) -> str:
    import re

    from core.models.choices import SubscriptionTier

    normalized = (plan_id or "").strip().lower()
    if not re.match(r"^[a-z][a-z0-9_]{1,29}$", normalized):
        raise ValueError("Identifiant de plan invalide.")
    if normalized not in SubscriptionTier.values:
        raise ValueError("Identifiant non reconnu. Choisissez une offre prédéfinie.")
    return normalized


def parse_plans_from_post(post) -> dict[str, dict[str, Any]]:
    current = get_subscription_plans()
    updated = dict(current)
    for plan_id in post.getlist("plan_id"):
        if plan_id not in updated:
            continue
        updated[plan_id] = {
            "label": post.get(f"label_{plan_id}", ""),
            "price": post.get(f"price_{plan_id}"),
            "duration_label": post.get(f"duration_{plan_id}", ""),
            "duration_days": post.get(f"duration_days_{plan_id}"),
            "tier_kind": post.get(f"tier_kind_{plan_id}", ""),
            "audience": post.get(f"audience_{plan_id}", ""),
            "active": post.get(f"active_{plan_id}") == "on",
            "is_featured": post.get(f"featured_{plan_id}") == "on",
            "badge": post.get(f"badge_{plan_id}", ""),
            "features": post.get(f"features_{plan_id}", ""),
        }
    return updated


def add_subscription_plan(plan_id: str, meta: dict[str, Any]) -> dict[str, dict[str, Any]]:
    normalized_id = validate_plan_id(plan_id)
    plans = get_subscription_plans()
    if normalized_id in plans:
        raise ValueError("Ce plan est déjà configuré.")
    plans[normalized_id] = _normalize_plan_meta(meta, normalized_id, {})
    return save_subscription_plans(plans)


def remove_subscription_plan(plan_id: str) -> dict[str, dict[str, Any]]:
    plans = get_subscription_plans()
    if plan_id not in plans:
        raise ValueError("Plan introuvable.")
    if len(plans) <= 1:
        raise ValueError("Impossible de supprimer le dernier plan.")
    del plans[plan_id]
    return save_subscription_plans(plans)


def duration_days_for_plan(plan_id: str) -> int:
    meta = get_subscription_plans().get(plan_id, {})
    try:
        return max(1, int(meta.get("duration_days", _default_duration_days(plan_id))))
    except (TypeError, ValueError):
        return _default_duration_days(plan_id)


def _normalize_pack_meta(raw: dict[str, Any], pack_id: str, base: dict[str, Any] | None = None) -> dict[str, Any]:
    base = dict(base or {})
    label = str(raw.get("label") or base.get("label") or pack_id).strip()
    description = str(raw.get("description") or base.get("description") or "").strip()
    try:
        price = int(raw.get("price", base.get("price", 0)))
    except (TypeError, ValueError):
        price = int(base.get("price", 0))
    try:
        quantity = int(raw.get("quantity", base.get("quantity", 1)))
    except (TypeError, ValueError):
        quantity = int(base.get("quantity", 1))
    try:
        duration_days = int(raw.get("duration_days", base.get("duration_days", 0)))
    except (TypeError, ValueError):
        duration_days = int(base.get("duration_days", 0))
    pack_type = str(raw.get("pack_type") or base.get("pack_type") or "boost")
    if pack_type not in PACK_TYPES:
        pack_type = "boost"
    active = _as_bool(raw.get("active", base.get("active", True)), True)
    return {
        "label": label,
        "description": description,
        "price": max(0, price),
        "pack_type": pack_type,
        "quantity": max(1, quantity),
        "duration_days": max(0, duration_days),
        "active": active,
    }


def _merged_in_app_packs(stored: Any) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for key, meta in DEFAULT_IN_APP_PACKS.items():
        merged[key] = _normalize_pack_meta(meta, key, meta)
    if isinstance(stored, dict):
        for key, raw in stored.items():
            pack_id = str(key)
            if not isinstance(raw, dict):
                continue
            base = merged.get(pack_id, DEFAULT_IN_APP_PACKS.get(pack_id, {}))
            merged[pack_id] = _normalize_pack_meta(raw, pack_id, base)
    return merged


def get_in_app_packs() -> dict[str, dict[str, Any]]:
    from core.models import SiteSetting

    try:
        row = SiteSetting.objects.filter(key="in_app_packs").first()
        stored = row.value if row is not None else DEFAULT_IN_APP_PACKS
    except Exception:
        stored = DEFAULT_IN_APP_PACKS
    return _merged_in_app_packs(stored)


def save_in_app_packs(packs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    merged = _merged_in_app_packs(packs)
    set_value("in_app_packs", merged)
    return merged


def validate_pack_id(pack_id: str) -> str:
    import re

    normalized = (pack_id or "").strip().lower()
    if not re.match(r"^[a-z][a-z0-9_]{1,29}$", normalized):
        raise ValueError("Identifiant de pack invalide (lettres, chiffres, underscore).")
    return normalized


def add_in_app_pack(pack_id: str, meta: dict[str, Any]) -> dict[str, dict[str, Any]]:
    normalized_id = validate_pack_id(pack_id)
    packs = get_in_app_packs()
    if normalized_id in packs:
        raise ValueError("Ce pack est déjà configuré.")
    packs[normalized_id] = _normalize_pack_meta(meta, normalized_id, {})
    return save_in_app_packs(packs)


def remove_in_app_pack(pack_id: str) -> dict[str, dict[str, Any]]:
    packs = get_in_app_packs()
    if pack_id in DEFAULT_IN_APP_PACKS:
        raise ValueError("Pack catalogue : désactivez-le plutôt que de le supprimer.")
    if pack_id not in packs:
        raise ValueError("Pack introuvable.")
    del packs[pack_id]
    return save_in_app_packs(packs)


def parse_packs_from_post(post) -> dict[str, dict[str, Any]]:
    current = get_in_app_packs()
    updated = dict(current)
    for pack_id in post.getlist("pack_id"):
        if pack_id not in updated:
            continue
        updated[pack_id] = {
            "label": post.get(f"pack_label_{pack_id}", ""),
            "description": post.get(f"pack_desc_{pack_id}", ""),
            "price": post.get(f"pack_price_{pack_id}"),
            "pack_type": post.get(f"pack_type_{pack_id}", ""),
            "quantity": post.get(f"pack_qty_{pack_id}"),
            "duration_days": post.get(f"pack_days_{pack_id}"),
            "active": post.get(f"pack_active_{pack_id}") == "on",
        }
    return updated


def default_boost_pack_price() -> int:
    packs = get_in_app_packs()
    for meta in packs.values():
        if meta.get("pack_type") == "boost" and meta.get("active", True):
            return int(meta.get("price", 5000))
    return 5000


def boost_pack_duration_days() -> int:
    packs = get_in_app_packs()
    for meta in packs.values():
        if meta.get("pack_type") == "boost" and meta.get("active", True):
            return int(meta.get("duration_days", 7) or 7)
    return 7


def get(key: str, default: Any = None) -> Any:
    from core.models import SiteSetting

    try:
        row = SiteSetting.objects.filter(key=key).first()
        value = DEFAULTS.get(key, default) if row is None else row.value
    except Exception:
        value = DEFAULTS.get(key, default)
    if key == "subscription_plans":
        return _merged_subscription_plans(value if isinstance(value, dict) else {})
    if key == "subscription_prices":
        plan_prices = {
            plan_id: int(meta.get("price", 0)) for plan_id, meta in get_subscription_plans().items()
        }
        stored_prices = _merged_subscription_prices(value if isinstance(value, dict) else {})
        return {**plan_prices, **stored_prices}
    if key == "in_app_packs":
        return get_in_app_packs()
    return value


def set_value(key: str, value: Any) -> None:
    from core.models import SiteSetting

    SiteSetting.objects.update_or_create(key=key, defaults={"value": value})


def save_maintenance_from_post(post) -> dict[str, Any]:
    maintenance = post.get("maintenance_mode") == "on"
    message = str(post.get("maintenance_message") or "").strip()
    set_value("maintenance_mode", maintenance)
    set_value("maintenance_message", message)
    return {"maintenance_mode": maintenance, "maintenance_message": message}


def save_registrations_from_post(post) -> bool:
    enabled = post.get("registrations_enabled") == "on"
    set_value("registrations_enabled", enabled)
    return enabled


def get_all() -> dict[str, Any]:
    data = dict(DEFAULTS)
    from core.models import SiteSetting

    for row in SiteSetting.objects.all():
        if row.key == "subscription_plans":
            data[row.key] = _merged_subscription_plans(row.value)
        elif row.key == "subscription_prices":
            data[row.key] = _merged_subscription_prices(row.value)
        else:
            data[row.key] = row.value
    data["subscription_plans"] = get_subscription_plans()
    data["subscription_prices"] = get("subscription_prices")
    return data


def is_maintenance_mode() -> bool:
    return _as_bool(get("maintenance_mode", False), default=False)


def public_config() -> dict[str, Any]:
    from core.controllers import app_config_controller

    return {
        "registrationsEnabled": _as_bool(get("registrations_enabled"), True),
        "subscriptionPrices": get("subscription_prices"),
        "inAppPacks": {
            pack_id: meta
            for pack_id, meta in get_in_app_packs().items()
            if meta.get("active", True)
        },
        "appConfig": app_config_controller.public_app_config(),
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
    plans_row = SiteSetting.objects.filter(key="subscription_plans").first()
    merged_plans = _merged_subscription_plans(plans_row.value if plans_row is not None else {})
    if plans_row is None or merged_plans != plans_row.value:
        set_value("subscription_plans", merged_plans)
    prices_row = SiteSetting.objects.filter(key="subscription_prices").first()
    stored_prices = prices_row.value if prices_row is not None else {}
    final_prices = _merged_subscription_prices(stored_prices if isinstance(stored_prices, dict) else {})
    for plan_id, meta in merged_plans.items():
        final_prices.setdefault(plan_id, int(meta.get("price", 0)))
    if final_prices != (stored_prices if isinstance(stored_prices, dict) else {}):
        set_value("subscription_prices", final_prices)
    packs_row = SiteSetting.objects.filter(key="in_app_packs").first()
    merged_packs = _merged_in_app_packs(packs_row.value if packs_row is not None else {})
    if packs_row is None or merged_packs != packs_row.value:
        set_value("in_app_packs", merged_packs)
    app_row = SiteSetting.objects.filter(key="app_config").first()
    from core.controllers import app_config_controller

    merged_app = app_config_controller.get_app_config()
    if app_row is None or app_row.value != merged_app:
        set_value("app_config", merged_app)
    return created


def disable_maintenance() -> None:
    set_value("maintenance_mode", False)