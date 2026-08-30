"""Configuration globale de l'application — algorithmes, fonctionnalités, système."""

from __future__ import annotations

from typing import Any

DEFAULT_APP_CONFIG: dict[str, Any] = {
    "default_search_radius_km": 50,
    "max_search_radius_km": 200,
    "video_chat_enabled": False,
    "text_messages_enabled": True,
    "voice_messages_enabled": True,
    "image_messages_enabled": True,
    "voice_call_enabled": True,
    "selfie_verification_enabled": False,
    "freemium_limits_enabled": True,
    "explorer_search_enabled": True,
    "history_search_enabled": True,
    "messages_search_enabled": True,
    "force_update_enabled": False,
    "force_update_ios": "1.0.0",
    "force_update_android": "1.0.0",
    "force_update_web": "1.0.0",
    "force_update_message": "Une mise à jour de l'application est requise pour continuer.",
    "force_update_url_ios": "https://apps.apple.com/",
    "force_update_url_android": "https://play.google.com/store",
}

FEATURE_BOOL_KEYS = (
    "video_chat_enabled",
    "text_messages_enabled",
    "voice_messages_enabled",
    "image_messages_enabled",
    "voice_call_enabled",
    "selfie_verification_enabled",
    "explorer_search_enabled",
    "history_search_enabled",
    "messages_search_enabled",
    "freemium_limits_enabled",
    "force_update_enabled",
)

FORCE_UPDATE_STR_KEYS = (
    "force_update_ios",
    "force_update_android",
    "force_update_web",
    "force_update_message",
    "force_update_url_ios",
    "force_update_url_android",
)


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


def _as_int(value: Any, default: int, *, minimum: int | None = None, maximum: int | None = None) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = default
    if minimum is not None:
        number = max(minimum, number)
    if maximum is not None:
        number = min(maximum, number)
    return number


def get_app_config() -> dict[str, Any]:
    from core.controllers import site_settings_controller

    stored = site_settings_controller.get("app_config") or {}
    if not isinstance(stored, dict):
        stored = {}
    merged = dict(DEFAULT_APP_CONFIG)
    merged.update(stored)
    merged["default_search_radius_km"] = _as_int(
        merged.get("default_search_radius_km"), DEFAULT_APP_CONFIG["default_search_radius_km"], minimum=1, maximum=500
    )
    merged["max_search_radius_km"] = _as_int(
        merged.get("max_search_radius_km"), DEFAULT_APP_CONFIG["max_search_radius_km"], minimum=1, maximum=1000
    )
    if merged["default_search_radius_km"] > merged["max_search_radius_km"]:
        merged["default_search_radius_km"] = merged["max_search_radius_km"]
    if "voice_messages_enabled" not in stored and "voice_call_enabled" in stored:
        merged["voice_messages_enabled"] = stored.get("voice_call_enabled")
    for key in FEATURE_BOOL_KEYS:
        merged[key] = _as_bool(merged.get(key), DEFAULT_APP_CONFIG[key])
    merged["voice_call_enabled"] = merged["voice_messages_enabled"]
    for key in FORCE_UPDATE_STR_KEYS:
        merged[key] = str(merged.get(key) or DEFAULT_APP_CONFIG.get(key, "")).strip()
    return merged


def save_app_config(data: dict) -> dict[str, Any]:
    from core.controllers import site_settings_controller

    config = get_app_config()
    if "default_search_radius_km" in data:
        config["default_search_radius_km"] = _as_int(
            data.get("default_search_radius_km"), config["default_search_radius_km"], minimum=1, maximum=500
        )
    if "max_search_radius_km" in data:
        config["max_search_radius_km"] = _as_int(
            data.get("max_search_radius_km"), config["max_search_radius_km"], minimum=1, maximum=1000
        )
    if config["default_search_radius_km"] > config["max_search_radius_km"]:
        config["default_search_radius_km"] = config["max_search_radius_km"]
    for key in FEATURE_BOOL_KEYS:
        if key in data:
            config[key] = _as_bool(data.get(key), config[key])
    if "voice_messages_enabled" in data:
        config["voice_call_enabled"] = config["voice_messages_enabled"]
    elif "voice_call_enabled" in data:
        config["voice_messages_enabled"] = config["voice_call_enabled"]
    for key in FORCE_UPDATE_STR_KEYS:
        if key in data:
            config[key] = str(data.get(key) or config.get(key, "")).strip()
    site_settings_controller.set_value("app_config", config)
    return config


def parse_config_from_post(post) -> dict:
    voice = post.get("voice_messages_enabled") == "on" or post.get("voice_call_enabled") == "on"
    return {
        "default_search_radius_km": post.get("default_search_radius_km"),
        "max_search_radius_km": post.get("max_search_radius_km"),
        "video_chat_enabled": post.get("video_chat_enabled") == "on",
        "text_messages_enabled": post.get("text_messages_enabled") == "on",
        "voice_messages_enabled": voice,
        "image_messages_enabled": post.get("image_messages_enabled") == "on",
        "voice_call_enabled": voice,
        "selfie_verification_enabled": post.get("selfie_verification_enabled") == "on",
        "freemium_limits_enabled": post.get("freemium_limits_enabled") == "on",
        "force_update_enabled": post.get("force_update_enabled") == "on",
        "force_update_ios": post.get("force_update_ios"),
        "force_update_android": post.get("force_update_android"),
        "force_update_web": post.get("force_update_web"),
        "force_update_message": post.get("force_update_message"),
        "force_update_url_ios": post.get("force_update_url_ios"),
        "force_update_url_android": post.get("force_update_url_android"),
    }


