"""Témoignages, reports, blocks."""

from __future__ import annotations

from django.core.paginator import Paginator
from django.db import models
from django.db.models import Case, Count, IntegerField, Q, Value, When
from django.utils import timezone

from core.models import BannedIdentity, BlockedUser, PhotoBlacklist, Profile, Report, Testimonial
from core.models.choices import NotificationType, ReportReason, ReportStatus

REPORT_REASON_PRIORITY: dict[str, int] = {
    ReportReason.HARASSMENT: 100,
    ReportReason.HATE_SPEECH: 95,
    ReportReason.SCAM: 90,
    ReportReason.INAPPROPRIATE_CONTENT: 85,
    ReportReason.FAKE_PROFILE: 80,
    ReportReason.SPAM: 50,
    ReportReason.OTHER: 30,
    ReportReason.PLATFORM: 20,
}

URGENT_REASONS = frozenset(
    {
        ReportReason.HARASSMENT,
        ReportReason.HATE_SPEECH,
        ReportReason.SCAM,
        ReportReason.INAPPROPRIATE_CONTENT,
    }
)


def published_testimonials(limit: int = 12) -> list[Testimonial]:
    return list(Testimonial.objects.filter(is_published=True).order_by("-created_at")[:limit])


def submit_testimonial(profile: Profile | None, data: dict) -> Testimonial:
    return Testimonial.objects.create(
        user=profile,
        author_name=data.get("author_name") or (profile.first_name if profile else "Anonyme"),
        author_age=data.get("author_age") or (profile.age if profile else None),
        content=data["content"],
        rating=int(data.get("rating", 5)),
        is_published=False,
    )


def moderate_testimonial(tid, *, is_published: bool | None = None, delete: bool = False):
    t = Testimonial.objects.get(pk=tid)
    if delete:
        t.delete()
        return None
    if is_published is not None:
        t.is_published = is_published
        t.is_verified = is_published
        t.save()
    return t


def create_report(reporter: Profile, data: dict) -> Report:
    from core.models.choices import ReportReason

    reported = None
    if data.get("reported_profile_id"):
        reported = Profile.objects.filter(pk=data["reported_profile_id"]).first()
    reason = (data.get("reason") or ReportReason.OTHER).strip()
    if reason not in ReportReason.values:
        reason = ReportReason.OTHER
    message = (data.get("message") or "").strip()
    if not message:
        raise ValueError("Décrivez brièvement le motif du signalement.")
    report = Report.objects.create(
        reporter=reporter,
        reported_profile=reported,
        reason=reason,
        message=message,
        report_kind=data.get("report_kind", "profile"),
    )
    _maybe_auto_ban_reported(reported, reason)
    return report


AUTO_BAN_REASONS = frozenset(
    {
        ReportReason.HARASSMENT,
        ReportReason.HATE_SPEECH,
        ReportReason.INAPPROPRIATE_CONTENT,
        ReportReason.SCAM,
        "inappropriate_content",
        "harassment",
        "hate_speech",
        "scam",
    }
)
AUTO_BAN_THRESHOLD = 2


def _maybe_auto_ban_reported(reported: Profile | None, reason: str) -> None:
    if reported is None or reason not in AUTO_BAN_REASONS:
        return
    if reported.banned_at:
        return
    distinct_reporters = (
        Report.objects.filter(
            reported_profile=reported,
            reason__in=AUTO_BAN_REASONS,
        )
        .values("reporter_id")
        .distinct()
        .count()
    )
    if distinct_reporters < AUTO_BAN_THRESHOLD:
        return
    ban_profile(
        reported,
        reason=f"Ban automatique après {distinct_reporters} signalements ({reason}).",
        admin=None,
    )
    Report.objects.filter(reported_profile=reported, reason__in=AUTO_BAN_REASONS).update(
        status=ReportStatus.ACTION_TAKEN,
        resolution="banned",
    )


def reports_summary() -> dict:
    today = timezone.localdate()
    pending = Report.objects.filter(status=ReportStatus.PENDING)
    return {
        "pending": pending.count(),
        "urgent": pending.filter(reason__in=URGENT_REASONS).count(),
        "treated_today": Report.objects.filter(reviewed_at__date=today).exclude(
            status=ReportStatus.PENDING
        ).count(),
        "dismissed": Report.objects.filter(status=ReportStatus.DISMISSED).count(),
    }


