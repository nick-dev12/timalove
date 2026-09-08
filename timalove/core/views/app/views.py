from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_http_methods, require_POST

from core.controllers import (
    likes_controller,
    match_controller,
    message_controller,
    moderation_controller,
    profile_controller,
)
from core.data.countries import COUNTRIES_FR
from core.data.onboarding import INTERESTS, TRAITS, LIFE_VALUES, LOOKING_FOR
from core.models.choices import Gender, RelationshipIntent, Religion, ReportReason


def _profile(request):
    return request.user.profile


def decouvrir(request):
    """Ancienne URL — redirige vers l'explorer (nouveau parcours)."""
    return redirect("public:explorer")


@require_POST
def swipe(request):
    return redirect("public:explorer")


@ensure_csrf_cookie
def likes(request):
    from core.controllers import notification_controller

    profile = _profile(request)
    likes_controller.mark_inbox_seen(profile)
    notification_controller.mark_read_for_context(profile, "likes")
    ctx = likes_controller.feed_context(profile)
    ctx.update(
        {
            "title": "Likes",
            "is_preview": False,
            "new_count": ctx["pending_count"],
            "super_count": sum(1 for item in ctx["likes"] if item.get("is_super_like")),
        }
    )
    ctx.update(profile_controller.freemium_subscription_context(profile))
    return render(request, "app/likes.html", ctx)


@ensure_csrf_cookie
def likes_feed(request):
    """Fragment HTML — rafraîchissement live des likes reçus."""
    profile = _profile(request)
    likes_controller.mark_inbox_seen(profile)
    ctx = likes_controller.feed_context(profile)
    return render(request, "partials/likes_feed.html", ctx)


def historique(request):
    return redirect("public:historique")


@login_required
@require_POST
def historique_like(request, profile_id):
    from core.controllers import quota_controller

    if quota_controller.history_locked(_profile(request)):
        return HttpResponse("", status=403)
    result = likes_controller.toggle_outgoing(_profile(request), profile_id)
    if not result["visible"]:
        return HttpResponse("")
    item = likes_controller.outgoing_item(_profile(request), profile_id)
    if not item:
        return HttpResponse("")
    return render(request, "partials/history_card.html", {"item": item, "is_preview": False})


@login_required
@require_POST
def historique_superlike(request, profile_id):
    from core.controllers import quota_controller

    if quota_controller.history_locked(_profile(request)):
        return HttpResponse("", status=403)
    result = likes_controller.toggle_outgoing_super(_profile(request), profile_id)
    if not result["visible"]:
        return HttpResponse("")
    item = likes_controller.outgoing_item(_profile(request), profile_id)
    if not item:
        return HttpResponse("")
    return render(request, "partials/history_card.html", {"item": item, "is_preview": False})


def rencontres(request):
    return render(
        request,
        "app/rencontres.html",
        {"title": "Rencontres", "matches": match_controller.list_for(_profile(request))},
    )


def discussions(request):
    return redirect("public:messages")


@require_http_methods(["GET", "POST"])
def discussion_detail(request, partner_id):
    profile = _profile(request)
    if request.method == "POST":
        ok, msg, _ = message_controller.send_text(profile, partner_id, request.POST.get("content", ""))
        if not ok:
            from core.controllers import quota_controller

            if not quota_controller.limit_code_for(profile):
                messages.error(request, msg)
        else:
            message_controller.mark_read(profile, partner_id)
        return redirect("app:discussion_detail", partner_id=partner_id)
    from core.controllers import notification_controller

    thread = message_controller.thread_for(profile, partner_id)
    if not thread:
        ok, msg, _match = message_controller.ensure_conversation(profile, partner_id)
        if not ok:
            messages.error(request, msg)
            referer = request.META.get("HTTP_REFERER") or ""
            if referer and referer.startswith(request.build_absolute_uri("/")):
                return redirect(referer)
            return redirect("public:messages")
        thread = message_controller.thread_for(profile, partner_id)
        if not thread:
            raise Http404("Conversation introuvable.")
    message_controller.mark_read(profile, partner_id)
    notification_controller.mark_read_for_context(profile, "messages", partner_id=partner_id)
    inbox_back = len(message_controller.list_conversations(profile)) > 1
    ctx = {
        "title": thread["partner"]["first_name"],
        "is_preview": False,
        "me": thread["me"],
        "partner": thread["partner"],
        "thread_items": thread["thread_items"],
        "partner_id": partner_id,
        "inbox_back": inbox_back,
        "blocked_by_me": thread.get("blocked_by_me", False),
        "blocked_me": thread.get("blocked_me", False),
        "can_send": thread.get("can_send", True),
        "quota_message": thread.get("quota_message", ""),
        "messages_remaining": thread.get("messages_remaining"),
        "conversation_pending": thread.get("conversation_pending", False),
        "can_accept": thread.get("can_accept", False),
        "partner_profile_id": thread.get("partner_profile_id", partner_id),
        "report_reasons": ReportReason.choices,
    }
    if thread.get("messages_remaining") is not None:
        ctx.update(profile_controller.freemium_subscription_context(profile))
    else:
        ctx["show_subscription_modal"] = False
    return render(request, "app/message_thread.html", ctx)


@login_required
@require_POST
def discussion_media(request, partner_id):
    profile = _profile(request)
    try:
        duration = int(request.POST.get("duration") or 0)
    except (TypeError, ValueError):
        duration = 0
    ok, msg, message = message_controller.send_media(
        profile,
        partner_id,
        request.POST.get("kind", ""),
        request.FILES.get("file"),
        duration,
    )
    if not ok:
        from core.controllers import quota_controller

        payload = {"ok": False, "error": msg}
        code = quota_controller.limit_code_for(profile)
        if code:
            payload["code"] = code
            payload["message"] = msg
        return JsonResponse(payload, status=400)
    item = message_controller._serialize_message(message, profile)
    return JsonResponse({"ok": True, "item": item})


@require_http_methods(["GET", "POST"])
def profil(request):
    profile = profile_controller.get_own(_profile(request))
    if request.method == "POST":
        profile_controller.update_profile(
            profile,
            {
                "first_name": request.POST.get("first_name"),
                "last_name": request.POST.get("last_name"),
                "phone": request.POST.get("phone"),
                "city": request.POST.get("city"),
                "commune": request.POST.get("commune"),
                "country": request.POST.get("country"),
                "residence_country": request.POST.get("residence_country"),
                "religion": request.POST.get("religion") or None,
                "relationship_intent": request.POST.get("relationship_intent"),
                "life_project": request.POST.get("life_project"),
                "profession": request.POST.get("profession"),
                "bio": request.POST.get("bio"),
                "looking_for": request.POST.get("looking_for"),
            },
        )
        messages.success(request, "Profil mis à jour.")
        return redirect("app:profil")
    member = profile_controller.serialize_visit(profile)
    ctx = {
        "title": "Mon profil",
        "profile": profile,
        "member": member,
        "filters": profile_controller.filters_for(profile),
        "religions": Religion.choices,
        "genders": Gender.choices,
        "relationship_intents": RelationshipIntent.choices,
        "countries": COUNTRIES_FR,
        "interests": INTERESTS,
        "traits": TRAITS,
        "life_values_catalog": LIFE_VALUES,
        "looking_for_catalog": LOOKING_FOR,
        "max_photos": profile_controller.MAX_GALLERY_PHOTOS,
        "show_dev_tools": settings.DEBUG,
    }
    ctx.update(profile_controller.settings_context(profile))
    return render(request, "app/profil.html", ctx)


def parametres(request):
    return redirect("/profil/?tab=settings")
