"""Middleware mode maintenance."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect

PUBLIC_WHEN_MAINTENANCE = (
    "/maintenance",
    "/admin/",
    "/espace-prive/",
    "/static/",
    "/media/",
    "/firebase-messaging-sw.js",
    "/api/health",
)


class MaintenanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path
        if any(path.startswith(p) for p in PUBLIC_WHEN_MAINTENANCE):
            return self.get_response(request)
        try:
            from core.controllers import site_settings_controller

            if site_settings_controller.is_maintenance_mode():
                profile = getattr(getattr(request, "user", None), "profile", None)
                if not profile or not profile.is_admin:
                    return redirect("public:maintenance")
        except Exception:
            pass
        return self.get_response(request)