def _priority_annotation(qs):
    reason_cases = [
        When(reason=reason, then=Value(score)) for reason, score in REPORT_REASON_PRIORITY.items()
    ]
    return qs.annotate(
        reason_priority=Case(*reason_cases, default=Value(10), output_field=IntegerField()),
        status_priority=Case(
            When(status=ReportStatus.PENDING, then=Value(0)),
            default=Value(1),
            output_field=IntegerField(),
        ),
        pending_against=Count(
            "reported_profile__reports_received",
            filter=Q(reported_profile__reports_received__status=ReportStatus.PENDING),
            distinct=True,
        ),
    )


def list_reports(
    *,
    status: str | None = None,
    search: str = "",
    priority: str | None = None,
    page: int = 1,
    per_page: int = 30,
):
    qs = Report.objects.select_related("reporter", "reported_profile", "resolved_by")
    if status:
        qs = qs.filter(status=status)
    if priority == "urgent":
        qs = qs.filter(status=ReportStatus.PENDING, reason__in=URGENT_REASONS)
    if search:
        qs = qs.filter(
            Q(reporter__first_name__icontains=search)
            | Q(reporter__last_name__icontains=search)
            | Q(reported_profile__first_name__icontains=search)
            | Q(reported_profile__last_name__icontains=search)
            | Q(message__icontains=search)
            | Q(reason__icontains=search)
            | Q(admin_note__icontains=search)
        )
    qs = _priority_annotation(qs).order_by(
        "status_priority",
        "-reason_priority",
        "-pending_against",
        "-created_at",
    )
    paginator = Paginator(qs, per_page)
    return paginator.get_page(page)


def get_report(report_id) -> Report | None:
    return (
        Report.objects.select_related("reporter", "reported_profile", "resolved_by")
        .filter(pk=report_id)
        .first()
    )


def report_priority_label(report: Report) -> str:
    if report.status != ReportStatus.PENDING:
        return "Traité"
    if report.reason in URGENT_REASONS:
        return "Urgent"
    if report.reason in {ReportReason.FAKE_PROFILE, ReportReason.SPAM}:
        return "Élevée"
    return "Normale"


def report_context(report: Report) -> dict:
    from core.controllers.explore_controller import collect_photos
    from core.models import Match, Message

    photos: list[str] = []
    messages: list[dict] = []
    if report.reported_profile_id:
        photos = collect_photos(report.reported_profile, limit=6)
    if report.reporter_id and report.reported_profile_id:
        match = Match.objects.filter(
            Q(user_1=report.reporter, user_2=report.reported_profile)
            | Q(user_1=report.reported_profile, user_2=report.reporter)
        ).first()
        if match:
            for msg in Message.objects.filter(match=match).select_related("sender").order_by("-created_at")[:5]:
                messages.append(
                    {
                        "id": str(msg.id)[:8],
                        "sender_id": str(msg.sender_id)[:8] if msg.sender_id else "—",
                        "sender_name": msg.sender.first_name if msg.sender else "—",
                        "content": (msg.content or "")[:500] or f"[{msg.get_message_type_display()}]",
                        "type": msg.message_type,
                        "created_at": msg.created_at,
                        "is_flagged": msg.is_flagged,
                    }
                )
            messages.reverse()
    return {"photos": photos, "messages": messages}


def _photo_hash(url: str) -> str:
    import hashlib

    normalized = (url or "").strip().lower().split("?")[0]
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def blacklist_profile_photos(profile: Profile, *, report: Report | None = None, reason: str = "") -> int:
    from core.controllers.explore_controller import collect_photos

    added = 0
    for url in collect_photos(profile, limit=12):
        digest = _photo_hash(url)
        _, created = PhotoBlacklist.objects.get_or_create(
            photo_hash=digest,
            defaults={
                "source_url": url[:500],
                "profile": profile,
                "report": report,
                "reason": reason or "Signalement modération",
            },
        )
        if created:
            added += 1
    return added


