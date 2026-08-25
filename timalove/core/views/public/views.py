from urllib.parse import urlparse

from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_http_methods

from core.controllers import home_controller
from core.controllers import site_settings_controller
from core.data import legal as legal_data


def _member_home(request):
    if not request.user.is_authenticated:
        return None
    profile = getattr(request.user, "profile", None)
    if profile and not profile.is_profile_complete:
        return redirect("/connexion/?signup=1")
    return redirect("public:explorer")


def _same_origin_back(request, fallback: str = "/explorer/") -> str:
    referer = request.META.get("HTTP_REFERER") or ""
    if not referer:
        return fallback
    parsed = urlparse(referer)
    if parsed.netloc and parsed.netloc != request.get_host():
        return fallback
    path = parsed.path or fallback
    if path.rstrip("/") == request.path.rstrip("/"):
        return fallback
    if parsed.query:
        return f"{path}?{parsed.query}"
    return path


@require_GET
def home(request):
    landing = _member_home(request)
    if landing:
        return landing
    return render(request, "landing/welcome.html", {"title": "Bienvenue"})


@require_GET
def accueil(request):
    return render(request, "landing/welcome.html", {"title": "Bienvenue"})


@require_GET
def presentation(request):
    return redirect("public:commencer", permanent=True)


@require_GET
def commencer(request):
    landing = _member_home(request)
    if landing:
        return landing
    return render(
        request,
        "landing/commencer.html",
        {
            "title": "Bienvenue",
            "steps": home_controller.STEPS,
        },
    )


@ensure_csrf_cookie
@require_GET
def explorer(request):
    from core.controllers import explore_controller
    import secrets

    is_hx = request.headers.get("HX-Request") == "true"
    direction = (request.GET.get("direction") or "").strip()

    if not is_hx:
        request.session["explorer_seed"] = secrets.token_hex(8)
        from core.controllers.explore_controller import reset_feed_session

        reset_feed_session(request.session)
    elif "explorer_seed" not in request.session:
        request.session["explorer_seed"] = secrets.token_hex(8)

    seed = request.session["explorer_seed"]
    page_limit = 1 if direction == "back" else 20
    cards, has_more = explore_controller.public_feed(
        seed=seed,
        limit=page_limit,
        viewer=getattr(request.user, "profile", None) if request.user.is_authenticated else None,
        session=request.session,
        reset=not is_hx and direction != "back",
    )
    served = len(request.session.get("explorer_served", []))
    next_offset = served
    quota = None
    if request.user.is_authenticated:
        from core.controllers import quota_controller

        quota = quota_controller.snapshot(getattr(request.user, "profile", None))
    context = {
        "title": "Explorer",
        "cards": cards,
        "has_more": has_more,
        "next_offset": next_offset,
        "reveal_first": not is_hx,
        "swipe_quota": quota,
    }

    if is_hx:
        return render(request, "partials/explorer_slides.html", context)

    return render(request, "landing/explorer.html", context)


@require_GET
def explorer_search(request):
    from core.controllers import explore_controller

    query = request.GET.get("q", "")
    hits = explore_controller.search_profiles(
        query,
        viewer=getattr(request.user, "profile", None) if request.user.is_authenticated else None,
    )
    return render(
        request,
        "partials/explorer_search_results.html",
        {
            "hits": hits,
            "q": query.strip(),
            "q_len": len(" ".join(query.split())),
        },
    )


@require_GET
def messages(request):
    from core.controllers import message_controller

    if not request.user.is_authenticated:
        return redirect(f"{reverse('public:explorer')}?gate=1")

    profile = getattr(request.user, "profile", None)
    if not profile:
        return redirect(f"{reverse('public:explorer')}?gate=1")

    from core.controllers import notification_controller

    conversations = message_controller.list_conversations(profile)
    notification_controller.mark_read_for_context(profile, "messages")
    return render(
        request,
        "app/messages.html",
        {
            "title": "Messages",
            "conversations": conversations,
            "me": profile,
            "is_preview": False,
        },
    )


@require_GET
def messages_preview(request, partner_key):
    from core.controllers import explore_controller, message_controller

    if not request.user.is_authenticated:
        return redirect(f"{reverse('public:explorer')}?gate=1")

    member = explore_controller.get_public_profile(partner_key)
    if not member:
        for conv in message_controller.demo_conversations():
            partner = conv.get("partner") or {}
            if str(partner.get("id")) == str(partner_key):
                member = {
                    "id": partner.get("id"),
                    "first_name": partner.get("first_name") or "Membre",
                    "photo_url": partner.get("primary_photo") or "",
                    "is_online": bool(partner.get("is_online")),
                }
                break
    if not member:
        return redirect("public:messages")

    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile and message_controller.get_active_match(profile, partner_key):
            return redirect("app:discussion_detail", partner_id=partner_key)

    me = None
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile:
            me = {
                "id": str(profile.pk),
                "first_name": profile.first_name or "Moi",
                "photo_url": profile.primary_photo or "",
                "is_online": True,
                "initial": (profile.first_name or "M")[:1].upper(),
            }
    demo = message_controller.demo_thread_for(member, me)
    return render(
        request,
        "app/message_thread.html",
        {
            "title": demo["partner"]["first_name"],
            "me": demo["me"],
            "partner": demo["partner"],
            "thread_items": demo["thread_items"],
            "is_preview": True,
            "inbox_back": True,
            "partner_id": partner_key,
        },
    )


