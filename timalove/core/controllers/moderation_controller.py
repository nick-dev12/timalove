"""Témoignages, reports, blocks."""

from __future__ import annotations

from django.utils import timezone

from core.models import BannedIdentity, BlockedUser, Profile, Report, Testimonial
from core.models.choices import ReportStatus


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
    reported = None
    if data.get("reported_profile_id"):
        reported = Profile.objects.filter(pk=data["reported_profile_id"]).first()
    return Report.objects.create(
        reporter=reporter,
        reported_profile=reported,
        reason=data.get("reason", "other"),
        message=data.get("message"),
        report_kind=data.get("report_kind", "profile"),
    )


def list_reports(status: str | None = None):
    qs = Report.objects.select_related("reporter", "reported_profile").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    return list(qs)


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
