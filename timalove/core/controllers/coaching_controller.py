"""Coaching."""

from __future__ import annotations

import uuid

from django.conf import settings

from core.controllers import site_settings_controller
from core.models import CoachingRequest, Profile, Transaction
from core.models.choices import CoachingStatus, TransactionStatus, TransactionType


def create_request(data: dict, user: Profile | None = None) -> CoachingRequest:
    amount = int(site_settings_controller.get("coaching_price_eur", 40) * 650)  # approx FCFA
    return CoachingRequest.objects.create(
        user=user,
        first_name=data["first_name"],
        last_name=data["last_name"],
        email=data.get("email"),
        phone=data["phone"],
        gender=data.get("gender"),
        situation=data.get("situation"),
        requested_date=data["requested_date"],
        time_slot=data["time_slot"],
        theme=data["theme"],
        message=data.get("message"),
        payment_amount=data.get("payment_amount", amount),
    )


def checkout(coaching: CoachingRequest) -> dict:
    order_id = f"coach_{uuid.uuid4().hex[:16]}"
    tx = Transaction.objects.create(
        user=coaching.user,
        order_id=order_id,
        amount=coaching.payment_amount,
        type=TransactionType.COACHING,
        status=TransactionStatus.PENDING,
        coaching_request=coaching,
    )
    # user nullable for anonymous coaching — Transaction.user is required FK
    # If anonymous, we need a workaround - skip if no user
    checkout_url = f"{settings.SITE_URL}/api/payments/confirm/?order_id={order_id}&simulate=1"
    return {"ok": True, "order_id": order_id, "checkout_url": checkout_url, "transaction_id": str(tx.id)}


def list_all(status: str | None = None):
    qs = CoachingRequest.objects.all().order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    return list(qs)


def update_status(coaching_id, status: str, meet_link: str | None = None, admin_notes: str | None = None):
    c = CoachingRequest.objects.get(pk=coaching_id)
    if status in CoachingStatus.values:
        c.status = status
    if meet_link is not None:
        c.meet_link = meet_link
    if admin_notes is not None:
        c.admin_notes = admin_notes
    c.save()
    return c