def dismiss_report(report_id, admin: Profile, notes: str = "") -> Report:
    return resolve_report(
        report_id,
        admin,
        ReportStatus.DISMISSED,
        resolution="dismissed",
        notes=notes or "Signalement infondé — ignoré.",
    )


def warn_reported_user(report_id, admin: Profile, notes: str = "") -> Report:
    from core.controllers import notification_controller

    report = Report.objects.select_related("reported_profile").get(pk=report_id)
    target = report.reported_profile
    warning_text = notes.strip() or (
        "Un comportement signalé sur TimaLove ne respecte pas nos règles. "
        "Merci de corriger votre profil et vos échanges."
    )
    if target:
        notification_controller.create(
            user=target,
            type=NotificationType.MODERATION_WARNING,
            title="Avertissement officiel TimaLove",
            message=warning_text,
            related_user=report.reporter,
        )
    return resolve_report(
        report_id,
        admin,
        ReportStatus.RESOLVED,
        resolution="warned",
        notes=warning_text,
    )


def ban_from_report(report_id, admin: Profile, notes: str = "") -> Report:
    report = Report.objects.select_related("reported_profile").get(pk=report_id)
    reason = notes.strip() or report.get_reason_display() or report.reason
    if report.reported_profile:
        ban_profile(report.reported_profile, reason=reason, admin=admin)
    return resolve_report(
        report_id,
        admin,
        ReportStatus.ACTION_TAKEN,
        resolution="banned",
        notes=reason,
    )


def blacklist_from_report(report_id, admin: Profile, notes: str = "") -> Report:
    report = Report.objects.select_related("reported_profile").get(pk=report_id)
    added = 0
    if report.reported_profile:
        added = blacklist_profile_photos(
            report.reported_profile,
            report=report,
            reason=notes or report.get_reason_display(),
        )
    note = notes.strip() or f"{added} empreinte(s) photo ajoutée(s) à la liste noire."
    return resolve_report(
        report_id,
        admin,
        ReportStatus.ACTION_TAKEN,
        resolution="photo_blacklisted",
        notes=note,
    )


def resolve_report(report_id, admin: Profile, status: str, resolution: str | None = None, notes: str | None = None):
    r = Report.objects.get(pk=report_id)
    r.status = status
    r.resolution = resolution
    r.admin_note = notes
    r.resolved_by = admin
    r.reviewed_at = timezone.now()
    r.save()
    if resolution == "banned" and r.reported_profile:
        ban_profile(r.reported_profile, reason=notes or r.reason, admin=admin)
    return r


def ban_profile(profile: Profile, reason: str = "", admin: Profile | None = None) -> None:
    profile.banned_at = timezone.now()
    profile.ban_reason = reason
    profile.is_hidden = True
    profile.save(update_fields=["banned_at", "ban_reason", "is_hidden", "updated_at"])
    email_n = (profile.email or "").strip().lower() or None
    phone_n = profile.phone or None
    if email_n or phone_n:
        BannedIdentity.objects.get_or_create(
            email_normalized=email_n,
            phone_normalized=phone_n,
            defaults={"profile": profile, "reason": reason},
        )


def has_blocked(blocker: Profile, blocked_id) -> bool:
    return BlockedUser.objects.filter(blocker=blocker, blocked_id=blocked_id).exists()


def is_blocked_between(a: Profile, b: Profile) -> bool:
    return BlockedUser.objects.filter(
        models.Q(blocker=a, blocked=b) | models.Q(blocker=b, blocked=a)
    ).exists()


def block_user(blocker: Profile, blocked_id) -> tuple[bool, str]:
    if str(blocker.id) == str(blocked_id):
        return False, "Action invalide."
    blocked = Profile.objects.filter(pk=blocked_id).first()
    if not blocked:
        return False, "Profil introuvable."
    BlockedUser.objects.get_or_create(blocker=blocker, blocked=blocked)
    return True, "Utilisateur bloqué."


def unblock_user(blocker: Profile, blocked_id) -> None:
    BlockedUser.objects.filter(blocker=blocker, blocked_id=blocked_id).delete()


def list_blocked(blocker: Profile):
    return list(
        BlockedUser.objects.filter(blocker=blocker).select_related("blocked").order_by("-created_at")
    )
