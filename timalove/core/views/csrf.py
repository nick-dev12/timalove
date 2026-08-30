"""Échec CSRF : message clair plutôt qu’une page 403 technique."""

from __future__ import annotations

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.csrf import csrf_failure as django_csrf_failure


def csrf_failure(request: HttpRequest, reason: str = "") -> HttpResponse:
    path = request.path or ""
    if path.startswith("/espace-prive"):
        messages.error(
            request,
            "La session a expiré. Rechargez la page puis reconnectez-vous.",
        )
        return redirect(reverse("admin_panel:connexion"))
    if path.startswith("/connexion"):
        messages.error(
            request,
            "La session a expiré. Rechargez la page puis reconnectez-vous.",
        )
        return redirect(reverse("auth:connexion"))
    if request.headers.get("HX-Request") == "true" or request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return django_csrf_failure(request, reason=reason)
    return render(
        request,
        "errors/csrf.html",
        {
            "title": "Session expirée",
            "reason": reason,
        },
        status=403,
    )
