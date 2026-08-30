"""Guards d'authentification membre / admin."""

from __future__ import annotations

from django.contrib.auth import logout
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

MEMBER_PREFIXES = (
    "/decouvrir",
    "/likes",
    "/historique",
    "/messages",
    "/rencontres",
    "/discussions",
    "/profil",
)

ADMIN_PREFIXES = ("/espace-prive",)
COMPLETER_PATH = "/completer-profil"

# Chemins publics (pas de redirect profil incomplet / auth)
PUBLIC_PATHS = (
    "/firebase-messaging-sw.js",
)

INCOMPLETE_ALLOWED = (
    COMPLETER_PATH,
    "/connexion",
    "/inscription",
    "/deconnexion",
    "/mot-de-passe-oublie",
    "/reinitialiser-mot-de-passe",
    "/api/onboarding",
    "/api/auth",
    "/api/push",
    "/api/health",
    "/api/site-config",
    "/api/swipes",
    "/api/likes",
    "/api/messages",
    "/api/matches",
    "/api/payments",
    "/api/compatibility",
    "/espace-prive",
    "/admin",
)


class AuthGuardsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path

        if path in PUBLIC_PATHS:
            return self.get_response(request)

        if path.startswith("/explorer"):
            if not request.user.is_authenticated:
                if path.rstrip("/") == "/explorer":
                    return redirect("public:home")
                return self.get_response(request)
            profile = getattr(request.user, "profile", None)
            if profile and profile.banned_at:
                logout(request)
                return redirect("auth:connexion")
            if (
                profile
                and not profile.is_admin
                and not profile.is_profile_complete
            ):
                return redirect("/connexion/?signup=1")
            return self.get_response(request)

        if any(path.startswith(p) for p in MEMBER_PREFIXES):
            if not request.user.is_authenticated:
                return redirect(f"{reverse('auth:connexion')}?next={path}")
            profile = getattr(request.user, "profile", None)
            if profile and profile.banned_at:
                logout(request)
                return redirect("auth:connexion")
            if profile and not profile.is_admin and not profile.is_profile_complete:
                return redirect(f"/connexion/?signup=1&next={path}")

        if path.startswith(COMPLETER_PATH):
            if not request.user.is_authenticated:
                return redirect("auth:connexion")

        if request.user.is_authenticated:
            profile = getattr(request.user, "profile", None)
            if (
                profile
                and not profile.banned_at
                and not profile.is_admin
                and not profile.is_profile_complete
                and not path.startswith(("/static", "/media", "/favicon"))
                and not any(path.startswith(p) for p in INCOMPLETE_ALLOWED)
            ):
                return redirect("/connexion/?signup=1")

        if any(path.startswith(p) for p in ADMIN_PREFIXES):
            if path.startswith("/espace-prive/connexion") or path.startswith(
                "/espace-prive/mot-de-passe-oublie"
            ):
                return self.get_response(request)
            if not request.user.is_authenticated:
                return redirect("admin_panel:connexion")
            profile = getattr(request.user, "profile", None)
            if not profile or not profile.is_admin:
                return redirect("public:home")

        return self.get_response(request)
