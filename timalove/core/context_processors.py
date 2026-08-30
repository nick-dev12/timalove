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
        badges["likes_count"] = likes_controller.count_unread_incoming(profile)
        badges["unread_messages"] = message_controller.unread_count(profile)
        badges["unread_notifications"] = notification_controller.unread_count(profile)
    except Exception:
        pass
    return {"nav_badges": badges, **membership}


def app_features(request):
    try:
        from core.controllers import app_config_controller

        return {"app_features": app_config_controller.feature_flags()}
    except Exception:
        return {
            "app_features": {
                "video_chat_enabled": False,
                "text_messages_enabled": True,
                "voice_messages_enabled": True,
                "image_messages_enabled": True,
                "voice_call_enabled": True,
                "selfie_verification_enabled": False,
                "explorer_search_enabled": True,
                "history_search_enabled": True,
                "messages_search_enabled": True,
            }
        }


def admin_panel_nav(request):
    badges = {"signalements": 0}
    nav_sections: list[dict] = []
    staff_role = ""
    user = getattr(request, "user", None)
    path = getattr(request, "path", "") or ""
    if not user or not user.is_authenticated or not path.startswith("/espace-prive"):
        return {"admin_nav_badges": badges, "admin_nav_sections": nav_sections, "admin_staff_role": staff_role}
    profile = getattr(user, "profile", None)
    if not profile or not getattr(profile, "is_admin", False):
        return {"admin_nav_badges": badges, "admin_nav_sections": nav_sections, "admin_staff_role": staff_role}
    try:
        from core.controllers import admin_controller, rbac_controller

        stats = admin_controller.dashboard_stats()
        badges["signalements"] = stats.get("reports_pending", 0)
        nav_sections = rbac_controller.nav_links_for(profile)
        staff_role = rbac_controller.role_label(profile.role)
    except Exception:
        pass
    return {
        "admin_nav_badges": badges,
        "admin_nav_sections": nav_sections,
        "admin_staff_role": staff_role,
    }
