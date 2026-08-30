"""Offres, packs in-app et codes promo — administration monétisation."""

from __future__ import annotations

import re
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.models import PromoCode, PromoCodeRedemption, Profile, Transaction
from core.models.choices import SubscriptionTier

CODE_PATTERN = re.compile(r"^[A-Z0-9_-]{3,40}$")


def _normalize_code(code: str) -> str:
    normalized = (code or "").strip().upper()
    if not CODE_PATTERN.match(normalized):
        raise ValueError("Code promo invalide (3–40 caractères, lettres/chiffres).")
    return normalized


def _parse_expires(value: str | None):
    if not value:
        return None
    try:
        dt = datetime.strptime(value, "%Y-%m-%d")
    except ValueError as exc:
        raise ValueError("Date d'expiration invalide.") from exc
    return timezone.make_aware(datetime.combine(dt.date(), datetime.max.time()))


def _parse_plan_tier(value: str | None, *, required: bool = True) -> str:
    plan_tier = (value or "").strip()
    if not plan_tier:
        if required:
            raise ValueError("Sélectionnez une formule d'abonnement.")
        return ""
    from core.controllers import site_settings_controller

    plans = site_settings_controller.get_subscription_plans()
    if plan_tier not in plans:
        raise ValueError("Formule d'abonnement invalide.")
    if plan_tier not in SubscriptionTier.values or plan_tier == SubscriptionTier.FREE:
        raise ValueError("Formule d'abonnement invalide.")
    return plan_tier


def _parse_max_uses(data: dict, *, current_usage: int = 0) -> int | None:
    unlimited = data.get("unlimited") is True or data.get("unlimited") == "on"
    if unlimited:
        return None
    raw = data.get("max_uses")
    if raw in (None, ""):
        raise ValueError("Indiquez le nombre de personnes ou cochez « Illimité ».")
    try:
        max_uses = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError("Nombre de bénéficiaires invalide.") from exc
    if max_uses < 1:
        raise ValueError("Le nombre de bénéficiaires doit être ≥ 1.")
    if max_uses < current_usage:
        raise ValueError("La limite ne peut pas être inférieure aux utilisations déjà comptées.")
    return max_uses


def promo_summary() -> dict:
    qs = PromoCode.objects.all()
    active = qs.filter(active=True)
    expired = active.filter(expires_at__lt=timezone.now())
    return {
        "total": qs.count(),
        "active": active.count(),
        "expired_active": expired.count(),
        "total_uses": sum(qs.values_list("usage_count", flat=True)),
    }


def list_promo_codes():
    return list(PromoCode.objects.order_by("-created_at"))


def promo_plan_label(promo: PromoCode) -> str:
    if not promo.plan_tier:
        return "Toutes formules"
    from core.controllers import site_settings_controller

    meta = site_settings_controller.get_subscription_plans().get(promo.plan_tier, {})
    return meta.get("label") or dict(SubscriptionTier.choices).get(promo.plan_tier, promo.plan_tier)


def promo_status_label(promo: PromoCode) -> str:
    if not promo.active:
        return "Désactivé"
    if promo.expires_at and promo.expires_at < timezone.now():
        return "Expiré"
    if promo.max_uses is not None and promo.usage_count >= promo.max_uses:
        return "Limite atteinte"
    return "Actif"


def promo_usage_label(promo: PromoCode) -> str:
    if promo.max_uses:
        suffix = "personnes" if promo.max_uses > 1 else "personne"
        return f"{promo.usage_count} / {promo.max_uses} {suffix}"
    if promo.usage_count:
        return f"{promo.usage_count} utilisation{'s' if promo.usage_count > 1 else ''} · illimité"
    return "Illimité"


