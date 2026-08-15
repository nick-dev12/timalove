"""Paiements Naboo — checkout / webhook / boost."""

from __future__ import annotations

import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from core.controllers import notification_controller, site_settings_controller
from core.models import Profile, Subscription, Transaction
from core.models.choices import (
    NotificationType,
    SubscriptionStatus,
    SubscriptionTier,
    TransactionStatus,
    TransactionType,
)

TIER_DURATIONS = {
    SubscriptionTier.PREMIUM_10D: timedelta(days=10),
    SubscriptionTier.PREMIUM_1M: timedelta(days=30),
    SubscriptionTier.PREMIUM_2M: timedelta(days=60),
    SubscriptionTier.VIP_1M: timedelta(days=30),
    SubscriptionTier.VIP_2M: timedelta(days=60),
    SubscriptionTier.VIP_FEMME_1W: timedelta(days=7),
}


def price_for_tier(tier: str) -> int:
    prices = site_settings_controller.get("subscription_prices") or {}
    return int(prices.get(tier, 0))


def create_checkout(profile: Profile, tier: str, payment_method: str | None = None) -> dict:
    if tier not in SubscriptionTier.values or tier == SubscriptionTier.FREE:
        return {"ok": False, "error": "Offre invalide."}
    amount = price_for_tier(tier)
    order_id = f"sub_{uuid.uuid4().hex[:16]}"
    tx = Transaction.objects.create(
        user=profile,
        order_id=order_id,
        amount=amount,
        payment_method=payment_method,
        type=TransactionType.SUBSCRIPTION,
        status=TransactionStatus.PENDING,
        plan_tier=tier,
        payment_details={"provider": "naboo"},
    )
    # En local sans clé Naboo : URL factice de confirmation
    checkout_url = f"{settings.SITE_URL}/api/payments/confirm/?order_id={order_id}&simulate=1"
    if settings.NABOO_API_KEY:
        checkout_url = f"{settings.NABOO_API_BASE}/checkout/{order_id}"
    return {
        "ok": True,
        "order_id": order_id,
        "amount": amount,
        "checkout_url": checkout_url,
        "transaction_id": str(tx.id),
    }


def create_boost_checkout(profile: Profile, days: int = 7) -> dict:
    amount = 5000
    order_id = f"boost_{uuid.uuid4().hex[:16]}"
    tx = Transaction.objects.create(
        user=profile,
        order_id=order_id,
        amount=amount,
        type=TransactionType.BOOST,
        status=TransactionStatus.PENDING,
        payment_details={"days": days},
    )
    checkout_url = f"{settings.SITE_URL}/api/payments/confirm/?order_id={order_id}&simulate=1"
    return {"ok": True, "order_id": order_id, "amount": amount, "checkout_url": checkout_url, "transaction_id": str(tx.id)}


@transaction.atomic
def fulfill_order(order_id: str, naboo_transaction_id: str | None = None) -> tuple[bool, str]:
    try:
        tx = Transaction.objects.select_for_update().get(order_id=order_id)
    except Transaction.DoesNotExist:
        return False, "Transaction introuvable."
    if tx.status == TransactionStatus.PAID:
        return True, "Déjà payée."

    tx.status = TransactionStatus.PAID
    tx.paid_at = timezone.now()
    if naboo_transaction_id:
        tx.naboo_transaction_id = naboo_transaction_id
    profile = tx.user

    if tx.type == TransactionType.SUBSCRIPTION and tx.plan_tier:
        duration = TIER_DURATIONS.get(tx.plan_tier, timedelta(days=30))
        starts = timezone.now()
        ends = starts + duration
        sub = Subscription.objects.create(
            user=profile,
            tier=tx.plan_tier,
            status=SubscriptionStatus.ACTIVE,
            amount=tx.amount,
            starts_at=starts,
            ends_at=ends,
            transaction=tx,
            plan_tier=tx.plan_tier,
            order_id=tx.order_id,
        )
        tx.subscription = sub
        tx.subscription_end_date = ends
        profile.subscription_tier = tx.plan_tier
        profile.subscription_status = SubscriptionStatus.ACTIVE
        profile.subscription_end_date = ends
        profile.save(
            update_fields=[
                "subscription_tier",
                "subscription_status",
                "subscription_end_date",
                "updated_at",
            ]
        )
        notification_controller.create(
            user=profile,
            type=NotificationType.SUBSCRIPTION_ACTIVATED,
            title="Abonnement activé",
            message="Votre abonnement est maintenant actif.",
        )
    elif tx.type == TransactionType.BOOST:
        days = int((tx.payment_details or {}).get("days", 7))
        profile.is_boosted = True
        profile.boost_end_date = timezone.now() + timedelta(days=days)
        profile.save(update_fields=["is_boosted", "boost_end_date", "updated_at"])
        notification_controller.create(
            user=profile,
            type=NotificationType.BOOST_ACTIVATED,
            title="Boost activé",
            message="Votre profil est mis en avant.",
        )
    elif tx.type == TransactionType.COACHING and tx.coaching_request_id:
        coaching = tx.coaching_request
        coaching.payment_status = TransactionStatus.PAID
        coaching.save(update_fields=["payment_status", "updated_at"])

    tx.save()
    return True, "Paiement confirmé."


def payment_status(profile: Profile) -> dict:
    return {
        "tier": profile.subscription_tier,
        "status": profile.subscription_status,
        "end_date": profile.subscription_end_date.isoformat() if profile.subscription_end_date else None,
        "is_boosted": profile.is_boosted,
        "boost_end_date": profile.boost_end_date.isoformat() if profile.boost_end_date else None,
        "has_active_subscription": profile.has_active_subscription,
    }


def expire_subscriptions_and_boosts() -> dict:
    now = timezone.now()
    expired_subs = Profile.objects.filter(
        subscription_status=SubscriptionStatus.ACTIVE,
        subscription_end_date__lt=now,
    )
    count_subs = 0
    for p in expired_subs:
        p.subscription_status = SubscriptionStatus.EXPIRED
        p.subscription_tier = SubscriptionTier.FREE
        p.save(update_fields=["subscription_status", "subscription_tier", "updated_at"])
        Subscription.objects.filter(user=p, status=SubscriptionStatus.ACTIVE).update(
            status=SubscriptionStatus.EXPIRED
        )
        notification_controller.create(
            user=p,
            type=NotificationType.SUBSCRIPTION_EXPIRED,
            title="Abonnement expiré",
            message="Votre abonnement a expiré.",
        )
        count_subs += 1

    expired_boosts = Profile.objects.filter(is_boosted=True, boost_end_date__lt=now)
    count_boosts = expired_boosts.update(is_boosted=False)
    return {"subscriptions": count_subs, "boosts": count_boosts}
