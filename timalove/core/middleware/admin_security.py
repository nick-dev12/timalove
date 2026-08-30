"""Middleware RBAC et 2FA pour l'espace privé admin."""

from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import Resolver404, resolve

from core.controllers import rbac_controller, two_factor_controller

ADMIN_PREFIX = "/espace-prive"
EXEMPT_PATHS = (
    "/espace-prive/connexion",
    "/espace-prive/2fa/configuration",
    "/espace-prive/2fa/verification",
)
EXEMPT_VIEWS = frozenset({"connexion", "admin_2fa_setup", "admin_2fa_verify"})


class AdminSecurityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path
        if not path.startswith(ADMIN_PREFIX):
            return self.get_response(request)
        if any(path.startswith(p) for p in EXEMPT_PATHS):
            return self.get_response(request)

        profile = getattr(getattr(request, "user", None), "profile", None)
        if not profile or not profile.is_staff_member:
            return self.get_response(request)

        view_name = self._resolve_view_name(request)
        if view_name and view_name not in EXEMPT_VIEWS:
            if not rbac_controller.can_access_view(profile, view_name):
                messages.error(request, "Vous n'avez pas accès à cette section.")
                return redirect("admin_panel:dashboard")

        if view_name not in EXEMPT_VIEWS:
            session = request.session
            if two_factor_controller.must_setup_2fa(profile, session):
                return redirect("admin_panel:admin_2fa_setup")
            if two_factor_controller.must_verify_2fa(profile, session):
                return redirect("admin_panel:admin_2fa_verify")

        return self.get_response(request)

    @staticmethod
    def _resolve_view_name(request: HttpRequest) -> str | None:
        try:
            match = resolve(request.path_info)
        except Resolver404:
            return None
        if match.namespace != "admin_panel":
            return None
        return match.url_name
