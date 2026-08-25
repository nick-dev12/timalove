"""Paiements CinetPay — checkout / webhook / boost."""

from __future__ import annotations

import logging
import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from core.controllers import cinetpay_controller, notification_controller, site_settings_controller
from core.models import Profile, Subscription, Transaction
from core.models.choices import (
    NotificationType,
    SubscriptionStatus,
    SubscriptionTier,
    TransactionStatus,
    TransactionType,
)

logger = logging.getLogger(__name__)

TIER_DURATIONS = {
    SubscriptionTier.JOURNEE_AMOUREUSE: timedelta(days=1),
    SubscriptionTier.PASS_AMOUR: timedelta(days=30),
    SubscriptionTier.ETERNITE: timedelta(days=36500),
    SubscriptionTier.VIP_1M: timedelta(days=30),
    SubscriptionTier.PASS_FEMME: timedelta(days=15),
    SubscriptionTier.PREMIUM_10D: timedelta(days=10),
    SubscriptionTier.PREMIUM_1M: timedelta(days=30),
    SubscriptionTier.PREMIUM_2M: timedelta(days=60),
    SubscriptionTier.VIP_2M: timedelta(days=60),
    SubscriptionTier.VIP_FEMME_1W: timedelta(days=7),
}


def price_for_tier(tier: str) -> int:
    prices = site_settings_controller.get("subscription_prices") or {}
    return int(prices.get(tier, 0))


def _site_url() -> str:
    return (getattr(settings, "SITE_URL", "") or "http://127.0.0.1:8000").rstrip("/")


def _notify_url() -> str:
    return f"{_site_url()}{reverse('api:cinetpay_notify')}"


def _return_url(order_id: str) -> str:
    return f"{_site_url()}{reverse('api:payments_confirm')}?order_id={order_id}"


def _simulate_url(order_id: str) -> str:
    return f"{_return_url(order_id)}&simulate=1"


def _can_simulate() -> bool:
    return bool(getattr(settings, "PAYMENT_SIMULATION", False)) and not cinetpay_controller.is_configured()


def _is_local_site() -> bool:
    site = (getattr(settings, "SITE_URL", "") or "").lower()
    return any(token in site for token in ("127.0.0.1", "localhost", "[::1]"))


def _allow_local_simulation() -> bool:
    return _is_local_site() and bool(
        getattr(settings, "PAYMENT_SIMULATION", False) or getattr(settings, "DEBUG", False)
    )


def _simulated_checkout(tx: Transaction, details: dict, *, reason: str) -> dict:
    details["mode"] = "simulate"
    details["fallback"] = reason
    tx.status = TransactionStatus.PENDING
    tx.payment_details = details
    tx.save(update_fields=["status", "payment_details", "updated_at"])
    return {
        "ok": True,
        "order_id": tx.order_id,
        "amount": tx.amount,
        "checkout_url": _simulate_url(tx.order_id),
        "transaction_id": str(tx.id),
        "simulated": True,
    }


def _order_marked_simulated(order_id: str) -> bool:
    details = Transaction.objects.filter(order_id=order_id).values_list("payment_details", flat=True).first()
    return bool(isinstance(details, dict) and details.get("mode") == "simulate")


def _start_provider_checkout(tx: Transaction, profile: Profile | None, description: str, extra: dict | None = None) -> dict:
    details = dict(tx.payment_details or {})
    details["provider"] = "cinetpay"
    if _can_simulate():
        return _simulated_checkout(tx, details, reason="no_provider_keys")
    if not cinetpay_controller.is_configured():
        return {"ok": False, "error": "Paiement indisponible pour le moment.", "message": "Paiement indisponible pour le moment."}

    result = cinetpay_controller.initialize(
        transaction_id=tx.order_id,
        amount=tx.amount,
        description=description,
        notify_url=_notify_url(),
        return_url=_return_url(tx.order_id),
        profile=profile,
        extra=extra,
    )
    if not result.get("ok"):
        if result.get("network") and _allow_local_simulation():
            logger.warning("[cinetpay] API injoignable — simulation locale pour %s.", tx.order_id)
            return _simulated_checkout(tx, details, reason="network")
        tx.status = TransactionStatus.FAILED
        details["error"] = result.get("error")
        tx.payment_details = details
        tx.save(update_fields=["status", "payment_details", "updated_at"])
        err = result.get("error") or "Impossible d’ouvrir le paiement."
        return {"ok": False, "error": err, "message": err}

    charged = int(result.get("amount") or tx.amount)
    if charged != tx.amount:
        tx.amount = charged
    details.update(
        {
            "payment_token": result.get("payment_token"),
            "payment_url": result.get("payment_url"),
            "currency": cinetpay_controller.currency(),
        }
    )
    tx.payment_details = details
    tx.save(update_fields=["amount", "payment_details", "updated_at"])
    return {
        "ok": True,
        "order_id": tx.order_id,
        "amount": tx.amount,
        "checkout_url": result["payment_url"],
        "transaction_id": str(tx.id),
        "simulated": False,
    }


