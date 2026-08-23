"""Notifications push Firebase Cloud Messaging (FCM)."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.utils import timezone

from core.controllers.firebase_app import get_firebase_app
from core.models import Notification, Profile, PushDevice
from core.utils.site_url import site_url_is_public

logger = logging.getLogger(__name__)

NOTIFICATION_PREF_MAP = {
    "new_match": "matches",
    "new_message": "messages",
    "profile_approved": "status",
    "profile_rejected": "status",
    "subscription_activated": "status",
    "subscription_expired": "status",
    "boost_activated": "status",
}

INVALID_TOKEN_ERRORS = {
    "registration-token-not-registered",
    "invalid-registration-token",
    "invalid-argument",
}


def _is_https_url(url: str) -> bool:
    return (url or "").lower().startswith("https://")


def _webpush_config(notification: Notification, link: str) -> "messaging.WebpushConfig":
    from firebase_admin import messaging

    # Data-only : le SW / onMessage affichent la notif. Un payload `notification`
    # est avalé par Chrome dès qu’un onglet du site est ouvert (aucun push OS).
    config_kwargs: dict = {
        "headers": {"Urgency": "high", "TTL": "86400"},
    }
    if _is_https_url(link):
        config_kwargs["fcm_options"] = messaging.WebpushFCMOptions(link=link)
    return messaging.WebpushConfig(**config_kwargs)


def _firebase_enabled() -> bool:
    return bool(getattr(settings, "FCM_ENABLED", False))


def _get_firebase_app():
    if not _firebase_enabled():
        return None
    return get_firebase_app()


def public_config() -> dict[str, Any]:
    return {
        "enabled": _firebase_enabled(),
        "firebase": {
            "apiKey": settings.FIREBASE_WEB_API_KEY,
            "authDomain": settings.FIREBASE_AUTH_DOMAIN,
            "projectId": settings.FIREBASE_PROJECT_ID,
            "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
            "messagingSenderId": settings.FIREBASE_MESSAGING_SENDER_ID,
            "appId": settings.FIREBASE_APP_ID,
            "measurementId": settings.FIREBASE_MEASUREMENT_ID,
        },
        "vapidKey": settings.FIREBASE_VAPID_KEY,
    }


def register_device(
    profile: Profile,
    *,
    token: str,
    platform: str = PushDevice.Platform.WEB,
    user_agent: str = "",
) -> PushDevice:
    token = token.strip()
    if not token:
        raise ValueError("Token FCM requis.")

    device, _created = PushDevice.objects.update_or_create(
        token=token,
        defaults={
            "profile": profile,
            "platform": platform if platform in PushDevice.Platform.values else PushDevice.Platform.WEB,
            "user_agent": (user_agent or "")[:500],
            "last_used_at": timezone.now(),
        },
    )
    return device


def unregister_device(profile: Profile, *, token: str) -> bool:
    deleted, _ = PushDevice.objects.filter(profile=profile, token=token.strip()).delete()
    return deleted > 0


def status_for(profile: Profile) -> dict[str, Any]:
    from core.controllers.profile_controller import notification_prefs_for

    prefs = notification_prefs_for(profile)
    devices = list(PushDevice.objects.filter(profile=profile).order_by("-last_used_at"))
    cred_ok = bool(settings.FIREBASE_CREDENTIALS_PATH.exists())
    return {
        "fcm_enabled": _firebase_enabled(),
        "credentials_found": cred_ok,
        "site_url": settings.SITE_URL.rstrip("/"),
        "site_url_public": site_url_is_public(settings.SITE_URL, debug=settings.DEBUG),
        "push_enabled": bool(prefs.get("push")),
        "preferences": prefs,
        "devices_count": len(devices),
        "devices": [
            {
                "id": str(device.id),
                "platform": device.platform,
                "last_used_at": device.last_used_at.isoformat() if device.last_used_at else None,
            }
            for device in devices
        ],
    }


def user_allows_push(profile: Profile, notification: Notification) -> bool:
    prefs = profile.notification_preferences or {}
    if prefs.get("push") is False:
        return False

    notification_type = notification.type
    if notification_type == "new_like":
        title = (notification.title or "").strip().lower()
        if title == "super like":
            return prefs.get("super_likes", True) is not False
        return prefs.get("likes", True) is not False

    pref_key = NOTIFICATION_PREF_MAP.get(notification_type)
    if pref_key and prefs.get(pref_key) is False:
        return False
    return True


def _notification_link(notification: Notification) -> str:
    return notification_link(notification)


def notification_link(notification: Notification) -> str:
    """Chemin relatif — le navigateur complète avec son origin (évite SITE_URL mal configuré)."""
    if notification.type == "new_message" and notification.related_match_id:
        partner_id = notification.related_user_id
        if partner_id:
            return f"/discussions/{partner_id}/"
    if notification.type == "new_match":
        partner_id = notification.related_user_id
        if partner_id:
            return f"/discussions/{partner_id}/"
        return "/likes/"
    if notification.type == "new_like":
        return "/likes/"
    return "/profil/?tab=settings"


def absolute_notification_link(notification: Notification) -> str:
    rel = notification_link(notification)
    if rel.startswith("/"):
        return f"{settings.SITE_URL.rstrip('/')}{rel}"
    return rel


def send_for_notification(notification_id: str, *, force: bool = False) -> dict[str, int]:
    """Envoie la push FCM pour une notification in-app existante."""
    if not _firebase_enabled():
        return {"sent": 0, "failed": 0, "skipped": 1}

    try:
        notification = Notification.objects.select_related("user", "related_user", "related_match").get(
            id=notification_id
        )
    except Notification.DoesNotExist:
        logger.warning("[fcm] notification introuvable : %s", notification_id)
        return {"sent": 0, "failed": 0, "skipped": 1}

    if not force and not user_allows_push(notification.user, notification):
        return {"sent": 0, "failed": 0, "skipped": 1}

    devices = list(PushDevice.objects.filter(profile=notification.user))
    if not devices:
        return {"sent": 0, "failed": 0, "skipped": 1}

    app = _get_firebase_app()
    if app is None:
        return {"sent": 0, "failed": 0, "skipped": 1}

    from firebase_admin import messaging

    link = notification_link(notification)
    absolute_link = absolute_notification_link(notification)
    data = {
        "notification_id": str(notification.id),
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "url": link,
    }
    if force and notification.type == "profile_approved" and notification.title == "Test TimaLove":
        data["test"] = "true"
    if notification.related_user_id:
        data["related_user_id"] = str(notification.related_user_id)
    if notification.related_match_id:
        data["related_match_id"] = str(notification.related_match_id)

    sent = 0
    failed = 0
    stale_tokens: list[str] = []
    errors: list[str] = []

    for device in devices:
        message = messaging.Message(
            token=device.token,
            data={k: str(v) for k, v in data.items()},
            webpush=_webpush_config(notification, absolute_link),
        )
        try:
            messaging.send(message, app=app)
            sent += 1
            PushDevice.objects.filter(pk=device.pk).update(last_used_at=timezone.now())
        except Exception as exc:
            failed += 1
            err_msg = getattr(exc, "message", None) or str(exc)
            errors.append(err_msg)
            code = getattr(exc, "code", "") or err_msg
            if any(marker in code for marker in INVALID_TOKEN_ERRORS):
                stale_tokens.append(device.token)
            logger.warning("[fcm] envoi échoué token=%s… : %s", device.token[:12], code)

    if stale_tokens:
        PushDevice.objects.filter(token__in=stale_tokens).delete()

    return {"sent": sent, "failed": failed, "skipped": 0, "errors": errors}