def save_features_from_post(post) -> dict[str, Any]:
    voice = post.get("voice_messages_enabled") == "on"
    return save_app_config(
        {
            "text_messages_enabled": post.get("text_messages_enabled") == "on",
            "voice_messages_enabled": voice,
            "image_messages_enabled": post.get("image_messages_enabled") == "on",
            "voice_call_enabled": voice,
            "selfie_verification_enabled": post.get("selfie_verification_enabled") == "on",
            "explorer_search_enabled": post.get("explorer_search_enabled") == "on",
            "history_search_enabled": post.get("history_search_enabled") == "on",
            "messages_search_enabled": post.get("messages_search_enabled") == "on",
        }
    )


def save_force_update_from_post(post) -> dict[str, Any]:
    return save_app_config(
        {
            "force_update_enabled": post.get("force_update_enabled") == "on",
            "force_update_ios": post.get("force_update_ios"),
            "force_update_android": post.get("force_update_android"),
            "force_update_message": post.get("force_update_message"),
            "force_update_url_ios": post.get("force_update_url_ios"),
            "force_update_url_android": post.get("force_update_url_android"),
        }
    )


def apply_messaging_feature_defaults() -> dict[str, Any]:
    """Persiste les défauts métier : texte / vocal / image ON, selfie OFF."""
    return save_app_config(
        {
            "text_messages_enabled": True,
            "voice_messages_enabled": True,
            "image_messages_enabled": True,
            "voice_call_enabled": True,
            "selfie_verification_enabled": False,
            "video_chat_enabled": False,
        }
    )


def feature_flags() -> dict[str, bool]:
    cfg = get_app_config()
    return {
        "video_chat_enabled": cfg["video_chat_enabled"],
        "text_messages_enabled": cfg["text_messages_enabled"],
        "voice_messages_enabled": cfg["voice_messages_enabled"],
        "image_messages_enabled": cfg["image_messages_enabled"],
        "voice_call_enabled": cfg["voice_call_enabled"],
        "selfie_verification_enabled": cfg["selfie_verification_enabled"],
        "explorer_search_enabled": cfg["explorer_search_enabled"],
        "history_search_enabled": cfg["history_search_enabled"],
        "messages_search_enabled": cfg["messages_search_enabled"],
    }


def default_max_distance_km() -> int:
    return int(get_app_config()["default_search_radius_km"])


def selfie_verification_required() -> bool:
    return bool(get_app_config()["selfie_verification_enabled"])


def text_messages_enabled() -> bool:
    return bool(get_app_config()["text_messages_enabled"])


def voice_messages_enabled() -> bool:
    return bool(get_app_config()["voice_messages_enabled"])


def image_messages_enabled() -> bool:
    return bool(get_app_config()["image_messages_enabled"])


def freemium_enabled() -> bool:
    return bool(get_app_config()["freemium_limits_enabled"])


def parse_version(value: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in (value or "0").replace("-", ".").split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts or (0,))


def version_lt(current: str, minimum: str) -> bool:
    left = parse_version(current)
    right = parse_version(minimum)
    length = max(len(left), len(right))
    left = left + (0,) * (length - len(left))
    right = right + (0,) * (length - len(right))
    return left < right


def force_update_check(*, platform: str, app_version: str) -> dict | None:
    cfg = get_app_config()
    if not cfg.get("force_update_enabled"):
        return None
    platform = (platform or "").strip().lower()
    minimum = ""
    store_url = ""
    if platform in {"ios", "iphone", "apple"}:
        minimum = cfg.get("force_update_ios") or "1.0.0"
        store_url = cfg.get("force_update_url_ios") or ""
    elif platform in {"android", "google"}:
        minimum = cfg.get("force_update_android") or "1.0.0"
        store_url = cfg.get("force_update_url_android") or ""
    else:
        return None
    if not app_version or not version_lt(app_version, minimum):
        return None
    return {
        "required": True,
        "minimum_version": minimum,
        "current_version": app_version,
        "message": cfg.get("force_update_message") or DEFAULT_APP_CONFIG["force_update_message"],
        "store_url": store_url,
    }


def public_app_config() -> dict[str, Any]:
    cfg = get_app_config()
    return {
        "defaultSearchRadiusKm": cfg["default_search_radius_km"],
        "maxSearchRadiusKm": cfg["max_search_radius_km"],
        "features": feature_flags(),
        "freemiumLimitsEnabled": cfg["freemium_limits_enabled"],
        "forceUpdate": {
            "enabled": cfg["force_update_enabled"],
            "ios": cfg["force_update_ios"],
            "android": cfg["force_update_android"],
            "message": cfg["force_update_message"],
            "storeUrlIos": cfg["force_update_url_ios"],
            "storeUrlAndroid": cfg["force_update_url_android"],
        },
    }
