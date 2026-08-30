"""Controllers admin — dashboard, membres, modération."""

from __future__ import annotations

from datetime import datetime, timedelta

from django.core.paginator import Paginator
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from core.models import (
    BannedIdentity,
    CoachingRequest,
    Match,
    Message,
    Profile,
    Report,
    Swipe,
    Testimonial,
    Transaction,
)
from core.models.choices import (
    CoachingStatus,
    RegistrationStatus,
    ReportStatus,
    SubscriptionStatus,
    SubscriptionTier,
    TransactionStatus,
    TransactionType,
)

ADMIN_MODERATION_REASONS: list[tuple[str, str]] = [
    ("spam", "Spam / faux profil"),
    ("harassment", "Harcèlement"),
    ("inappropriate", "Contenu inapproprié"),
    ("scam", "Arnaque / fraude"),
    ("identity", "Usurpation d'identité"),
    ("other", "Autre"),
]


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
        "members_banned": Profile.objects.filter(role="member", banned_at__isnull=False).count(),
        "members_suspended": Profile.objects.filter(role="member", suspended_at__isnull=False).count(),
        "matches_active": Match.objects.filter(status="active").count(),
        "messages_week": Message.objects.filter(created_at__gte=week).count(),
        "swipes_week": Swipe.objects.filter(created_at__gte=week).count(),
        "revenue_paid": Transaction.objects.filter(status=TransactionStatus.PAID).count(),
        "coaching_pending": CoachingRequest.objects.filter(status=CoachingStatus.PENDING).count(),
        "reports_pending": Report.objects.filter(status=ReportStatus.PENDING).count(),
        "testimonials_pending": Testimonial.objects.filter(is_published=False).count(),
        "subscriptions_active": Profile.objects.filter(
            role="member",
            subscription_status=SubscriptionStatus.ACTIVE,
        ).exclude(subscription_tier=SubscriptionTier.FREE).count(),
    }


def _format_fcfa(amount: int) -> str:
    return f"{int(amount):,}".replace(",", "\u202f")


def _chart_day_labels(days: int = 30) -> tuple[list[str], list[str]]:
    """Retourne (labels ISO, labels affichage jj/mm)."""
    today = timezone.localdate()
    iso_labels: list[str] = []
    display_labels: list[str] = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        iso_labels.append(day.isoformat())
        display_labels.append(day.strftime("%d/%m"))
    return iso_labels, display_labels


def _daily_series(model, iso_labels: list[str], **filters) -> list[int]:
    start_day = timezone.localdate() - timedelta(days=len(iso_labels) - 1)
    start = timezone.make_aware(datetime.combine(start_day, datetime.min.time()))
    rows = (
        model.objects.filter(created_at__gte=start, **filters)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"))
    )
    by_day = {row["day"].isoformat(): row["count"] for row in rows if row["day"]}
    return [by_day.get(label, 0) for label in iso_labels]


def _pct_delta(current: float, previous: float) -> tuple[float, str]:
    if previous == 0:
        delta = 100.0 if current > 0 else 0.0
    else:
        delta = ((current - previous) / previous) * 100
    if delta > 0:
        trend = "up"
    elif delta < 0:
        trend = "down"
    else:
        trend = "flat"
    return round(delta, 1), trend


def _month_bounds(reference: datetime | None = None) -> tuple[datetime, datetime, datetime, datetime]:
    ref = reference or timezone.now()
    local_today = timezone.localdate()
    month_start = local_today.replace(day=1)
    prev_month_end = month_start - timedelta(days=1)
    prev_month_start = prev_month_end.replace(day=1)
    month_start_dt = timezone.make_aware(datetime.combine(month_start, datetime.min.time()))
    prev_month_start_dt = timezone.make_aware(datetime.combine(prev_month_start, datetime.min.time()))
    prev_month_end_dt = timezone.make_aware(datetime.combine(prev_month_end, datetime.max.time()))
    return month_start_dt, ref, prev_month_start_dt, prev_month_end_dt


