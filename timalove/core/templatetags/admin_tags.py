from django import template

from core.controllers import admin_controller

register = template.Library()


@register.filter
def mask_email(value: str) -> str:
    return admin_controller.mask_email(value or "")


@register.filter
def member_pseudo(profile) -> str:
    return admin_controller.member_pseudonym(profile)


@register.filter
def member_status_label(profile) -> str:
    return admin_controller.account_status_label(profile)


@register.filter
def member_sub_label(profile) -> str:
    return admin_controller.subscription_kind_label(profile)


@register.filter
def profile_ref(value) -> str:
    if not value:
        return "—"
    profile = value
    if hasattr(value, "profile"):
        profile = getattr(value, "profile", None) or value
    ref = getattr(profile, "id", profile)
    return f"#{str(ref).replace('-', '')[:8]}"


@register.filter
def member_last_access(profile) -> str:
    return admin_controller.last_access_label(profile)


@register.filter
def report_priority_label(report) -> str:
    from core.controllers import moderation_controller

    return moderation_controller.report_priority_label(report)


@register.filter
def report_priority_badge(report) -> str:
    from core.controllers import moderation_controller

    label = moderation_controller.report_priority_label(report)
    if label == "Urgent":
        return "danger"
    if label == "Élevée":
        return "warn"
    if label == "Traité":
        return "muted"
    return "ok"


@register.filter
def tx_provider(tx) -> str:
    from core.controllers import finance_controller

    return finance_controller.transaction_provider_label(tx)


@register.filter
def tx_product(tx) -> str:
    from core.controllers import finance_controller

    return finance_controller.transaction_product_label(tx)


@register.filter
def tx_status_admin(tx) -> str:
    from core.controllers import finance_controller

    return finance_controller.transaction_status_admin_label(tx.status)


@register.filter
def tx_status_badge(status: str) -> str:
    if status == "paid":
        return "ok"
    if status == "failed":
        return "danger"
    if status == "pending":
        return "warn"
    if status == "dispute":
        return "danger"
    if status == "refunded":
        return "muted"
    return "muted"


@register.filter
def promo_status_label(promo) -> str:
    from core.controllers import monetization_controller

    return monetization_controller.promo_status_label(promo)


@register.filter
def promo_status_badge(promo) -> str:
    from core.controllers import monetization_controller

    label = monetization_controller.promo_status_label(promo)
    if label == "Actif":
        return "ok"
    if label == "Expiré":
        return "warn"
    if label == "Limite atteinte":
        return "danger"
    return "muted"


@register.filter
def promo_usage_label(promo) -> str:
    from core.controllers import monetization_controller

    return monetization_controller.promo_usage_label(promo)


@register.filter
def promo_plan_label(promo) -> str:
    from core.controllers import monetization_controller

    return monetization_controller.promo_plan_label(promo)


@register.filter
def fcfa(value) -> str:
    try:
        number = int(value)
    except (TypeError, ValueError):
        return "0 FCFA"
    formatted = f"{number:,}".replace(",", "\u202f")
    return f"{formatted} FCFA"


@register.filter
def join_lines(value) -> str:
    if isinstance(value, list):
        return "\n".join(str(item) for item in value if str(item).strip())
    return str(value or "")


@register.filter
def staff_role_label(role: str) -> str:
    from core.controllers import rbac_controller

    return rbac_controller.role_label(role or "")
