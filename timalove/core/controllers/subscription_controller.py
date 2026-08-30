"""Entitlements abonnements — Premium, VIP, Pass Femme."""

from __future__ import annotations

from core.models import Profile
from core.models.choices import Gender, SubscriptionTier

TIER_FREE = "free"
TIER_PREMIUM = "premium"
TIER_VIP = "vip"
TIER_PASS_FEMME = "pass_femme"

PLAN_TIER_KINDS = frozenset({TIER_PREMIUM, TIER_VIP, TIER_PASS_FEMME})

PREMIUM_TIERS = frozenset(
    {
        SubscriptionTier.PREMIUM_1M,
        SubscriptionTier.PREMIUM_10D,
        SubscriptionTier.PREMIUM_2M,
        SubscriptionTier.PASS_AMOUR,
        SubscriptionTier.JOURNEE_AMOUREUSE,
        SubscriptionTier.ETERNITE,
    }
)

VIP_TIERS = frozenset(
    {
        SubscriptionTier.VIP_1M,
        SubscriptionTier.VIP_2M,
        SubscriptionTier.VIP_FEMME_1W,
    }
)

PASS_FEMME_TIERS = frozenset({SubscriptionTier.PASS_FEMME})


def _active_tier(profile: Profile | None) -> str | None:
    if profile is None or not profile.has_active_subscription:
        return None
    return profile.subscription_tier or None


def _tier_kind_for_plan(plan_id: str | None) -> str | None:
    if not plan_id:
        return None
    from core.controllers import site_settings_controller

    meta = site_settings_controller.get_subscription_plans().get(plan_id, {})
    kind = meta.get("tier_kind")
    if kind in PLAN_TIER_KINDS:
        return kind
    if plan_id in PASS_FEMME_TIERS:
        return TIER_PASS_FEMME
    if plan_id in VIP_TIERS:
        return TIER_VIP
    if plan_id in PREMIUM_TIERS:
        return TIER_PREMIUM
    return TIER_PREMIUM


def tier_of(profile: Profile | None) -> str:
    raw = _active_tier(profile)
    if not raw:
        return TIER_FREE
    kind = _tier_kind_for_plan(raw)
    if kind == TIER_PASS_FEMME:
        return TIER_PASS_FEMME
    if kind == TIER_VIP:
        return TIER_VIP
    if kind == TIER_PREMIUM:
        return TIER_PREMIUM
    return TIER_PREMIUM


def is_premium(profile: Profile | None) -> bool:
    return tier_of(profile) != TIER_FREE


def is_vip(profile: Profile | None) -> bool:
    t = tier_of(profile)
    return t in {TIER_VIP, TIER_PASS_FEMME}


def is_pass_femme(profile: Profile | None) -> bool:
    return tier_of(profile) == TIER_PASS_FEMME


def visibility_multiplier(profile: Profile | None) -> int:
    t = tier_of(profile)
    if t in {TIER_VIP, TIER_PASS_FEMME}:
        return 10
    if t == TIER_PREMIUM:
        return 5
    return 1


def can_bypass_gender_filter(profile: Profile | None) -> bool:
    return is_vip(profile)


def conversation_requires_acceptance(recipient: Profile | None) -> bool:
    return is_vip(recipient)


def can_send_media(profile: Profile | None) -> bool:
    return is_premium(profile)


def plans_catalog_for(profile: Profile) -> list[str]:
    """IDs de plans affichables selon le genre et la configuration admin."""
    from core.controllers import site_settings_controller

    allowed: list[str] = []
    for plan_id, meta in site_settings_controller.get_subscription_plans().items():
        if not meta.get("active", True):
            continue
        audience = meta.get("audience", "all")
        if profile.gender == Gender.FEMALE and audience == "male":
            continue
        if profile.gender == Gender.MALE and audience == "female":
            continue
        allowed.append(plan_id)
    return allowed


def badge_for(profile: Profile | None) -> str:
    """vip | premium | ''"""
    if is_vip(profile):
        return "vip"
    if is_premium(profile):
        return "premium"
    return ""