def _revenue_sum(start: datetime, end: datetime) -> int:
    return int(
        Transaction.objects.filter(
            status=TransactionStatus.PAID,
            paid_at__gte=start,
            paid_at__lte=end,
        ).aggregate(total=Sum("amount"))["total"]
        or 0
    )


def dashboard_kpis() -> list[dict]:
    now = timezone.now()
    today = timezone.localdate()
    today_start = timezone.make_aware(datetime.combine(today, datetime.min.time()))
    yesterday_start = today_start - timedelta(days=1)
    month_start_dt, _, prev_month_start_dt, prev_month_end_dt = _month_bounds(now)
    week_ago = now - timedelta(days=7)

    mrr_current = _revenue_sum(month_start_dt, now)
    mrr_previous = _revenue_sum(prev_month_start_dt, prev_month_end_dt)
    mrr_delta, mrr_trend = _pct_delta(mrr_current, mrr_previous)

    from django.contrib.auth import get_user_model

    User = get_user_model()
    dau_current = User.objects.filter(
        last_login__gte=now - timedelta(hours=24),
        profile__role="member",
    ).count()
    dau_previous = User.objects.filter(
        last_login__gte=now - timedelta(hours=48),
        last_login__lt=now - timedelta(hours=24),
        profile__role="member",
    ).count()
    dau_delta, dau_trend = _pct_delta(dau_current, dau_previous)

    signups_today = Profile.objects.filter(role="member", created_at__gte=today_start).count()
    signups_yesterday = Profile.objects.filter(
        role="member",
        created_at__gte=yesterday_start,
        created_at__lt=today_start,
    ).count()
    signup_delta, signup_trend = _pct_delta(signups_today, signups_yesterday)

    paid_current = (
        Profile.objects.filter(role="member", subscription_status=SubscriptionStatus.ACTIVE)
        .exclude(subscription_tier=SubscriptionTier.FREE)
        .count()
    )
    new_paid_7d = (
        Transaction.objects.filter(
            type=TransactionType.SUBSCRIPTION,
            status=TransactionStatus.PAID,
            paid_at__gte=week_ago,
        )
        .values("user")
        .distinct()
        .count()
    )
    expired_7d = Profile.objects.filter(
        role="member",
        subscription_status=SubscriptionStatus.EXPIRED,
        updated_at__gte=week_ago,
    ).count()
    paid_previous = max(0, paid_current - new_paid_7d + expired_7d)
    paid_delta, paid_trend = _pct_delta(paid_current, paid_previous)

    matches_current = Match.objects.filter(created_at__gte=now - timedelta(hours=24)).count()
    matches_previous = Match.objects.filter(
        created_at__gte=now - timedelta(hours=48),
        created_at__lt=now - timedelta(hours=24),
    ).count()
    matches_delta, matches_trend = _pct_delta(matches_current, matches_previous)

    reports_pending = Report.objects.filter(status=ReportStatus.PENDING).count()
    reports_previous = Report.objects.filter(
        status=ReportStatus.PENDING,
        created_at__lt=week_ago,
    ).count()
    reports_delta, reports_trend = _pct_delta(reports_pending, reports_previous)

    return [
        {
            "id": "mrr",
            "label": "Revenus du mois",
            "value": mrr_current,
            "value_label": _format_fcfa(mrr_current),
            "suffix": "FCFA",
            "delta_pct": mrr_delta,
            "trend": mrr_trend,
            "hint": "vs mois précédent",
        },
        {
            "id": "dau",
            "label": "Utilisateurs actifs (24 h)",
            "value": dau_current,
            "value_label": str(dau_current),
            "suffix": "",
            "delta_pct": dau_delta,
            "trend": dau_trend,
            "hint": "vs veille",
        },
        {
            "id": "signups",
            "label": "Nouveaux inscrits",
            "value": signups_today,
            "value_label": str(signups_today),
            "suffix": "aujourd'hui",
            "delta_pct": signup_delta,
            "trend": signup_trend,
            "hint": "vs hier",
        },
        {
            "id": "paid",
            "label": "Abonnés payants actifs",
            "value": paid_current,
            "value_label": str(paid_current),
            "suffix": "",
            "delta_pct": paid_delta,
            "trend": paid_trend,
            "hint": "vs semaine passée",
        },
        {
            "id": "matches",
            "label": "Matchs du jour",
            "value": matches_current,
            "value_label": str(matches_current),
            "suffix": "24 h",
            "delta_pct": matches_delta,
            "trend": matches_trend,
            "hint": "vs veille",
        },
        {
            "id": "reports",
            "label": "Signalements en attente",
            "value": reports_pending,
            "value_label": str(reports_pending),
            "suffix": "",
            "delta_pct": reports_delta,
            "trend": reports_trend,
            "hint": "vs semaine passée",
            "alert": reports_pending >= 5,
        },
    ]


