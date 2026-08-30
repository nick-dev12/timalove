"""CRM — campagnes push, email et popups in-app segmentés."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from core.models.crm import CampaignChannel, CampaignDelivery, CampaignSendMode, CampaignStatus, MarketingCampaign
from core.models.profile import Profile
from core.models.choices import RegistrationStatus, UserRole

DEFAULT_CRM_SETTINGS: dict = {
    "popups_enabled": True,
    "popup_poll_seconds": 45,
    "marketing_push_enabled": True,
    "show_on_login": True,
    "show_on_every_page": True,
    "email_from_name": "TimaLove",
}


def get_crm_settings() -> dict:
    from core.controllers import site_settings_controller

    stored = site_settings_controller.get("crm_settings") or {}
    merged = dict(DEFAULT_CRM_SETTINGS)
    if isinstance(stored, dict):
        merged.update(stored)
    return merged


def save_crm_settings(data: dict) -> dict:
    from core.controllers import site_settings_controller

    current = get_crm_settings()
    for key in DEFAULT_CRM_SETTINGS:
        if key in data:
            current[key] = data[key]
    site_settings_controller.set_value("crm_settings", current)
    return current


def _birthdate_for_min_age(age: int) -> date:
    today = timezone.localdate()
    return date(today.year - age, today.month, today.day)


def segment_profiles(filters: dict | None) -> QuerySet[Profile]:
    filters = filters or {}
    qs = Profile.objects.filter(
        role=UserRole.MEMBER,
        registration_status=RegistrationStatus.APPROVED,
        banned_at__isnull=True,
        is_hidden=False,
    )
    gender = (filters.get("gender") or "").strip()
    if gender:
        qs = qs.filter(gender=gender)
    city = (filters.get("city") or "").strip()
    if city:
        qs = qs.filter(Q(city__icontains=city) | Q(commune__icontains=city))
    tier = (filters.get("subscription_tier") or "").strip()
    if tier:
        qs = qs.filter(subscription_tier=tier)
    sub_status = (filters.get("subscription_status") or "").strip()
    if sub_status:
        qs = qs.filter(subscription_status=sub_status)
    inactive_days = filters.get("inactive_days")
    if inactive_days not in (None, ""):
        try:
            days = max(1, int(inactive_days))
            cutoff = timezone.now() - timedelta(days=days)
            qs = qs.filter(Q(last_active_at__lt=cutoff) | Q(last_active_at__isnull=True))
        except (TypeError, ValueError):
            pass
    try:
        age_min = int(filters["age_min"]) if filters.get("age_min") not in (None, "") else None
    except (TypeError, ValueError):
        age_min = None
    try:
        age_max = int(filters["age_max"]) if filters.get("age_max") not in (None, "") else None
    except (TypeError, ValueError):
        age_max = None
    if age_min is not None:
        qs = qs.filter(date_of_birth__lte=_birthdate_for_min_age(age_min))
    if age_max is not None:
        qs = qs.filter(date_of_birth__gte=_birthdate_for_min_age(age_max))
    return qs.distinct()


def parse_segment_from_post(post) -> dict:
    segment = {}
    for key in ("gender", "city", "subscription_tier", "subscription_status", "inactive_days", "age_min", "age_max"):
        value = (post.get(f"seg_{key}") or "").strip()
        if value:
            segment[key] = value
    return segment


def list_platform_cities(query: str | None = None, *, limit: int = 30) -> list[dict]:
    """Villes distinctes des profils membres (regroupées sans tenir compte de la casse)."""
    from collections import defaultdict
    from django.db.models import Count

    rows = (
        Profile.objects.filter(
            role=UserRole.MEMBER,
            registration_status=RegistrationStatus.APPROVED,
        )
        .exclude(city="")
        .values("city")
        .annotate(count=Count("id"))
        .order_by("-count", "city")
    )
    merged: dict[str, dict] = {}
    best_count: dict[str, int] = defaultdict(int)
    for row in rows:
        name = (row["city"] or "").strip()
        if not name:
            continue
        key = name.lower()
        if key not in merged:
            merged[key] = {"name": name, "count": 0}
        merged[key]["count"] += row["count"]
        if row["count"] >= best_count[key]:
            merged[key]["name"] = name
            best_count[key] = row["count"]

    cities = sorted(merged.values(), key=lambda item: (-item["count"], item["name"].lower()))
    q = (query or "").strip().lower()
    if q:
        cities = [city for city in cities if q in city["name"].lower()]
    cap = max(1, min(limit, 50))
    return cities[:cap]


def campaigns_summary() -> dict:
    base = MarketingCampaign.objects.all()
    sent = base.filter(status=CampaignStatus.SENT)
    delivered = sum(sent.values_list("delivered_count", flat=True))
    opened = sum(sent.values_list("opened_count", flat=True))
    clicked = sum(sent.values_list("clicked_count", flat=True))
    open_rate = round((opened / delivered) * 100, 1) if delivered else 0
    click_rate = round((clicked / delivered) * 100, 1) if delivered else 0
    return {
        "total": base.count(),
        "scheduled": base.filter(status=CampaignStatus.SCHEDULED).count(),
        "sent": sent.count(),
        "delivered": delivered,
        "open_rate": open_rate,
        "click_rate": click_rate,
    }


def list_campaigns(limit: int = 50):
    return list(MarketingCampaign.objects.select_related("created_by").order_by("-created_at")[:limit])


def create_campaign(admin: Profile | None, data: dict) -> MarketingCampaign:
    name = (data.get("name") or "").strip()
    title = (data.get("title") or "").strip()
    body = (data.get("body") or "").strip()
    if not name or not title or not body:
        raise ValueError("Nom, titre et message sont obligatoires.")
    channel = data.get("channel") or CampaignChannel.PUSH_IN_APP
    if channel == CampaignChannel.EMAIL or channel not in CampaignChannel.values:
        channel = CampaignChannel.PUSH_IN_APP
    send_mode = data.get("send_mode") or CampaignSendMode.IMMEDIATE
    scheduled_at = None
    if send_mode == CampaignSendMode.SCHEDULED:
        raw = (data.get("scheduled_at") or "").strip()
        if not raw:
            raise ValueError("Date de programmation requise.")
        try:
            dt = datetime.strptime(raw, "%Y-%m-%dT%H:%M")
            scheduled_at = timezone.make_aware(dt)
        except ValueError as exc:
            raise ValueError("Date de programmation invalide.") from exc
        if scheduled_at <= timezone.now():
            raise ValueError("La date programmée doit être dans le futur.")
    segment = data.get("segment") or {}
    audience = segment_profiles(segment)
    status = CampaignStatus.SCHEDULED if send_mode == CampaignSendMode.SCHEDULED else CampaignStatus.DRAFT
    campaign = MarketingCampaign.objects.create(
        name=name,
        channel=channel,
        title=title,
        body=body,
        image_url=(data.get("image_url") or "").strip()[:500],
        deep_link="/",
        segment=segment,
        send_mode=send_mode,
        scheduled_at=scheduled_at,
        status=status,
        recipients_count=audience.count(),
        created_by=admin,
    )
    if send_mode == CampaignSendMode.IMMEDIATE:
        launch_campaign(campaign.id)
        campaign.refresh_from_db()
    return campaign


def cancel_campaign(campaign_id) -> MarketingCampaign:
    campaign = MarketingCampaign.objects.get(pk=campaign_id)
    if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED}:
        raise ValueError("Seules les campagnes brouillon ou programmées peuvent être annulées.")
    campaign.status = CampaignStatus.CANCELLED
    campaign.save(update_fields=["status", "updated_at"])
    return campaign


def _delivery_channels(campaign: MarketingCampaign) -> list[str]:
    if campaign.channel == CampaignChannel.PUSH_IN_APP:
        return ["push", "in_app"]
    if campaign.channel == CampaignChannel.PUSH:
        return ["push"]
    if campaign.channel == CampaignChannel.IN_APP:
        return ["in_app"]
    if campaign.channel == CampaignChannel.EMAIL:
        return ["email"]
    return ["in_app"]


def _broadcast_in_app(profile_id, delivery: CampaignDelivery, campaign: MarketingCampaign) -> None:
    from asgiref.sync import async_to_sync
    from channels.layers import get_channel_layer

    layer = get_channel_layer()
    if not layer:
        return
    payload = popup_payload(delivery, campaign)
    payload["event"] = "notification"
    async_to_sync(layer.group_send)(
        f"notif_{profile_id}",
        {"type": "notify", "payload": payload},
    )


def popup_payload(delivery: CampaignDelivery, campaign: MarketingCampaign) -> dict:
    return {
        "id": str(delivery.id),
        "kind": "marketing",
        "type": "marketing",
        "campaign_id": str(campaign.id),
        "title": campaign.title,
        "message": campaign.body,
        "image_url": campaign.image_url or "",
        "url": campaign.deep_link or "/",
        "delivery_id": str(delivery.id),
    }


@transaction.atomic
def execute_campaign(campaign_id) -> dict:
    campaign = MarketingCampaign.objects.select_for_update().get(pk=campaign_id)
    if campaign.status in {CampaignStatus.SENT, CampaignStatus.CANCELLED}:
        return {"skipped": True, "reason": campaign.status}
    if campaign.send_mode == CampaignSendMode.SCHEDULED and campaign.scheduled_at:
        if campaign.scheduled_at > timezone.now() and campaign.status != CampaignStatus.SENDING:
            return {"skipped": True, "reason": "not_due"}

    campaign.status = CampaignStatus.SENDING
    campaign.save(update_fields=["status", "updated_at"])

    profiles = list(segment_profiles(campaign.segment))
    campaign.recipients_count = len(profiles)
    settings = get_crm_settings()
    channels = _delivery_channels(campaign)

    for profile in profiles:
        delivery, created = CampaignDelivery.objects.get_or_create(
            campaign=campaign,
            profile=profile,
            defaults={"channel": campaign.channel},
        )
        if not created and delivery.push_sent and delivery.email_sent:
            continue

        if "email" in channels and not delivery.email_sent:
            if _send_campaign_email(profile, campaign, delivery):
                delivery.email_sent = True
        if "push" in channels and settings.get("marketing_push_enabled", True) and not delivery.push_sent:
            if _send_campaign_push(profile, campaign, delivery):
                delivery.push_sent = True
        if "in_app" in channels and settings.get("popups_enabled", True):
            _broadcast_in_app(profile.id, delivery, campaign)
        delivery.save()

    campaign.delivered_count = CampaignDelivery.objects.filter(campaign=campaign).count()
    campaign.status = CampaignStatus.SENT
    campaign.sent_at = timezone.now()
    campaign.save(
        update_fields=["recipients_count", "delivered_count", "status", "sent_at", "updated_at"]
    )
    return {"sent": campaign.delivered_count, "recipients": campaign.recipients_count}


def _send_campaign_push(profile: Profile, campaign: MarketingCampaign, delivery: CampaignDelivery) -> bool:
    from core.controllers import push_controller

    result = push_controller.send_campaign_push(
        profile=profile,
        title=campaign.title,
        body=campaign.body,
        url=campaign.deep_link,
        image_url=campaign.image_url,
        delivery_id=str(delivery.id),
        campaign_id=str(campaign.id),
    )
    return bool(result.get("sent"))


def _send_campaign_email(profile: Profile, campaign: MarketingCampaign, delivery: CampaignDelivery) -> bool:
    from core.controllers import email_controller
    from core.controllers.auth_controller import is_synthetic_email, normalize_email
    from django.conf import settings

    raw = profile.email or profile.user.email or ""
    email = normalize_email(raw) if raw else ""
    if not email or is_synthetic_email(email):
        return False
    track_url = f"{settings.SITE_URL.rstrip('/')}/api/crm/track/{delivery.id}/click/"
    img = f'<p><img src="{campaign.image_url}" alt="" style="max-width:100%;border-radius:12px"></p>' if campaign.image_url else ""
    html = (
        f"<p>{campaign.body}</p>{img}"
        f'<p><a href="{track_url}" style="color:#E8637A;font-weight:bold">Voir sur TimaLove</a></p>'
    )
    ok = email_controller.send_email(email, campaign.title, html, text=campaign.body)
    return ok


def launch_campaign(campaign_id) -> MarketingCampaign:
    campaign = MarketingCampaign.objects.get(pk=campaign_id)
    if campaign.status not in {CampaignStatus.DRAFT, CampaignStatus.SCHEDULED}:
        raise ValueError("Cette campagne ne peut plus être lancée.")
    campaign.status = CampaignStatus.SENDING
    campaign.save(update_fields=["status", "updated_at"])
    _dispatch_campaign_send(campaign.id)
    campaign.refresh_from_db()
    return campaign


def republish_campaign(campaign_id, admin: Profile | None = None) -> MarketingCampaign:
    source = MarketingCampaign.objects.get(pk=campaign_id)
    if source.status not in {CampaignStatus.SENT, CampaignStatus.CANCELLED}:
        raise ValueError("Seule une campagne déjà envoyée ou annulée peut être republicée.")
    clone = MarketingCampaign.objects.create(
        name=source.name,
        channel=source.channel if source.channel != CampaignChannel.EMAIL else CampaignChannel.PUSH_IN_APP,
        title=source.title,
        body=source.body,
        image_url=source.image_url,
        deep_link="/",
        segment=source.segment or {},
        send_mode=CampaignSendMode.IMMEDIATE,
        status=CampaignStatus.DRAFT,
        recipients_count=segment_profiles(source.segment or {}).count(),
        created_by=admin or source.created_by,
    )
    return launch_campaign(clone.id)


def _run_campaign_safe(campaign_id) -> None:
    try:
        execute_campaign(campaign_id)
    except Exception:
        campaign = MarketingCampaign.objects.filter(pk=campaign_id).first()
        if campaign and campaign.status == CampaignStatus.SENDING:
            campaign.status = CampaignStatus.DRAFT
            campaign.save(update_fields=["status", "updated_at"])


def _dispatch_campaign_send(campaign_id) -> None:
    try:
        from core.tasks import send_marketing_campaign

        send_marketing_campaign.delay(str(campaign_id))
        return
    except Exception:
        pass
    import threading

    threading.Thread(target=_run_campaign_safe, args=(campaign_id,), daemon=True).start()


def store_campaign_image(upload) -> str:
    from pathlib import Path

    from django.conf import settings

    from core.controllers.chat_media_controller import compress_image_bytes

    raw = upload.read()
    if not raw:
        raise ValueError("Image vide.")
    if len(raw) > 8 * 1024 * 1024:
        raise ValueError("Image trop lourde (8 Mo max).")
    try:
        payload = compress_image_bytes(raw)
    except Exception as exc:
        raise ValueError("Image illisible.") from exc
    folder = Path(settings.MEDIA_ROOT) / "campaigns"
    folder.mkdir(parents=True, exist_ok=True)
    import uuid

    filename = f"{uuid.uuid4().hex[:16]}.jpg"
    (folder / filename).write_bytes(payload)
    return f"{settings.MEDIA_URL}campaigns/{filename}"


def process_due_scheduled_campaigns() -> int:
    due = MarketingCampaign.objects.filter(
        status=CampaignStatus.SCHEDULED,
        scheduled_at__lte=timezone.now(),
    )
    count = 0
    for campaign in due:
        execute_campaign(campaign.id)
        count += 1
    return count


def pending_popups(profile: Profile, *, limit: int = 3) -> list[dict]:
    settings = get_crm_settings()
    if not settings.get("popups_enabled", True):
        return []
    if not settings.get("show_on_login", True) and not settings.get("show_on_every_page", True):
        return []
    qs = (
        CampaignDelivery.objects.filter(
            profile=profile,
            dismissed_at__isnull=True,
            opened_at__isnull=True,
            campaign__status=CampaignStatus.SENT,
            campaign__channel__in=[
                CampaignChannel.IN_APP,
                CampaignChannel.PUSH_IN_APP,
            ],
        )
        .select_related("campaign")
        .order_by("-delivered_at")[:limit]
    )
    items = []
    for delivery in qs:
        items.append(popup_payload(delivery, delivery.campaign))
    return items


def mark_popup_opened(delivery_id, profile: Profile) -> bool:
    delivery = CampaignDelivery.objects.select_related("campaign").filter(pk=delivery_id, profile=profile).first()
    if not delivery or delivery.opened_at:
        return False
    now = timezone.now()
    delivery.opened_at = now
    delivery.in_app_shown = True
    delivery.save(update_fields=["opened_at", "in_app_shown"])
    MarketingCampaign.objects.filter(pk=delivery.campaign_id).update(
        opened_count=CampaignDelivery.objects.filter(campaign_id=delivery.campaign_id, opened_at__isnull=False).count()
    )
    return True


def mark_popup_clicked(delivery_id, profile: Profile | None = None) -> MarketingCampaign | None:
    qs = CampaignDelivery.objects.select_related("campaign").filter(pk=delivery_id)
    if profile:
        qs = qs.filter(profile=profile)
    delivery = qs.first()
    if not delivery:
        return None
    now = timezone.now()
    updates = ["clicked_at"]
    delivery.clicked_at = now
    if not delivery.opened_at:
        delivery.opened_at = now
        delivery.in_app_shown = True
        updates.extend(["opened_at", "in_app_shown"])
    delivery.save(update_fields=updates)
    campaign = delivery.campaign
    MarketingCampaign.objects.filter(pk=campaign.id).update(
        opened_count=CampaignDelivery.objects.filter(campaign=campaign, opened_at__isnull=False).count(),
        clicked_count=CampaignDelivery.objects.filter(campaign=campaign, clicked_at__isnull=False).count(),
    )
    campaign.refresh_from_db()
    return campaign


def mark_popup_dismissed(delivery_id, profile: Profile) -> bool:
    delivery = CampaignDelivery.objects.filter(pk=delivery_id, profile=profile).first()
    if not delivery:
        return False
    now = timezone.now()
    delivery.dismissed_at = now
    if not delivery.opened_at:
        delivery.opened_at = now
        delivery.in_app_shown = True
    delivery.save(update_fields=["dismissed_at", "opened_at", "in_app_shown"])
    MarketingCampaign.objects.filter(pk=delivery.campaign_id).update(
        opened_count=CampaignDelivery.objects.filter(campaign_id=delivery.campaign_id, opened_at__isnull=False).count()
    )
    return True


def campaign_rates(campaign: MarketingCampaign) -> dict:
    delivered = max(campaign.delivered_count, 1)
    return {
        "open_rate": round((campaign.opened_count / delivered) * 100, 1),
        "click_rate": round((campaign.clicked_count / delivered) * 100, 1),
    }