def create_promo_code(data: dict) -> PromoCode:
    code = _normalize_code(data.get("code", ""))
    if PromoCode.objects.filter(code=code).exists():
        raise ValueError("Ce code promo existe déjà.")
    plan_tier = _parse_plan_tier(data.get("plan_tier"))
    try:
        discount = int(data.get("discount_percent", 0))
    except (TypeError, ValueError) as exc:
        raise ValueError("Pourcentage de remise invalide.") from exc
    if discount < 1 or discount > 100:
        raise ValueError("La remise doit être entre 1 % et 100 %.")
    max_uses = _parse_max_uses(data)
    return PromoCode.objects.create(
        code=code,
        plan_tier=plan_tier,
        discount_percent=discount,
        expires_at=_parse_expires(data.get("expires_at")),
        max_uses=max_uses,
        active=data.get("active") == "on" or data.get("active") is True,
        note=(data.get("note") or "").strip()[:200],
    )


def update_promo_code(promo_id, data: dict) -> PromoCode:
    promo = PromoCode.objects.get(pk=promo_id)
    try:
        discount = int(data.get("discount_percent", promo.discount_percent))
    except (TypeError, ValueError) as exc:
        raise ValueError("Pourcentage de remise invalide.") from exc
    if discount < 1 or discount > 100:
        raise ValueError("La remise doit être entre 1 % et 100 %.")
    if "plan_tier" in data:
        promo.plan_tier = _parse_plan_tier(data.get("plan_tier"))
    max_uses = _parse_max_uses(data, current_usage=promo.usage_count)
    promo.discount_percent = discount
    promo.expires_at = _parse_expires(data.get("expires_at"))
    promo.max_uses = max_uses
    if "active" in data:
        promo.active = data.get("active") is True or data.get("active") == "on"
    promo.note = (data.get("note") or "").strip()[:200]
    promo.save()
    return promo


def toggle_promo_code(promo_id, *, active: bool) -> PromoCode:
    promo = PromoCode.objects.get(pk=promo_id)
    promo.active = active
    promo.save(update_fields=["active", "updated_at"])
    return promo


def delete_promo_code(promo_id) -> None:
    PromoCode.objects.filter(pk=promo_id).delete()


def validate_promo_for_checkout(
    code: str,
    *,
    tier: str | None = None,
    for_boost: bool = False,
) -> PromoCode:
    normalized = _normalize_code(code)
    promo = PromoCode.objects.filter(code=normalized).first()
    if promo is None:
        raise ValueError("Code promo inconnu.")
    if not promo.active:
        raise ValueError("Ce code promo n'est plus actif.")
    if promo.expires_at and promo.expires_at < timezone.now():
        raise ValueError("Ce code promo a expiré.")
    if promo.max_uses is not None and promo.usage_count >= promo.max_uses:
        raise ValueError("Ce code promo a atteint sa limite d'utilisation.")
    if promo.plan_tier:
        if for_boost:
            raise ValueError("Ce code promo s'applique à une formule d'abonnement.")
        if not tier:
            raise ValueError("Sélectionnez une formule pour utiliser ce code.")
        if tier != promo.plan_tier:
            plan_label = promo_plan_label(promo)
            raise ValueError(f"Ce code promo s'applique uniquement à la formule « {plan_label} ».")
    return promo


def discounted_amount(amount: int, promo: PromoCode) -> tuple[int, int]:
    discount = max(0, int(round(amount * promo.discount_percent / 100)))
    return max(0, amount - discount), discount


@transaction.atomic
def record_promo_redemption(
    promo: PromoCode,
    profile: Profile | None,
    *,
    transaction_obj: Transaction | None = None,
    discount_amount: int = 0,
) -> PromoCodeRedemption:
    promo = PromoCode.objects.select_for_update().get(pk=promo.pk)
    if promo.max_uses is not None and promo.usage_count >= promo.max_uses:
        raise ValueError("Limite d'utilisation atteinte.")
    promo.usage_count += 1
    promo.save(update_fields=["usage_count", "updated_at"])
    return PromoCodeRedemption.objects.create(
        promo=promo,
        profile=profile,
        transaction=transaction_obj,
        discount_amount=max(0, discount_amount),
    )
