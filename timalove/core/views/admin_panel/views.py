from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from core.controllers import (
    admin_controller,
    auth_controller,
    coaching_controller,
    moderation_controller,
    site_settings_controller,
)
from core.models.choices import CoachingStatus, RegistrationStatus, ReportStatus


@require_http_methods(["GET", "POST"])
def connexion(request):
    if request.user.is_authenticated and getattr(getattr(request.user, "profile", None), "is_admin", False):
        return redirect("admin_panel:dashboard")
    if request.method == "POST":
        ok, msg = auth_controller.login_user(
            request, request.POST.get("email", ""), request.POST.get("password", "")
        )
        profile = getattr(request.user, "profile", None) if ok else None
        if ok and profile and profile.is_admin:
            return redirect("admin_panel:dashboard")
        if ok:
            auth_controller.logout_user(request)
            messages.error(request, "Accès réservé aux administrateurs.")
        else:
            messages.error(request, msg)
    return render(request, "admin_panel/connexion.html", {"title": "Espace Privé"})


def dashboard(request):
    return render(
        request,
        "admin_panel/dashboard.html",
        {"title": "Dashboard", "stats": admin_controller.dashboard_stats()},
    )


@require_http_methods(["GET", "POST"])
def inscriptions(request):
    if request.method == "POST":
        admin_controller.set_registration_status(
            request.POST.get("profile_id"),
            request.POST.get("status"),
            request.POST.get("rejection_reason"),
        )
        messages.success(request, "Statut mis à jour.")
        return redirect("admin_panel:inscriptions")
    status = request.GET.get("status")
    search = request.GET.get("q", "")
    return render(
        request,
        "admin_panel/inscriptions.html",
        {
            "title": "Inscriptions",
            "profiles": admin_controller.list_profiles(status=status, search=search),
            "statuses": RegistrationStatus.choices,
            "current_status": status,
            "q": search,
        },
    )


def activites(request):
    return render(
        request,
        "admin_panel/activites.html",
        {"title": "Activités", "activities": admin_controller.recent_activities()},
    )


@require_http_methods(["GET", "POST"])
def coaching(request):
    if request.method == "POST":
        coaching_controller.update_status(
            request.POST.get("id"),
            request.POST.get("status"),
            meet_link=request.POST.get("meet_link"),
            admin_notes=request.POST.get("admin_notes"),
        )
        messages.success(request, "Coaching mis à jour.")
        return redirect("admin_panel:coaching")
    return render(
        request,
        "admin_panel/coaching.html",
        {
            "title": "Coaching",
            "items": coaching_controller.list_all(),
            "statuses": CoachingStatus.choices,
        },
    )


def paiements(request):
    return render(
        request,
        "admin_panel/paiements.html",
        {"title": "Paiements", "transactions": admin_controller.list_transactions()},
    )


@require_http_methods(["GET", "POST"])
def avis(request):
    if request.method == "POST":
        if request.POST.get("delete"):
            moderation_controller.moderate_testimonial(request.POST.get("id"), delete=True)
        else:
            moderation_controller.moderate_testimonial(
                request.POST.get("id"),
                is_published=request.POST.get("publish") == "1",
            )
        return redirect("admin_panel:avis")
    from core.models import Testimonial

    return render(
        request,
        "admin_panel/avis.html",
        {"title": "Avis", "items": list(Testimonial.objects.all()[:100])},
    )


@require_http_methods(["GET", "POST"])
def signalements(request):
    if request.method == "POST":
        moderation_controller.resolve_report(
            request.POST.get("id"),
            request.user.profile,
            request.POST.get("status"),
            resolution=request.POST.get("resolution"),
            notes=request.POST.get("notes"),
        )
        return redirect("admin_panel:signalements")
    return render(
        request,
        "admin_panel/signalements.html",
        {
            "title": "Signalements",
            "items": moderation_controller.list_reports(),
            "statuses": ReportStatus.choices,
        },
    )


def monitoring(request):
    return render(
        request,
        "admin_panel/monitoring.html",
        {"title": "Monitoring", "stats": admin_controller.dashboard_stats()},
    )


@require_http_methods(["GET", "POST"])
def parametres(request):
    if request.method == "POST":
        site_settings_controller.set_value(
            "registrations_enabled", request.POST.get("registrations_enabled") == "on"
        )
        site_settings_controller.set_value(
            "maintenance_mode", request.POST.get("maintenance_mode") == "on"
        )
        site_settings_controller.set_value(
            "maintenance_message", request.POST.get("maintenance_message", "")
        )
        site_settings_controller.set_value(
            "free_messages_limit", int(request.POST.get("free_messages_limit") or 3)
        )
        site_settings_controller.set_value(
            "free_swipes_per_day", int(request.POST.get("free_swipes_per_day") or 20)
        )
        site_settings_controller.set_value(
            "free_likes_per_day", int(request.POST.get("free_likes_per_day") or 10)
        )
        site_settings_controller.set_value(
            "free_likes_visible", int(request.POST.get("free_likes_visible") or 1)
        )
        site_settings_controller.set_value(
            "whatsapp_number", request.POST.get("whatsapp_number", "")
        )
        site_settings_controller.set_value(
            "contact_email", request.POST.get("contact_email", "")
        )
        messages.success(request, "Paramètres enregistrés.")
        return redirect("admin_panel:parametres")
    return render(
        request,
        "admin_panel/parametres.html",
        {"title": "Paramètres", "settings": site_settings_controller.get_all()},
    )
