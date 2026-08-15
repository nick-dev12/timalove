"""Controllers admin."""

from __future__ import annotations

from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from core.models import (
    CoachingRequest,
    Match,
    Message,
    Profile,
    Report,
    Swipe,
    Testimonial,
    Transaction,
)
from core.models.choices import CoachingStatus, RegistrationStatus, ReportStatus, TransactionStatus


def dashboard_stats() -> dict:
    now = timezone.now()
    week = now - timedelta(days=7)
    return {
        "members_total": Profile.objects.filter(role="member").count(),
        "members_approved": Profile.objects.filter(
            role="member", registration_status=RegistrationStatus.APPROVED
        ).count(),
        "pending_registrations": Profile.objects.filter(
            registration_status=RegistrationStatus.PENDING
        ).count(),
        "matches_active": Match.objects.filter(status="active").count(),
        "messages_week": Message.objects.filter(created_at__gte=week).count(),
        "swipes_week": Swipe.objects.filter(created_at__gte=week).count(),
        "revenue_paid": Transaction.objects.filter(status=TransactionStatus.PAID).count(),
        "coaching_pending": CoachingRequest.objects.filter(status=CoachingStatus.PENDING).count(),
        "reports_pending": Report.objects.filter(status=ReportStatus.PENDING).count(),
        "testimonials_pending": Testimonial.objects.filter(is_published=False).count(),
    }


def list_profiles(status: str | None = None, search: str = ""):
    qs = Profile.objects.filter(role="member").order_by("-created_at")
    if status:
        qs = qs.filter(registration_status=status)
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(city__icontains=search)
        )
    return list(qs[:200])


def set_registration_status(profile_id, status: str, rejection_reason: str | None = None) -> Profile:
    from core.controllers import notification_controller
    from core.models.choices import NotificationType

    p = Profile.objects.get(pk=profile_id)
    p.registration_status = status
    if rejection_reason:
        p.rejection_reason = rejection_reason
    if status == RegistrationStatus.APPROVED:
        p.is_verified = True
        notification_controller.create(
            user=p,
            type=NotificationType.PROFILE_APPROVED,
            title="Profil approuvé",
            message="Votre profil a été validé. Bienvenue sur TimaLove !",
        )
    elif status == RegistrationStatus.REJECTED:
        notification_controller.create(
            user=p,
            type=NotificationType.PROFILE_REJECTED,
            title="Profil refusé",
            message=rejection_reason or "Votre profil n'a pas été validé.",
        )
    p.save()
    return p


def recent_activities(limit: int = 50) -> list[dict]:
    swipes = (
        Swipe.objects.select_related("swiper", "swiped")
        .filter(is_like=True)
        .order_by("-created_at")[:limit]
    )
    return [
        {
            "type": "like",
            "from": s.swiper,
            "to": s.swiped,
            "super": s.is_super_like,
            "at": s.created_at,
        }
        for s in swipes
    ]


def list_transactions(limit: int = 100):
    return list(
        Transaction.objects.select_related("user").order_by("-created_at")[:limit]
    )
