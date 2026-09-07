"""Monitoring — santé services + journal des erreurs système."""

from __future__ import annotations

import hashlib
import logging
import traceback as tb_mod
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone

logger = logging.getLogger(__name__)

# Évite les boucles si l'écriture DB échoue pendant un emit logging
_RECORDING = False

SKIP_PATH_PREFIXES = (
    "/static/",
    "/media/",
    "/favicon",
    "/espace-prive/monitoring",
    "/api/health",
)

DEDUP_MINUTES = 30
MAX_EVENTS_RETAINED = 800
TRACE_MAX = 4000
MSG_MAX = 2000


def _client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _location_from_traceback(tb_text: str) -> str:
    if not tb_text:
        return ""
    lines = [ln.strip() for ln in tb_text.strip().splitlines() if ln.strip()]
    # Prefer last "File ... line N" from project code
    candidates = [ln for ln in lines if ln.startswith("File ") and "site-packages" not in ln]
    if not candidates:
        candidates = [ln for ln in lines if ln.startswith("File ")]
    if not candidates:
        return ""
    last = candidates[-1]
    # File "/path/file.py", line 12, in func
    try:
        path_part = last.split('"')[1]
        line_part = last.split("line ", 1)[1].split(",", 1)[0].strip()
        name = path_part.replace("\\", "/").split("/")[-1]
        return f"{name}:{line_part}"
    except (IndexError, ValueError):
        return last[:120]


def _fingerprint(*, level: str, source: str, title: str, path: str, exception_type: str) -> str:
    raw = f"{level}|{source}|{title}|{path}|{exception_type}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:40]


def record_event(
    *,
    level: str,
    source: str,
    title: str,
    message: str = "",
    path: str = "",
    method: str = "",
    status_code: int | None = None,
    exception_type: str = "",
    location: str = "",
    traceback_text: str = "",
    request=None,
    metadata: dict | None = None,
) -> None:
    """Enregistre une erreur / alerte (déduplication 30 min)."""
    global _RECORDING
    if _RECORDING:
        return
    path = (path or "")[:500]
    if any(path.startswith(p) for p in SKIP_PATH_PREFIXES):
        return

    title = (title or "Événement système")[:220]
    message = (message or "")[:MSG_MAX]
    traceback_text = (traceback_text or "")[:TRACE_MAX]
    if not location and traceback_text:
        location = _location_from_traceback(traceback_text)
    location = (location or "")[:300]
    exception_type = (exception_type or "")[:120]
    method = (method or "")[:12]
    source = (source or "system")[:24]
    level = (level or "error")[:16]

    user_email = ""
    ip = _client_ip(request)
    if request is not None:
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            user_email = (getattr(user, "email", "") or "")[:254]
        if not path:
            path = (getattr(request, "path", "") or "")[:500]
        if not method:
            method = (getattr(request, "method", "") or "")[:12]

    fp = _fingerprint(
        level=level,
        source=source,
        title=title,
        path=path,
        exception_type=exception_type,
    )

    _RECORDING = True
    try:
        from core.models import SystemEvent

        now = timezone.now()
        since = now - timedelta(minutes=DEDUP_MINUTES)
        with transaction.atomic():
            existing = (
                SystemEvent.objects.select_for_update()
                .filter(fingerprint=fp, last_seen_at__gte=since)
                .order_by("-last_seen_at")
                .first()
            )
            if existing:
                existing.occurrence_count += 1
                existing.last_seen_at = now
                existing.message = message or existing.message
                if traceback_text:
                    existing.traceback = traceback_text
                if location:
                    existing.location = location
                if status_code:
                    existing.status_code = status_code
                if user_email:
                    existing.user_email = user_email
                if ip:
                    existing.ip_address = ip
                if metadata:
                    merged = dict(existing.metadata or {})
                    merged.update(metadata)
                    existing.metadata = merged
                existing.save(
                    update_fields=[
                        "occurrence_count",
                        "last_seen_at",
                        "message",
                        "traceback",
                        "location",
                        "status_code",
                        "user_email",
                        "ip_address",
                        "metadata",
                    ]
                )
            else:
                SystemEvent.objects.create(
                    level=level,
                    source=source,
                    title=title,
                    message=message,
                    path=path,
                    method=method,
                    status_code=status_code,
                    exception_type=exception_type,
                    location=location,
                    traceback=traceback_text,
                    fingerprint=fp,
                    user_email=user_email,
                    ip_address=ip,
                    metadata=metadata or {},
                    last_seen_at=now,
                )
        _prune_old_events()
    except Exception:  # noqa: BLE001
        # Ne jamais casser la requête métier pour un échec de journalisation
        logger.debug("record_event failed", exc_info=True)
    finally:
        _RECORDING = False


