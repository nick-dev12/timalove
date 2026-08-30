from django import template

from core.controllers import subscription_controller

register = template.Library()


@register.filter
def sub_badge(value) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        return value if value in {"vip", "premium"} else ""
    if isinstance(value, dict):
        badge = str(value.get("subscription_badge") or "")
        return badge if badge in {"vip", "premium"} else ""
    return subscription_controller.badge_for(value)
