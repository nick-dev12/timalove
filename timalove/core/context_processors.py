from __future__ import annotations


def site_branding(request):
    return {
        "brand_name": "TimaLove",
        "brand_tagline": "Mise en relation sérieuse vers le mariage",
    }


def app_nav_badges(request):
    badges = {"likes_count": 0, "unread_messages": 0, "unread_notifications": 0}
    membership = {"is_freemium": False, "has_premium": False}
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"nav_badges": badges, **membership}
    profile = getattr(user, "profile", None)
    if not profile:
        return {"nav_badges": badges, **membership}
    try:
        from core.controllers import likes_controller, message_controller, notification_controller, quota_controller

        membership["is_freemium"] = quota_controller.is_freemium(profile)
        membership["has_premium"] = not membership["is_freemium"]
        badges["likes_count"] = likes_controller.count_incoming(profile)
        badges["unread_messages"] = message_controller.unread_count(profile)
        badges["unread_notifications"] = notification_controller.unread_count(profile)
    except Exception:
        pass
    return {"nav_badges": badges, **membership}