def _daily_amount_series(iso_labels: list[str], **filters) -> list[int]:
    start_day = timezone.localdate() - timedelta(days=len(iso_labels) - 1)
    start = timezone.make_aware(datetime.combine(start_day, datetime.min.time()))
    rows = (
        Transaction.objects.filter(status=TransactionStatus.PAID, paid_at__gte=start, **filters)
        .annotate(day=TruncDate("paid_at"))
        .values("day")
        .annotate(total=Sum("amount"))
    )
    by_day = {row["day"].isoformat(): int(row["total"] or 0) for row in rows if row["day"]}
    return [by_day.get(label, 0) for label in iso_labels]


def _daily_banned_series(iso_labels: list[str]) -> list[int]:
    start_day = timezone.localdate() - timedelta(days=len(iso_labels) - 1)
    start = timezone.make_aware(datetime.combine(start_day, datetime.min.time()))
    rows = (
        Profile.objects.filter(role="member", banned_at__gte=start)
        .annotate(day=TruncDate("banned_at"))
        .values("day")
        .annotate(count=Count("id"))
    )
    by_day = {row["day"].isoformat(): row["count"] for row in rows if row["day"]}
    return [by_day.get(label, 0) for label in iso_labels]


def _engagement_funnel() -> dict:
    members = Profile.objects.filter(role="member").count()
    completed = Profile.objects.filter(role="member", onboarding_completed=True).count()
    swipers = Swipe.objects.values("swiper_id").distinct().count()
    match_ids = set(Match.objects.values_list("user_1_id", flat=True)) | set(
        Match.objects.values_list("user_2_id", flat=True)
    )
    matchers = len(match_ids)
    paying = (
        Profile.objects.filter(role="member", subscription_status=SubscriptionStatus.ACTIVE)
        .exclude(subscription_tier=SubscriptionTier.FREE)
        .count()
    )
    return {
        "labels": [
            "Inscriptions",
            "Profils complétés",
            "≥ 1 swipe",
            "≥ 1 match",
            "Convertis payants",
        ],
        "values": [members, completed, swipers, matchers, paying],
    }


def _top_cities(limit: int = 8) -> dict:
    rows = (
        Profile.objects.filter(role="member")
        .exclude(Q(city__isnull=True) | Q(city=""))
        .values("city")
        .annotate(count=Count("id"))
        .order_by("-count")[:limit]
    )
    return {
        "labels": [row["city"] for row in rows],
        "values": [row["count"] for row in rows],
    }


def dashboard_recent_activity() -> dict:
    transactions = []
    for tx in Transaction.objects.select_related("user").order_by("-created_at")[:8]:
        transactions.append(
            {
                "id": str(tx.id).replace("-", "")[:8],
                "type": tx.get_type_display(),
                "amount_label": _format_fcfa(tx.amount),
                "status": tx.status,
                "status_label": tx.get_status_display(),
                "created_at": tx.created_at,
            }
        )
    reports = list(
        Report.objects.filter(status=ReportStatus.PENDING)
        .select_related("reporter", "reported_profile")
        .order_by("-created_at")[:5]
    )
    return {"transactions": transactions, "reports": reports}


