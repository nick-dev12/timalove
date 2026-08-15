"""Notifications push Firebase Cloud Messaging (FCM)."""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.utils import timezone

from core.controllers.firebase_app import get_firebase_app
from core.models import Notification, Profile, PushDevice

logger = logging.getLogger(__name__)

NOTIFICATION_PREF_MAP = {
    "new_like": "likes",
    "new_match": "matches",
    "new_message": "messages",
}

INVALID_TOKEN_ERRORS = {
    "registration-token-not-registered",
    "invalid-registration-token",
    "invalid-argument",
}


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


def user_allows_push(profile: Profile, notification_type: str) -> bool:
    prefs = profile.notification_preferences or {}
    if prefs.get("push") is False:
        return False
    pref_key = NOTIFICATION_PREF_MAP.get(notification_type)
    if pref_key and prefs.get(pref_key) is False:
        return False
    return True


def _notification_link(notification: Notification) -> str:
    site = settings.SITE_URL.rstrip("/")
    if notification.type == "new_message" and notification.related_match_id:
        partner_id = notification.related_user_id
        if partner_id:
            return f"{site}/discussions/{partner_id}/"
    if notification.type == "new_match":
        return f"{site}/rencontres/"
    if notification.type == "new_like":
        return f"{site}/likes/"
    return f"{site}/profil/?tab=settings"


def send_for_notification(notification_id: str) -> dict[str, int]:
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

    if not user_allows_push(notification.user, notification.type):
        return {"sent": 0, "failed": 0, "skipped": 1}

    devices = list(PushDevice.objects.filter(profile=notification.user))
    if not devices:
        return {"sent": 0, "failed": 0, "skipped": 1}

    app = _get_firebase_app()
    if app is None:
        return {"sent": 0, "failed": 0, "skipped": 1}

    from firebase_admin import messaging

    link = _notification_link(notification)
    data = {
        "notification_id": str(notification.id),
        "type": notification.type,
        "title": notification.title,
        "message": notification.message,
        "url": link,
    }
    if notification.related_user_id:
        data["related_user_id"] = str(notification.related_user_id)
    if notification.related_match_id:
        data["related_match_id"] = str(notification.related_match_id)

    sent = 0
    failed = 0
    stale_tokens: list[str] = []

    for device in devices:
        message = messaging.Message(
            token=device.token,
            notification=messaging.Notification(
                title=notification.title,
                body=notification.message[:240],
            ),
            data={k: str(v) for k, v in data.items()},
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=notification.title,
                    body=notification.message[:240],
                    icon=f"{settings.SITE_URL.rstrip('/')}/static/images/logo.webp",
                ),
                fcm_options=messaging.WebpushFCMOptions(link=link),
            ),
        )
        try:
            messaging.send(message, app=app)
            sent += 1
            PushDevice.objects.filter(pk=device.pk).update(last_used_at=timezone.now())
        except Exception as exc:
            failed += 1
            code = getattr(exc, "code", "") or str(exc)
            if any(marker in code for marker in INVALID_TOKEN_ERRORS):
                stale_tokens.append(device.token)
            logger.warning("[fcm] envoi échoué token=%s… : %s", device.token[:12], code)

    if stale_tokens:
        PushDevice.objects.filter(token__in=stale_tokens).delete()

    return {"sent": sent, "failed": failed, "skipped": 0}
