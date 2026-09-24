"""Présence réelle : un membre est en ligne seulement s’il a un socket ouvert."""

from __future__ import annotations

from datetime import timedelta

from django.core.cache import cache
from django.utils import timezone

from core.models import Profile

ONLINE_TTL_SECONDS = 90
CONN_KEY_TTL = 60 * 60 * 24
PRESENCE_GROUP = "presence"


def _conn_key(profile_id) -> str:
    return f"presence:conns:{profile_id}"


def connection_count(profile_id) -> int:
    try:
        return max(0, int(cache.get(_conn_key(profile_id)) or 0))
    except (TypeError, ValueError):
        return 0


def _persist(profile_id, online: bool) -> None:
    fields = {"is_online": online}
    if online:
        fields["last_active_at"] = timezone.now()
    Profile.objects.filter(pk=profile_id).update(**fields)


def mark_socket_connected(profile_id) -> bool:
    """Incrémente les sockets ouverts. True si le membre vient de passer en ligne."""
    key = _conn_key(profile_id)
    cache.add(key, 0, timeout=CONN_KEY_TTL)
    try:
        count = cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=CONN_KEY_TTL)
        count = 1
    became_online = count == 1
    if became_online:
        _persist(profile_id, True)
    else:
        Profile.objects.filter(pk=profile_id).update(last_active_at=timezone.now(), is_online=True)
    return became_online


def mark_socket_disconnected(profile_id) -> bool:
    """Décrémente. True si plus aucun socket — le membre est hors ligne."""
    key = _conn_key(profile_id)
    try:
        count = cache.decr(key)
    except ValueError:
        cache.delete(key)
        _persist(profile_id, False)
        return True
    if count <= 0:
        cache.delete(key)
        _persist(profile_id, False)
        return True
    return False


def mark_offline(profile: Profile) -> None:
    cache.delete(_conn_key(profile.pk))
    _persist(profile.pk, False)


def heartbeat(profile_id) -> None:
    if connection_count(profile_id) > 0:
        Profile.objects.filter(pk=profile_id).update(last_active_at=timezone.now(), is_online=True)


def is_present(profile: Profile) -> bool:
    if connection_count(profile.pk) > 0:
        return True
    if not getattr(profile, "is_online", False):
        return False
    last = getattr(profile, "last_active_at", None)
    if not last:
        return False
    return timezone.now() - last <= timedelta(seconds=ONLINE_TTL_SECONDS)


def status_for_ids(profile_ids: list) -> dict[str, bool]:
    import uuid

    ids: list[uuid.UUID] = []
    for raw in profile_ids[:100]:
        text = str(raw or "").strip()
        if not text:
            continue
        try:
            ids.append(uuid.UUID(text))
        except ValueError:
            continue
    if not ids:
        return {}
    rows = Profile.objects.filter(pk__in=ids).only("pk", "is_online", "last_active_at")
    return {str(profile.pk): is_present(profile) for profile in rows}


def presence_payload(profile_id, online: bool) -> dict:
    return {
        "event": "presence",
        "profile_id": str(profile_id),
        "online": bool(online),
    }