def dashboard_analytics(days: int = 30) -> dict:
    gender_map = {"male": "Hommes", "female": "Femmes"}

    iso_labels, display_labels = _chart_day_labels(days)
    week = timezone.now() - timedelta(days=7)

    gender_rows = (
        Profile.objects.filter(role="member")
        .values("gender")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    gender_labels = []
    gender_values = []
    for row in gender_rows:
        gender_labels.append(gender_map.get(row["gender"], "Non renseigné"))
        gender_values.append(row["count"])

    status_rows = (
        Profile.objects.filter(role="member")
        .values("registration_status")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    status_labels = []
    status_values = []
    status_map = dict(RegistrationStatus.choices)
    for row in status_rows:
        status_labels.append(status_map.get(row["registration_status"], row["registration_status"]))
        status_values.append(row["count"])

    tier_rows = (
        Profile.objects.filter(role="member", subscription_status=SubscriptionStatus.ACTIVE)
        .exclude(subscription_tier=SubscriptionTier.FREE)
        .values("subscription_tier")
        .annotate(count=Count("id"))
        .order_by("-count")
    )
    tier_map = dict(SubscriptionTier.choices)
    tier_labels = [tier_map.get(r["subscription_tier"], r["subscription_tier"]) for r in tier_rows]
    tier_values = [r["count"] for r in tier_rows]

    likes_week = Swipe.objects.filter(created_at__gte=week, is_like=True).count()
    passes_week = Swipe.objects.filter(created_at__gte=week, is_like=False).count()
    super_week = Swipe.objects.filter(created_at__gte=week, is_super_like=True).count()

    one_shot_types = [TransactionType.BOOST, TransactionType.COACHING]
    subscription_revenue = _daily_amount_series(
        iso_labels,
        type=TransactionType.SUBSCRIPTION,
    )
    one_shot_revenue = _daily_amount_series(iso_labels, type__in=one_shot_types)

    return {
        "labels": display_labels,
        "activity": {
            "members": _daily_series(Profile, iso_labels, role="member"),
            "messages": _daily_series(Message, iso_labels),
            "swipes": _daily_series(Swipe, iso_labels),
            "matches": _daily_series(Match, iso_labels),
            "payments": _daily_series(Transaction, iso_labels, status=TransactionStatus.PAID),
        },
        "revenue": {
            "subscription": subscription_revenue,
            "one_shot": one_shot_revenue,
        },
        "acquisition": {
            "signups": _daily_series(Profile, iso_labels, role="member"),
            "churn": _daily_banned_series(iso_labels),
        },
        "demographics": {
            "gender_labels": gender_labels,
            "gender_values": gender_values,
            "status_labels": status_labels,
            "status_values": status_values,
        },
        "subscriptions": {
            "labels": tier_labels,
            "values": tier_values,
        },
        "engagement_week": {
            "labels": ["Likes", "Passes", "Super likes"],
            "values": [likes_week, passes_week, super_week],
        },
        "funnel": _engagement_funnel(),
        "geography": _top_cities(),
        "moderation": {
            "pending_reports": Report.objects.filter(status=ReportStatus.PENDING).count(),
            "pending_inscriptions": Profile.objects.filter(
                registration_status=RegistrationStatus.PENDING
            ).count(),
            "coaching_pending": CoachingRequest.objects.filter(status=CoachingStatus.PENDING).count(),
        },
    }


def list_inscriptions(
    *,
    search: str = "",
    status: str | None = None,
    page: int = 1,
    per_page: int = 30,
):
    qs = Profile.objects.filter(role="member").order_by("-created_at")
    if status:
        qs = qs.filter(registration_status=status)
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(city__icontains=search)
            | Q(commune__icontains=search)
        )
    paginator = Paginator(qs, per_page)
    return paginator.get_page(page)


def members_summary() -> dict:
    base = Profile.objects.filter(role="member")
    reported_ids = Report.objects.filter(reported_profile__isnull=False).values("reported_profile_id").distinct()
    return {
        "active": base.filter(
            registration_status=RegistrationStatus.APPROVED,
            banned_at__isnull=True,
            suspended_at__isnull=True,
        ).count(),
        "reported": base.filter(id__in=reported_ids).count(),
        "banned": base.filter(banned_at__isnull=False).count(),
        "blocked": base.filter(suspended_at__isnull=False).count(),
        "shadowbanned": base.filter(is_shadowbanned=True).count(),
    }


def mask_email(email: str) -> str:
    email = (email or "").strip()
    if not email or "@" not in email:
        return "—"
    local, domain = email.split("@", 1)
    if len(local) <= 2:
        masked_local = local[:1] + "***"
    else:
        masked_local = local[:2] + "***"
    return f"{masked_local}@{domain}"


def member_pseudonym(profile: Profile) -> str:
    first = (profile.first_name or "").strip()
    last_initial = (profile.last_name or "")[:1].upper()
    if first and last_initial:
        return f"{first} {last_initial}."
    return profile.display_name


def account_status_label(profile: Profile) -> str:
    if profile.banned_at:
        return "Banni"
    if profile.suspended_at:
        return "Suspendu"
    if profile.is_shadowbanned:
        return "Shadowban"
    if profile.registration_status == RegistrationStatus.PENDING:
        return "En attente"
    if profile.registration_status == RegistrationStatus.REJECTED:
        return "Rejeté"
    return "Actif"


def subscription_kind_label(profile: Profile) -> str:
    from core.controllers import subscription_controller

    kind = subscription_controller.tier_of(profile)
    if kind == subscription_controller.TIER_VIP:
        return "VIP"
    if kind == subscription_controller.TIER_PASS_FEMME:
        return "Pass Femme"
    if kind == subscription_controller.TIER_PREMIUM:
        return "Premium"
    return "Gratuit"


def last_access_label(profile: Profile) -> str:
    user = getattr(profile, "user", None)
    dt = None
    if user and user.last_login:
        dt = user.last_login
    elif profile.last_active_at:
        dt = profile.last_active_at
    if not dt:
        return "—"
    return timezone.localtime(dt).strftime("%d/%m/%Y %H:%M")


def list_members(
    *,
    search: str = "",
    subscription_tier: str | None = None,
    subscription_kind: str | None = None,
    account_status: str | None = None,
    banned: str | None = None,
    blocked: str | None = None,
    page: int = 1,
    per_page: int = 30,
):
    qs = (
        Profile.objects.filter(role="member")
        .select_related("user")
        .annotate(reports_count=Count("reports_received"))
        .order_by("-created_at")
    )
    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(email__icontains=search)
            | Q(phone__icontains=search)
            | Q(city__icontains=search)
            | Q(commune__icontains=search)
        )
    if account_status == "active":
        qs = qs.filter(
            banned_at__isnull=True,
            suspended_at__isnull=True,
            is_shadowbanned=False,
            registration_status=RegistrationStatus.APPROVED,
        )
    elif account_status == "banned":
        qs = qs.filter(banned_at__isnull=False)
    elif account_status == "suspended":
        qs = qs.filter(suspended_at__isnull=False)
    elif account_status == "pending":
        qs = qs.filter(registration_status=RegistrationStatus.PENDING)
    elif account_status == "shadowbanned":
        qs = qs.filter(is_shadowbanned=True)
    if subscription_kind == "free":
        qs = qs.filter(
            Q(subscription_tier=SubscriptionTier.FREE)
            | ~Q(subscription_status=SubscriptionStatus.ACTIVE)
        )
    elif subscription_kind == "premium":
        qs = qs.filter(
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_tier__in=[
                SubscriptionTier.PREMIUM_1M,
                SubscriptionTier.PREMIUM_10D,
                SubscriptionTier.PREMIUM_2M,
                SubscriptionTier.PASS_AMOUR,
                SubscriptionTier.JOURNEE_AMOUREUSE,
                SubscriptionTier.ETERNITE,
            ],
        )
    elif subscription_kind == "vip":
        qs = qs.filter(
            subscription_status=SubscriptionStatus.ACTIVE,
            subscription_tier__in=[
                SubscriptionTier.VIP_1M,
                SubscriptionTier.VIP_2M,
                SubscriptionTier.VIP_FEMME_1W,
                SubscriptionTier.PASS_FEMME,
            ],
        )
    if subscription_tier:
        qs = qs.filter(subscription_tier=subscription_tier)
    if banned == "yes":
        qs = qs.filter(banned_at__isnull=False)
    elif banned == "no":
        qs = qs.filter(banned_at__isnull=True)
    if blocked == "yes":
        qs = qs.filter(suspended_at__isnull=False)
    elif blocked == "no":
        qs = qs.filter(suspended_at__isnull=True)
    paginator = Paginator(qs, per_page)
    return paginator.get_page(page)


