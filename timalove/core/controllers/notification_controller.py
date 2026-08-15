"""Notifications."""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone

from core.models import Match, Notification, Profile


def create(
    *,
    user: Profile,
    type: str,
    title: str,
    message: str,
    related_user: Profile | None = None,
    related_match: Match | None = None,
) -> Notification:
    notification = Notification.objects.create(
        user=user,
        type=type,
        title=title,
        message=message,
        related_user=related_user,
        related_match=related_match,
    )

    if getattr(settings, "FCM_ENABLED", False):
        from core.tasks import send_push_notification

        send_push_notification.delay(str(notification.id))

    return notification


def list_for(profile: Profile, limit: int = 50) -> list[Notification]:
    return list(profile.notifications.select_related("related_user")[:limit])


def unread_count(profile: Profile) -> int:
    return profile.notifications.filter(is_read=False).count()


def mark_read(profile: Profile, ids: list | None = None) -> int:
    qs = profile.notifications.filter(is_read=False)
    if ids:
        qs = qs.filter(id__in=ids)
    return qs.update(is_read=True, read_at=timezone.now())