def create_checkout(profile: Profile, tier: str, payment_method: str | None = None) -> dict:
    from core.controllers import subscription_controller

    if tier not in SubscriptionTier.values or tier == SubscriptionTier.FREE:
        return {"ok": False, "error": "Offre invalide.", "message": "Offre invalide."}
    if tier not in subscription_controller.plans_catalog_for(profile):
        return {"ok": False, "error": "Offre non disponible pour votre profil.", "message": "Offre non disponible."}
    amount = price_for_tier(tier)
    if amount <= 0:
        return {"ok": False, "error": "Tarif introuvable.", "message": "Tarif introuvable."}
    order_id = f"sub_{uuid.uuid4().hex[:16]}"
    tx = Transaction.objects.create(
        user=profile,
        order_id=order_id,
        amount=amount,
        payment_method=payment_method,
        type=TransactionType.SUBSCRIPTION,
        status=TransactionStatus.PENDING,
        plan_tier=tier,
        payment_details={"provider": "cinetpay", "tier": tier},
    )
    label = dict(SubscriptionTier.choices).get(tier, "Abonnement TimaLove")
    return _start_provider_checkout(tx, profile, f"TimaLove — {label}")


def create_boost_checkout(profile: Profile, days: int = 7) -> dict:
    amount = 5000
    order_id = f"boost_{uuid.uuid4().hex[:16]}"
    tx = Transaction.objects.create(
        user=profile,
        order_id=order_id,
        amount=amount,
        type=TransactionType.BOOST,
        status=TransactionStatus.PENDING,
        payment_details={"provider": "cinetpay", "days": days},
    )
    return _start_provider_checkout(tx, profile, f"TimaLove — Boost {days} jours")


def checkout_transaction(tx: Transaction, profile: Profile | None, description: str, extra: dict | None = None) -> dict:
    return _start_provider_checkout(tx, profile, description, extra=extra)


def confirm_order(order_id: str, *, simulate: bool = False) -> tuple[bool, str]:
    if not order_id:
        return False, "Transaction introuvable."
    if simulate:
        if not (_can_simulate() or _order_marked_simulated(order_id)):
            return False, "Simulation de paiement refusée."
        return fulfill_order(order_id, provider_ref="simulate")

    check = cinetpay_controller.check(order_id)
    if not check.get("accepted"):
        return False, str(check.get("error") or "Paiement non confirmé.")
    return fulfill_order(
        order_id,
        provider_ref=check.get("operator_id") or order_id,
        extra={"check": check.get("raw"), "payment_method": check.get("payment_method")},
    )


def handle_notify(payload: dict, x_token: str | None = None) -> tuple[bool, str]:
    order_id = (payload.get("cpm_trans_id") or payload.get("transaction_id") or "").strip()
    if not order_id:
        return False, "Identifiant de transaction manquant."
    secret = (getattr(settings, "CINETPAY_SECRET_KEY", "") or "").strip()
    if secret and x_token and not cinetpay_controller.hmac_matches(payload, x_token):
        logger.warning("[cinetpay] HMAC invalide pour %s — vérification API quand même.", order_id)
    return confirm_order(order_id, simulate=False)


@transaction.atomic
def fulfill_order(order_id: str, provider_ref: str | None = None, extra: dict | None = None) -> tuple[bool, str]:
    try:
        tx = Transaction.objects.select_for_update().get(order_id=order_id)
    except Transaction.DoesNotExist:
        return False, "Transaction introuvable."
    if tx.status == TransactionStatus.PAID:
        return True, "Déjà payée."

    tx.status = TransactionStatus.PAID
    tx.paid_at = timezone.now()
    if provider_ref:
        tx.naboo_transaction_id = provider_ref
    details = dict(tx.payment_details or {})
    if extra:
        details.update(extra)
    tx.payment_details = details
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
        boost_fields: list[str] = []
        if tx.plan_tier == SubscriptionTier.PASS_FEMME:
            profile.is_boosted = True
            profile.boost_end_date = ends
            boost_fields = ["is_boosted", "boost_end_date"]
        profile.save(
            update_fields=[
                "subscription_tier",
                "subscription_status",
                "subscription_end_date",
                *boost_fields,
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