def get_member(profile_id) -> Profile | None:
    return (
        Profile.objects.select_related("user")
        .filter(pk=profile_id, role="member")
        .first()
    )


def member_activity(profile: Profile) -> dict:
    swipes_sent = Swipe.objects.filter(swiper=profile).count()
    swipes_received = Swipe.objects.filter(swiped=profile).count()
    return {
        "likes_sent": Swipe.objects.filter(swiper=profile, is_like=True).count(),
        "likes_received": Swipe.objects.filter(swiped=profile, is_like=True).count(),
        "swipes_sent": swipes_sent,
        "swipes_received": swipes_received,
        "matches": Match.objects.filter(
            Q(user_1=profile) | Q(user_2=profile),
            status="active",
        ).count(),
        "matches_total": Match.objects.filter(Q(user_1=profile) | Q(user_2=profile)).count(),
        "messages_sent": Message.objects.filter(sender=profile).count(),
        "reports_against": Report.objects.filter(reported_profile=profile).count(),
        "transactions": list(
            Transaction.objects.filter(user=profile).order_by("-created_at")[:15]
        ),
    }


def member_public_photos(profile: Profile) -> list[str]:
    from core.controllers.explore_controller import collect_photos

    return collect_photos(profile, limit=6)


def member_detail_context(profile: Profile) -> dict:
    user = profile.user
    return {
        "pseudonym": member_pseudonym(profile),
        "masked_email": mask_email(profile.email or ""),
        "account_status": account_status_label(profile),
        "subscription_label": subscription_kind_label(profile),
        "last_access": last_access_label(profile),
        "photos": member_public_photos(profile),
        "verification_score": profile.face_match_score,
        "has_verification_photo": bool(profile.verification_photo_url),
    }


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


