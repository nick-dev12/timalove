"""Notifications in-app, temps réel et push FCM."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from core.models import Match, Notification, Profile
from core.models.choices import NotificationType

logger = logging.getLogger(__name__)

MESSAGE_PUSH_COOLDOWN = timedelta(minutes=2)


def _notification_kind(notification: Notification) -> str:
    if notification.type == NotificationType.NEW_LIKE:
        title = (notification.title or "").strip().lower()
        if title == "super like":
            return "super_like"
        return "new_like"
    return notification.type


def _notification_payload(notification: Notification) -> dict:
    from core.controllers import likes_controller, message_controller, push_controller

    related = getattr(notification, "related_user", None)
    name = ""
    photo = ""
    initial = "?"
    if related is not None:
        name = (related.first_name or "Membre").strip() or "Membre"
        photo = related.primary_photo or ""
        initial = name[:1].upper()

    kind = _notification_kind(notification)
    payload = {
        "id": str(notification.id),
        "event": "notification",
        "type": notification.type,
        "kind": kind,
        "title": notification.title,
        "message": notification.message,
        "related_user_id": str(notification.related_user_id) if notification.related_user_id else None,
        "related_user_name": name,
        "related_user_photo": photo,
        "related_user_initial": initial,
        "related_match_id": str(notification.related_match_id) if notification.related_match_id else None,
        "url": push_controller.notification_link(notification),
        "created_at": notification.created_at.isoformat() if notification.created_at else None,
        "unread_messages": 0,
        "likes_count": 0,
    }
    if notification.type == NotificationType.PROFILE_APPROVED and notification.title == "Test TimaLove":
        payload["test"] = True
    try:
        payload["unread_messages"] = message_controller.unread_count(notification.user)
        payload["likes_count"] = likes_controller.count_unread_incoming(notification.user)
    except Exception:
        pass
    return payload


def _broadcast_realtime(notification: Notification) -> None:
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if not layer:
            return
        async_to_sync(layer.group_send)(
            f"notif_{notification.user_id}",
            {"type": "notify", "payload": _notification_payload(notification)},
        )
    except Exception as exc:
        logger.warning("[notif] websocket indisponible : %s", exc)


def _dispatch_push(notification: Notification, *, force: bool = False) -> None:
    if not getattr(settings, "FCM_ENABLED", False):
        return
    from core.controllers import push_controller
    from core.tasks import send_push_notification

    notification_id = str(notification.id)
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        push_controller.send_for_notification(notification_id, force=force)
        return
    try:
        send_push_notification.delay(notification_id, force=force)
    except Exception:
        push_controller.send_for_notification(notification_id, force=force)


def create(
    *,
    user: Profile,
    type: str,
    title: str,
    message: str,
    related_user: Profile | None = None,
    related_match: Match | None = None,
    push_force: bool = False,
) -> Notification:
    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
        related_user=related_user,
        related_match=related_match,
    )
    _broadcast_realtime(notification)
    _dispatch_push(notification, force=push_force)
    return notification


def should_notify_message(*, recipient: Profile, match: Match) -> bool:
    """Évite le spam push sur une même conversation (fenêtre courte)."""
    cutoff = timezone.now() - MESSAGE_PUSH_COOLDOWN
    return not Notification.objects.filter(
        user=recipient,
        type=NotificationType.NEW_MESSAGE,
        related_match=match,
        created_at__gte=cutoff,
    ).exists()


def notify_new_message(
    *,
    sender: Profile,
    match: Match,
    preview: str,
) -> Notification | None:
    partner = match.partner_of(sender)
    if partner.pk == sender.pk:
        return None
    from core.controllers.moderation_controller import is_blocked_between

    if is_blocked_between(sender, partner):
        return None
    body = (preview or "").strip() or f"{sender.first_name} vous a écrit."
    push_ok = should_notify_message(recipient=partner, match=match)
    notification = Notification.objects.create(
        user=partner,
        type=NotificationType.NEW_MESSAGE,
        title=f"Message de {sender.first_name}",
        message=body[:240],
        related_user=sender,
        related_match=match,
    )
    _broadcast_realtime(notification)
    # Push throttlé ; in-app + WS toujours envoyés (y compris compte limité en réception).
    if push_ok:
        _dispatch_push(notification)
    return notification


def notify_match(*, profile: Profile, partner: Profile, match: Match) -> Notification:
    name = (partner.first_name or "Quelqu'un").strip()
    return create(
        user=profile,
        type=NotificationType.NEW_MATCH,
        title="Nouveau match",
        message=f"Vous et {name} vous êtes likés. Écrivez-lui !",
        related_user=partner,
        related_match=match,
    )


def notify_like(*, recipient: Profile, sender: Profile, is_super_like: bool) -> Notification:
    if is_super_like:
        return create(
            user=recipient,
            type=NotificationType.NEW_LIKE,
            title="Super like",
            message=f"{sender.first_name} vous a envoyé un Super like.",
            related_user=sender,
        )
    return create(
        user=recipient,
        type=NotificationType.NEW_LIKE,
        title="Nouveau like",
        message=f"{sender.first_name} a aimé votre profil.",
        related_user=sender,
    )


def send_test(profile: Profile) -> dict:
    """Envoie une notification de test (in-app + push forcée)."""
    from core.controllers import push_controller
    from core.controllers.profile_controller import notification_prefs_for
    from core.models import PushDevice

    prefs = notification_prefs_for(profile)
    if not prefs.get("push"):
        raise ValueError("Activez d’abord les notifications push.")
    if PushDevice.objects.filter(profile=profile).count() == 0:
        raise ValueError("Aucun appareil enregistré. Réactivez les notifications sur cet appareil.")

    notification = Notification.objects.create(
        user=profile,
        type=NotificationType.PROFILE_APPROVED,
        title="Test TimaLove",
        message="Vos notifications fonctionnent. Vous recevrez likes, matchs et messages ici.",
    )
    # Push FCM d'abord : le broadcast Redis ne doit pas bloquer le bouton de test.
    result = push_controller.send_for_notification(str(notification.id), force=True)
    _broadcast_realtime(notification)
    return {
        "notification_id": str(notification.id),
        "url": push_controller.notification_link(notification),
        **result,
    }


def list_for(profile: Profile, limit: int = 50) -> list[Notification]:
    return list(profile.notifications.select_related("related_user")[:limit])


def unread_count(profile: Profile) -> int:
    return profile.notifications.filter(is_read=False).count()


def mark_read(profile: Profile, ids: list | None = None) -> int:
    qs = profile.notifications.filter(is_read=False)
    if ids:
        qs = qs.filter(id__in=ids)
    return qs.update(is_read=True, read_at=timezone.now())
