"""Monitoring — santé services + journal des erreurs système."""

from __future__ import annotations

import hashlib
import logging
import traceback as tb_mod
from datetime import timedelta
from typing import Any

from django.db import transaction
from django.db.models import Q
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
# Niveaux affichés dans le journal Monitoring (pas les avertissements / requêtes lentes).
JOURNAL_LEVELS = ("error", "critical")
JOURNAL_MAX_AGE_DAYS = 14

# Erreurs attendues / non bloquantes — ne pas journaliser ni afficher.
IGNORE_EXCEPTION_TYPES = frozenset(
    {
        "Http404",
        "PermissionDenied",
        "SuspiciousOperation",
        "ValidationError",
        "EmptyPage",
        "PageNotAnInteger",
    }
)

IGNORE_LOGGING_TITLES = (
    "Internal Server Error:",
    "Bad Request:",
    "Not Found:",
    "Forbidden:",
)


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


def _is_ignorable_exception(exception: Exception | None) -> bool:
    if exception is None:
        return False
    from django.core.exceptions import PermissionDenied, SuspiciousOperation, ValidationError
    from django.core.paginator import EmptyPage, PageNotAnInteger
    from django.http import Http404

    if isinstance(
        exception,
        (Http404, PermissionDenied, SuspiciousOperation, ValidationError, EmptyPage, PageNotAnInteger),
    ):
        return True
    return type(exception).__name__ in IGNORE_EXCEPTION_TYPES


def _apply_journal_filters(qs):
    qs = qs.exclude(exception_type__in=IGNORE_EXCEPTION_TYPES)
    for prefix in IGNORE_LOGGING_TITLES:
        qs = qs.exclude(source="logging", title__startswith=prefix)
    qs = qs.exclude(source="logging", metadata__logger="django.request")
    # Les entrées HTTP 500 génériques dupliquent l'exception sans stack trace utile.
    qs = qs.exclude(source="http")
    cutoff = timezone.now() - timedelta(days=JOURNAL_MAX_AGE_DAYS)
    return qs.filter(last_seen_at__gte=cutoff)


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
    if _is_ignorable_exception(exception):
        return
    if request is not None:
        request._monitoring_exception_logged = True  # noqa: SLF001
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
    if status_code < 500:
        return
    if getattr(request, "_monitoring_exception_logged", False):
        return
    path = getattr(request, "path", "") or ""
    record_event(
        level="critical",
        source="http",
        title=f"HTTP {status_code} sur {path}"[:220],
        message=detail or f"Réponse {status_code}",
        status_code=status_code,
        request=request,
    )


def record_slow_request(request, duration_ms: float) -> None:
    """Conservé pour compatibilité — les requêtes lentes ne sont plus journalisées."""
    return


def list_events(*, level: str = "", source: str = "", limit: int = 60) -> list:
    from core.models import SystemEvent

    qs = SystemEvent.objects.filter(level__in=JOURNAL_LEVELS)
    qs = _apply_journal_filters(qs)
    if level in JOURNAL_LEVELS:
        qs = qs.filter(level=level)
    if source:
        if source == SystemEvent.Source.SLOW:
            return []
        qs = qs.filter(source=source)
    else:
        qs = qs.exclude(source=SystemEvent.Source.SLOW)
    return list(qs.order_by("-last_seen_at")[:limit])


def events_summary() -> dict[str, Any]:
    from django.db.models import Count

    from core.models import SystemEvent

    now = timezone.now()
    day_ago = now - timedelta(days=1)
    qs = SystemEvent.objects.filter(last_seen_at__gte=day_ago, level__in=JOURNAL_LEVELS)
    qs = _apply_journal_filters(qs)
    return {
        "errors_24h": qs.filter(level="error").count(),
        "warnings_24h": 0,
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


def prune_benign_events() -> int:
    """Supprime du journal les erreurs non bloquantes, doublons et bugs déjà corrigés."""
    from core.models import SystemEvent

    criteria = Q(exception_type__in=IGNORE_EXCEPTION_TYPES) | Q(
        source="logging", metadata__logger="django.request"
    )
    for prefix in IGNORE_LOGGING_TITLES:
        criteria |= Q(source="logging", title__startswith=prefix)

    # Bugs corrigés en production — retirer l'historique bruyant du journal.
    criteria |= Q(path="/espace-prive/paiements/", exception_type="TypeError")
    criteria |= Q(path="/espace-prive/paiements/", exception_type="TemplateSyntaxError")
    criteria |= Q(path="/espace-prive/paiements/", title__icontains="tx_status_badge")
    criteria |= Q(path="/temoignages/", exception_type="NameError")
    criteria |= Q(path="/temoignages/", title__icontains="home_controller")
    criteria |= Q(path="/api/payments/confirm/", exception_type="AttributeError")
    criteria |= Q(path="/api/payments/confirm/", title__icontains="has no attribute 'messages'")
    criteria |= Q(path="/espace-prive/paiements/", source="http", status_code=500)
    criteria |= Q(path="/temoignages/", source="http", status_code=500)
    criteria |= Q(path="/api/payments/confirm/", source="http", status_code=500)
    criteria |= Q(path="/api/profile/photo/primary/", source="http", status_code=500)
    criteria |= Q(exception_type="EmptyPage")
    criteria |= Q(exception_type="PageNotAnInteger")
    criteria |= Q(title__icontains="EmptyPage")
    criteria |= Q(path="/espace-prive/membres/", exception_type="EmptyPage")
    criteria |= Q(path="/espace-prive/signalements/", exception_type="EmptyPage")
    criteria |= Q(path="/coaching/", exception_type="DataError")
    criteria |= Q(path="/coaching/", title__icontains="integer out of range")
    criteria |= Q(source="http")

    deleted, _details = SystemEvent.objects.filter(criteria).delete()
    return int(deleted)


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
