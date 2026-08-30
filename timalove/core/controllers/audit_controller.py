"""Journal d'audit back-office."""

from __future__ import annotations

from django.core.paginator import Paginator

from core.models import AuditLog, Profile

ACTION_FILTERS: list[tuple[str, str]] = [
    ("", "Toutes les actions"),
    ("user.ban", "Bannissements"),
    ("user.unban", "Levées de ban"),
    ("user.suspend", "Suspensions"),
    ("user.subscription_grant", "Abonnements accordés"),
    ("finance.refund", "Remboursements"),
    ("report.ban", "Bans via signalement"),
    ("report.dismiss", "Signalements ignorés"),
    ("config.algorithm", "Config algorithmique"),
    ("config.features", "Fonctionnalités app"),
    ("config.system", "Paramètres système"),
    ("monetisation.promo_create", "Codes promo créés"),
    ("monetisation.plans_save", "Formules enregistrées"),
    ("staff.create", "Comptes staff créés"),
    ("security.2fa_enable", "2FA activée"),
    ("settings.contact", "Contact & contenu"),
]


def _client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_action(
    actor: Profile | None,
    action: str,
    message: str,
    *,
    target_type: str = "",
    target_id: str = "",
    target_label: str = "",
    metadata: dict | None = None,
    request=None,
) -> AuditLog:
    actor_name = "Système"
    if actor:
        actor_name = actor.display_name or actor.first_name or "Admin"
    if actor and actor_name not in message:
        message = f"{actor_name} — {message}"
    return AuditLog.objects.create(
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=str(target_id) if target_id else "",
        target_label=target_label[:200] if target_label else "",
        message=message,
        metadata=metadata or {},
        ip_address=_client_ip(request),
    )


def list_audit_logs(*, search: str = "", action: str | None = None, page: int = 1, per_page: int = 40):
    qs = AuditLog.objects.select_related("actor").order_by("-created_at")
    if action:
        qs = qs.filter(action=action)
    if search:
        qs = qs.filter(message__icontains=search)
    paginator = Paginator(qs, per_page)
    return paginator.get_page(page)


def audit_summary() -> dict:
    from django.utils import timezone

    today = timezone.localdate()
    base = AuditLog.objects.all()
    return {
        "total": base.count(),
        "today": base.filter(created_at__date=today).count(),
    }


def format_log_row(log: AuditLog) -> str:
    when = log.created_at.strftime("%d/%m/%Y à %H:%M")
    return f"{log.message} — {when}"


def log_admin(request, action: str, message: str, **kwargs) -> AuditLog:
    """Raccourci depuis une vue admin HTTP."""
    actor = getattr(getattr(request, "user", None), "profile", None)
    return log_action(actor, action, message, request=request, **kwargs)


def profile_ref(profile) -> str:
    if not profile:
        return "?"
    return f"#{str(profile.id).replace('-', '')[:8]}"
