import json

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods

from core.controllers import auth_controller, email_controller, signup_controller
from core.controllers.home_controller import ORIGINE_OPTIONS
from core.data.countries import COUNTRIES_FR
from core.data.onboarding import INTERESTS, SIGNUP_COPY, TRAITS
from core.models.choices import Gender, RelationshipIntent, Religion


def _firebase_web_config() -> dict:
    return {
        "apiKey": settings.FIREBASE_WEB_API_KEY,
        "authDomain": settings.FIREBASE_AUTH_DOMAIN,
        "projectId": settings.FIREBASE_PROJECT_ID,
        "storageBucket": settings.FIREBASE_STORAGE_BUCKET,
        "messagingSenderId": settings.FIREBASE_MESSAGING_SENDER_ID,
        "appId": settings.FIREBASE_APP_ID,
        "measurementId": settings.FIREBASE_MEASUREMENT_ID,
    }


def _safe_next(request) -> str | None:
    nxt = request.GET.get("next") or request.POST.get("next") or ""
    if nxt.startswith("/") and not nxt.startswith("//"):
        return nxt
    return None


def _wants_json(request) -> bool:
    return request.headers.get("X-Requested-With") == "XMLHttpRequest"


def _after_login_path(request, profile) -> str:
    if not auth_controller.is_profile_complete(profile):
        nxt = _safe_next(request)
        if nxt:
            return f"/connexion/?signup=1&next={nxt}"
        return "/connexion/?signup=1"
    return _safe_next(request) or reverse("public:explorer")


def _after_login_redirect(request, profile):
    return redirect(_after_login_path(request, profile))


def _auth_gate_context(request, **extra):
    profile = getattr(getattr(request, "user", None), "profile", None) if getattr(request, "user", None) and request.user.is_authenticated else None
    ctx = {
        "title": extra.pop("title", "Connexion"),
        "firebase_config": json.dumps(_firebase_web_config()),
        "google_client_id": settings.GOOGLE_WEB_CLIENT_ID,
        "genders": Gender.choices,
        "origines": ORIGINE_OPTIONS,
        "countries": COUNTRIES_FR,
        "interests": INTERESTS,
        "traits": TRAITS,
        "signup_copy": SIGNUP_COPY,
        "relationship_intents": RelationshipIntent.choices,
        "religions": [
            (Religion.CHRETIENNE, "Chrétien"),
            (Religion.MUSULMANE, "Musulman"),
            (Religion.AUTRE, "Autre"),
        ],
        "oauth_incomplete": bool(profile and not auth_controller.is_profile_complete(profile)),
        "signup_prefill": json.dumps(signup_controller.profile_prefill(profile) if profile else {}, ensure_ascii=False),
    }
    ctx.update(extra)
    return ctx


@ensure_csrf_cookie
@require_http_methods(["GET", "POST"])
def connexion(request):
    profile = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    if request.user.is_authenticated and auth_controller.is_profile_complete(profile):
        if request.method == "POST" and _wants_json(request):
            return JsonResponse({"ok": True, "redirect": _after_login_path(request, profile)})
        return redirect(_safe_next(request) or "public:explorer")

    show_form = request.GET.get("form") == "1"
    login_mode = request.POST.get("login_mode") or request.GET.get("tab") or "phone"
    if login_mode not in {"phone", "email"}:
        login_mode = "phone"

    if request.method == "POST" and not request.user.is_authenticated:
        identifier = (
            request.POST.get("phone", "") if login_mode == "phone" else request.POST.get("email", "")
        )
        ok, msg = auth_controller.login_user(
            request,
            identifier,
            request.POST.get("password", ""),
            mode=login_mode,
        )
        if ok:
            dest = _after_login_path(request, getattr(request.user, "profile", None))
            if _wants_json(request):
                return JsonResponse({"ok": True, "redirect": dest})
            return redirect(dest)
        if _wants_json(request):
            return JsonResponse({"ok": False, "message": msg}, status=400)
        messages.error(request, msg)

    oauth_incomplete = bool(request.user.is_authenticated and profile and not auth_controller.is_profile_complete(profile))
    return render(
        request,
        "auth/connexion.html",
        _auth_gate_context(
            request,
            title="Connexion",
            show_form=show_form,
            login_mode=login_mode,
            open_signup=request.GET.get("signup") == "1" or oauth_incomplete,
            via=request.GET.get("via", ""),
            next_url=_safe_next(request) or "",
        ),
    )


@require_http_methods(["GET", "POST"])
def inscription(request):
    if request.user.is_authenticated:
        return _after_login_redirect(request, getattr(request.user, "profile", None))
    if request.method == "POST":
        data = {
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "email": request.POST.get("email"),
            "phone": request.POST.get("phone"),
            "password": request.POST.get("password"),
            "date_of_birth": request.POST.get("date_of_birth"),
            "gender": request.POST.get("gender"),
            "city": request.POST.get("city"),
            "country": request.POST.get("country"),
            "religion": request.POST.get("religion") or None,
            "bio": request.POST.get("bio"),
        }
        ok, msg, profile = auth_controller.register_member(data)
        if ok:
            auth_controller.login_user(request, data["email"], data["password"])
            messages.success(request, msg)
            return redirect("app:profil")
        messages.error(request, msg)
    return render(
        request,
        "auth/inscription.html",
        {
            "title": "Inscription",
            "genders": Gender.choices,
            "religions": Religion.choices,
            "origines": ORIGINE_OPTIONS,
        },
    )


@login_required
@ensure_csrf_cookie
@require_http_methods(["GET"])
def completer_profil(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return redirect("auth:connexion")
    if profile.is_profile_complete:
        return redirect(_safe_next(request) or "public:explorer")
    nxt = _safe_next(request)
    if nxt:
        return redirect(f"/connexion/?signup=1&next={nxt}")
    return redirect("/connexion/?signup=1")


@require_http_methods(["GET", "POST"])
def mot_de_passe_oublie(request):
    if request.method == "POST":
        ok, msg, token_path = auth_controller.request_password_reset(request.POST.get("email", ""))
        if token_path:
            email = request.POST.get("email", "")
            email_controller.password_reset_email(email, token_path)
            messages.info(request, f"{msg} (dev: /reinitialiser-mot-de-passe/{token_path}/)")
        else:
            messages.info(request, msg)
    return render(request, "auth/mot_de_passe_oublie.html", {"title": "Mot de passe oublié"})


def deconnexion(request):
    auth_controller.logout_user(request)
    return redirect("public:explorer")