@require_GET
def historique(request):
    from core.controllers import likes_controller, quota_controller

    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile:
            if quota_controller.history_locked(profile):
                return render(
                    request,
                    "app/historique.html",
                    {
                        "title": "Historique",
                        "items": [],
                        "stories": [],
                        "has_more": False,
                        "next_offset": 0,
                        "is_preview": False,
                        "history_locked": True,
                    },
                )
            page = likes_controller.outgoing(profile)
            items = page["items"]
            return render(
                request,
                "app/historique.html",
                {
                    "title": "Historique",
                    "items": items,
                    "stories": items[:12],
                    "has_more": page["has_more"],
                    "next_offset": page["next_offset"],
                    "is_preview": False,
                    "history_locked": False,
                    "history_locked_extra": page.get("history_locked_extra", 0),
                    "history_limit": page.get("history_limit"),
                },
            )
    return render(
        request,
        "app/historique.html",
        {
            "title": "Historique",
            "items": [],
            "stories": [],
            "has_more": False,
            "next_offset": 0,
            "is_preview": True,
            "history_locked": False,
        },
    )


@require_GET
def historique_plus(request):
    from core.controllers import likes_controller, quota_controller

    if not request.user.is_authenticated:
        return HttpResponse("")
    profile = getattr(request.user, "profile", None)
    if not profile or quota_controller.history_limit_for(profile) is not None:
        if profile and quota_controller.is_male_freemium(profile):
            return HttpResponse("")
    try:
        offset = max(0, int(request.GET.get("offset") or 0))
    except (TypeError, ValueError):
        offset = 0
    page = likes_controller.outgoing(profile, offset=offset)
    return render(
        request,
        "partials/history_page.html",
        {
            "items": page["items"],
            "has_more": page["has_more"],
            "next_offset": page["next_offset"],
            "is_preview": False,
        },
    )


@require_GET
def historique_search(request):
    from core.controllers import likes_controller, quota_controller

    query = request.GET.get("q", "")
    hits = []
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile and not quota_controller.history_locked(profile):
            hits = likes_controller.search_outgoing(profile, query)
    return render(
        request,
        "partials/explorer_search_results.html",
        {
            "hits": hits,
            "q": query.strip(),
            "q_len": len(" ".join(query.split())),
        },
    )


@require_GET
def explorer_stories(request):
    from core.controllers import stories_controller

    return render(
        request,
        "landing/explorer_stories.html",
        stories_controller.page_context(),
    )


@require_GET
def explorer_profil(request, profile_id):
    from core.controllers import explore_controller, likes_controller

    viewer = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    member = explore_controller.get_public_profile_or_404(profile_id, viewer=viewer)
    liked = False
    super_liked = False
    if viewer:
        liked = likes_controller.has_liked(viewer, member["id"])
        super_liked = likes_controller.has_super_liked(viewer, member["id"])
    is_fragment = (
        request.headers.get("HX-Request") == "true"
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
    )
    if not is_fragment:
        return redirect(f"/explorer/?profil={profile_id}")
    return render(
        request,
        "partials/visit_profil.html",
        {
            "title": member["first_name"],
            "member": member,
            "liked": liked,
            "super_liked": super_liked,
        },
    )


@require_GET
def qui_suis_je(request):
    return render(request, "landing/qui_suis_je.html", {"title": "Qui suis-je ?"})


@require_http_methods(["GET", "POST"])
def coaching(request):
    from core.controllers import coaching_controller, home_controller
    from django.contrib import messages

    if request.method == "POST":
        profile = getattr(getattr(request, "user", None), "profile", None) if request.user.is_authenticated else None
        data = {
            "first_name": request.POST.get("first_name"),
            "last_name": request.POST.get("last_name"),
            "email": request.POST.get("email"),
            "phone": request.POST.get("phone"),
            "requested_date": request.POST.get("requested_date"),
            "time_slot": request.POST.get("time_slot"),
            "theme": request.POST.get("theme"),
            "message": request.POST.get("message"),
        }
        coaching = coaching_controller.create_request(data, user=profile)
        if profile:
            result = coaching_controller.checkout(coaching)
            if result.get("checkout_url"):
                return redirect(result["checkout_url"])
        messages.success(request, "Votre demande de coaching a été enregistrée. Nous vous recontactons bientôt.")
        return redirect("public:coaching")

    return render(request, "landing/coaching.html", home_controller.coaching_page_context())


@require_GET
def temoignages(request):
    return render(request, "landing/temoignages.html", home_controller.testimonials_page_context())


@require_http_methods(["GET", "POST"])
def contact(request):
    from core.controllers import contact_controller
    from django.contrib import messages

    site_config = site_settings_controller.public_config()
    if request.method == "POST":
        ok, message = contact_controller.submit(
            {
                "name": request.POST.get("name"),
                "email": request.POST.get("email"),
                "message": request.POST.get("message"),
            }
        )
        if ok:
            messages.success(request, message)
            return redirect("public:contact")
        messages.error(request, message)

    whatsapp = site_config.get("whatsappNumber") or "+33 6 13 03 14 55"
    digits = "".join(ch for ch in whatsapp if ch.isdigit())
    return render(
        request,
        "landing/contact.html",
        {
            "title": "Contact",
            "site_config": site_config,
            "whatsapp_link": f"https://wa.me/{digits}",
        },
    )


@require_GET
def cgv(request):
    return render(request, "legal/page.html", {"title": "CGV", "sections": legal_data.CGV_SECTIONS})


@require_GET
def mentions(request):
    return render(
        request,
        "legal/page.html",
        {"title": "Mentions légales", "sections": legal_data.MENTIONS_SECTIONS},
    )


@require_GET
def confidentialite(request):
    return render(
        request,
        "legal/page.html",
        {"title": "Politique de confidentialité", "sections": legal_data.PRIVACY_SECTIONS},
    )


@require_GET
def maintenance(request):
    return render(
        request,
        "landing/maintenance.html",
        {
            "message": site_settings_controller.get(
                "maintenance_message", "Maintenance en cours. Nous revenons très bientôt."
            )
        },
    )