def unban_member(profile_id) -> Profile:
    p = Profile.objects.get(pk=profile_id)
    p.banned_at = None
    p.ban_reason = ""
    p.is_hidden = False
    p.is_shadowbanned = False
    p.save(update_fields=["banned_at", "ban_reason", "is_hidden", "is_shadowbanned", "updated_at"])
    BannedIdentity.objects.filter(profile=p).delete()
    return p


def suspend_member(profile_id, reason: str = "") -> Profile:
    p = Profile.objects.get(pk=profile_id)
    p.suspended_at = timezone.now()
    p.is_hidden = True
    if reason:
        p.ban_reason = reason
    p.save(update_fields=["suspended_at", "is_hidden", "ban_reason", "updated_at"])
    return p


def unsuspend_member(profile_id) -> Profile:
    p = Profile.objects.get(pk=profile_id)
    p.suspended_at = None
    if not p.banned_at:
        p.is_hidden = False
        p.ban_reason = ""
    p.save(update_fields=["suspended_at", "is_hidden", "ban_reason", "updated_at"])
    return p


def set_member_hidden(profile_id, hidden: bool) -> Profile:
    p = Profile.objects.get(pk=profile_id)
    p.is_hidden = hidden
    p.save(update_fields=["is_hidden", "updated_at"])
    return p


def shadowban_member(profile_id, enabled: bool = True) -> Profile:
    p = Profile.objects.get(pk=profile_id)
    p.is_shadowbanned = enabled
    p.save(update_fields=["is_shadowbanned", "updated_at"])
    return p


def reset_member_password(profile_id, new_password: str | None = None) -> str:
    import secrets

    from django.contrib.auth import get_user_model

    User = get_user_model()
    profile = Profile.objects.select_related("user").get(pk=profile_id)
    if not profile.user_id:
        raise ValueError("Compte utilisateur introuvable.")
    password = (new_password or "").strip() or secrets.token_urlsafe(9)
    if len(password) < 8:
        raise ValueError("Le mot de passe doit contenir au moins 8 caractères.")
    user = User.objects.get(pk=profile.user_id)
    user.set_password(password)
    user.save(update_fields=["password"])
    return password


