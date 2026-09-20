"""Accès membre selon statut d'inscription (pending / approved / rejected)."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

from core.models import Profile
from core.models.choices import RegistrationStatus

PENDING_ALLOWED_PREFIXES = (
    "/validation-en-attente",
    "/profil",
    "/completer-profil",
    "/coaching",
    "/deconnexion",
    "/connexion",
    "/inscription",
    "/politique-de-confidentialite",
    "/mentions-legales",
    "/suppression-de-compte",
    "/securite-des-enfants",
    "/cgv",
    "/conditions-d-utilisation",
    "/contact",
    "/accueil",
    "/presentation",
    "/qui-suis-je",
    "/temoignages",
    "/api/profile",
    "/api/onboarding",
    "/api/push",
    "/api/payments",
    "/api/auth",
    "/api/app-config",
    "/api/site-config",
    "/api/health",
    "/espace-prive",
    "/admin",
)

APPROVAL_REQUIRED_PREFIXES = (
    "/explorer",
    "/likes",
    "/historique",
    "/messages",
    "/discussions",
    "/rencontres",
    "/decouvrir",
    "/api/swipes",
    "/api/likes",
    "/api/messages",
    "/api/matches",
    "/api/compatibility",
)


def is_approved(profile: Profile | None) -> bool:
    if profile is None:
        return False
    if profile.is_admin:
        return True
    return profile.registration_status == RegistrationStatus.APPROVED


def is_pending(profile: Profile | None) -> bool:
    return profile is not None and profile.registration_status == RegistrationStatus.PENDING


def is_rejected(profile: Profile | None) -> bool:
    return profile is not None and profile.registration_status == RegistrationStatus.REJECTED


def pending_context(profile: Profile | None) -> dict:
    if profile is None:
        return {}
    return {
        "registration_status": profile.registration_status,
        "registration_pending": is_pending(profile),
        "registration_rejected": is_rejected(profile),
        "rejection_reason": (profile.rejection_reason or "").strip(),
    }


def redirect_if_not_approved(request: HttpRequest, profile: Profile | None) -> HttpResponse | None:
    """Redirige les membres non approuvés hors des parcours réservés."""
    if profile is None or profile.is_admin or is_approved(profile):
        return None
    path = request.path or ""
    if path.startswith("/validation-en-attente"):
        return None
    if any(path.startswith(prefix) for prefix in PENDING_ALLOWED_PREFIXES):
        return None
    if is_rejected(profile) or is_pending(profile):
        return redirect(reverse("public:validation_pending"))
    return None


def block_if_pending_explorer(profile: Profile | None) -> HttpResponse | None:
    if profile is None or profile.is_admin or is_approved(profile):
        return None
    if is_pending(profile) or is_rejected(profile):
        return redirect(reverse("public:validation_pending"))
    return None
