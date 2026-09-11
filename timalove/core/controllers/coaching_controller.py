"""Coaching."""

from __future__ import annotations

import uuid

from core.controllers import site_settings_controller
from core.models import CoachingRequest, Profile, Transaction
from core.models.choices import CoachingStatus, TransactionStatus, TransactionType

FCFA_PER_EUR = 650
MAX_COACHING_FCFA = 2_000_000


def coaching_amount_fcfa(raw_price=None) -> int:
    """Montant coaching en FCFA — accepte EUR (< 1000) ou FCFA déjà saisi par l'admin."""
    if raw_price is None:
        raw_price = site_settings_controller.get("coaching_price_eur", 40)
    try:
        value = float(raw_price)
    except (TypeError, ValueError):
        value = 40.0
    if value >= 1000:
        amount = int(value)
    else:
        amount = int(value * FCFA_PER_EUR)
    return max(1000, min(amount, MAX_COACHING_FCFA))


def create_request(data: dict, user: Profile | None = None) -> CoachingRequest:
    amount = coaching_amount_fcfa()
    raw_override = data.get("payment_amount")
    if raw_override is not None:
        try:
            amount = coaching_amount_fcfa(raw_override)
        except (TypeError, ValueError):
            pass
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
        payment_amount=amount,
    )


def checkout(coaching: CoachingRequest) -> dict:
    from core.controllers import payment_controller

    order_id = f"coach_{uuid.uuid4().hex[:16]}"
    tx = Transaction.objects.create(
        user=coaching.user,
        order_id=order_id,
        amount=coaching.payment_amount,
        type=TransactionType.COACHING,
        status=TransactionStatus.PENDING,
        coaching_request=coaching,
        payment_details={"provider": "naboopay"},
    )
    extra = {
        "first_name": coaching.first_name,
        "last_name": coaching.last_name,
        "email": coaching.email,
        "phone": coaching.phone,
    }
    return payment_controller.checkout_transaction(
        tx, coaching.user, "TimaLove — Coaching", extra=extra
    )


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