def _prune_old_events() -> None:
    from core.models import SystemEvent

    ids = list(
        SystemEvent.objects.order_by("-last_seen_at").values_list("id", flat=True)[MAX_EVENTS_RETAINED:]
    )
    if ids:
        SystemEvent.objects.filter(id__in=ids).delete()


def record_exception(request, exception: Exception) -> None:
    traceback_text = "".join(tb_mod.format_exception(type(exception), exception, exception.__traceback__))
    record_event(
        level="error",
        source="exception",
        title=f"{type(exception).__name__}: {exception}"[:220],
        message=str(exception)[:MSG_MAX],
        exception_type=type(exception).__name__,
        traceback_text=traceback_text,
        request=request,
        status_code=500,
    )


def record_http_error(request, status_code: int, *, detail: str = "") -> None:
    if status_code < 400:
        return
    # Ignore bruit 404 courant hors API critique
    path = getattr(request, "path", "") or ""
    if status_code == 404 and not path.startswith("/api/"):
        return
    level = "critical" if status_code >= 500 else "warning"
    title = f"HTTP {status_code} sur {path}"[:220]
    record_event(
        level=level,
        source="http",
        title=title,
        message=detail or f"Réponse {status_code}",
        status_code=status_code,
        request=request,
    )


def record_slow_request(request, duration_ms: float) -> None:
    record_event(
        level="warning",
        source="slow",
        title=f"Requête lente ({duration_ms:.0f} ms)",
        message=f"{request.method} {request.path} a pris {duration_ms:.1f} ms",
        status_code=getattr(getattr(request, "_monitoring_status", None), "status_code", None),
        request=request,
        metadata={"duration_ms": round(duration_ms, 1)},
    )


def list_events(*, level: str = "", source: str = "", limit: int = 60) -> list:
    from core.models import SystemEvent

    qs = SystemEvent.objects.all()
    if level:
        qs = qs.filter(level=level)
    if source:
        qs = qs.filter(source=source)
    return list(qs[:limit])


def events_summary() -> dict[str, Any]:
    from django.db.models import Count

    from core.models import SystemEvent

    now = timezone.now()
    day_ago = now - timedelta(days=1)
    qs = SystemEvent.objects.filter(last_seen_at__gte=day_ago)
    return {
        "errors_24h": qs.filter(level__in=["error", "critical"]).count(),
        "warnings_24h": qs.filter(level="warning").count(),
        "critical_24h": qs.filter(level="critical").count(),
        "by_source": list(
            qs.values("source").annotate(n=Count("id")).order_by("-n")[:8]
        ),
    }


def format_event_for_ui(event) -> dict[str, Any]:
    return {
        "id": str(event.id),
        "level": event.level,
        "level_label": event.get_level_display(),
        "source": event.source,
        "source_label": event.get_source_display(),
        "title": event.title,
        "message": event.message,
        "path": event.path,
        "method": event.method,
        "status_code": event.status_code,
        "exception_type": event.exception_type,
        "location": event.location,
        "traceback": event.traceback,
        "occurrence_count": event.occurrence_count,
        "user_email": event.user_email,
        "ip_address": event.ip_address,
        "created_at": event.created_at,
        "last_seen_at": event.last_seen_at,
        "where": _where_label(event),
    }


def _where_label(event) -> str:
    parts = []
    if event.method and event.path:
        parts.append(f"{event.method} {event.path}")
    elif event.path:
        parts.append(event.path)
    if event.location:
        parts.append(event.location)
    if event.status_code:
        parts.append(f"HTTP {event.status_code}")
    return " · ".join(parts) if parts else "—"