def logout_member_sessions(profile_id) -> int:
    from django.contrib.sessions.models import Session

    profile = Profile.objects.select_related("user").get(pk=profile_id)
    if not profile.user_id:
        return 0
    user_id = str(profile.user_id)
    deleted = 0
    for session in Session.objects.all().iterator():
        try:
            data = session.get_decoded()
        except Exception:
            continue
        if str(data.get("_auth_user_id")) == user_id:
            session.delete()
            deleted += 1
    return deleted


def force_verify_member(profile_id) -> Profile:
    p = Profile.objects.get(pk=profile_id)
    p.is_verified = True
    if p.registration_status == RegistrationStatus.PENDING:
        p.registration_status = RegistrationStatus.APPROVED
    p.save(update_fields=["is_verified", "registration_status", "updated_at"])
    return p


def revoke_verification(profile_id) -> Profile:
    p = Profile.objects.get(pk=profile_id)
    p.is_verified = False
    p.save(update_fields=["is_verified", "updated_at"])
    return p


def delete_member_account(profile_id) -> None:
    from django.contrib.auth import get_user_model

    User = get_user_model()
    profile = Profile.objects.select_related("user").filter(pk=profile_id, role="member").first()
    if profile is None:
        raise ValueError("Membre introuvable.")
    if profile.user_id:
        User.objects.filter(pk=profile.user_id).delete()
    else:
        profile.delete()


def resolve_moderation_reason(reason_key: str, custom: str = "") -> str:
    labels = dict(ADMIN_MODERATION_REASONS)
    if reason_key in labels:
        base = labels[reason_key]
        if reason_key == "other" and custom.strip():
            return custom.strip()
        return base
    return custom.strip() or "Action administrateur"


def grant_subscription(profile_id, tier: str, days: int = 30) -> Profile:
    p = Profile.objects.get(pk=profile_id)
    if tier == SubscriptionTier.FREE:
        p.subscription_tier = SubscriptionTier.FREE
        p.subscription_status = SubscriptionStatus.INACTIVE
        p.subscription_end_date = None
    else:
        p.subscription_tier = tier
        p.subscription_status = SubscriptionStatus.ACTIVE
        p.subscription_end_date = timezone.now() + timedelta(days=max(1, days))
    p.save(
        update_fields=[
            "subscription_tier",
            "subscription_status",
            "subscription_end_date",
            "updated_at",
        ]
    )
    return p


def revoke_subscription(profile_id) -> Profile:
    return grant_subscription(profile_id, SubscriptionTier.FREE, 0)


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


def payments_summary() -> dict:
    base = Transaction.objects.all()
    paid_qs = base.filter(status=TransactionStatus.PAID)
    failed_qs = base.filter(status=TransactionStatus.FAILED)
    pending_qs = base.filter(status=TransactionStatus.PENDING)

    total_amount = int(base.aggregate(total=Sum("amount"))["total"] or 0)
    paid_amount = int(paid_qs.aggregate(total=Sum("amount"))["total"] or 0)
    failed_amount = int(failed_qs.aggregate(total=Sum("amount"))["total"] or 0)
    pending_amount = int(pending_qs.aggregate(total=Sum("amount"))["total"] or 0)

    return {
        "total_amount": total_amount,
        "paid_amount": paid_amount,
        "failed_amount": failed_amount,
        "pending_amount": pending_amount,
        "total_amount_label": _format_fcfa(total_amount),
        "paid_amount_label": _format_fcfa(paid_amount),
        "failed_amount_label": _format_fcfa(failed_amount),
        "pending_amount_label": _format_fcfa(pending_amount),
        "total_count": base.count(),
        "paid_count": paid_qs.count(),
        "failed_count": failed_qs.count(),
        "pending_count": pending_qs.count(),
    }


def list_transactions(limit: int = 100, status: str | None = None):
    qs = Transaction.objects.select_related("user").order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    return list(qs[:limit])


def list_banned_identities(limit: int = 100):
    return list(
        BannedIdentity.objects.select_related("profile")
        .order_by("-created_at")[:limit]
    )
