import json

from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from core.controllers import (
    auth_controller,
    coaching_controller,
    discover_controller,
    likes_controller,
    match_controller,
    message_controller,
    moderation_controller,
    notification_controller,
    onboarding_controller,
    payment_controller,
    profile_controller,
    push_controller,
    signup_controller,
    site_settings_controller,
    swipe_controller,
    matching_controller,
)


def _json(request):
    try:
        return json.loads(request.body.decode() or "{}")
    except Exception:
        return {}


@require_GET
def health(request):
    return JsonResponse({"status": "ok"})


@require_GET
def site_config(request):
    return JsonResponse(site_settings_controller.public_config())


@login_required
@require_GET
def discover_feed(request):
    cards = discover_controller.feed_for(request.user.profile)
    return JsonResponse(
        {
            "profiles": [
                {
                    "id": str(p.id),
                    "firstName": p.first_name,
                    "age": p.age,
                    "city": p.city,
                    "bio": p.bio,
                    "photoUrl": p.primary_photo,
                    "isVerified": p.is_verified,
                }
                for p in cards
            ],
            "blur": discover_controller.should_blur_photos(request.user.profile),
        }
    )


@login_required
@require_POST
def swipes(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "error": "Profil introuvable."}, status=400)
    data = _json(request) or request.POST
    result = swipe_controller.record_swipe(
        profile, data.get("swiped_id") or data.get("swipedId"), data.get("action", "pass")
    )
    status = 200 if result.get("ok") else 400
    return JsonResponse(result, status=status)


@login_required
@require_GET
def likes_incoming(request):
    items = likes_controller.incoming(request.user.profile)
    from core.controllers import quota_controller

    if quota_controller.is_freemium(request.user.profile):
        items = items[: quota_controller.likes_visible_limit()]
    return JsonResponse(
        {
            "likes": [
                {
                    "id": str(i["profile"].id),
                    "firstName": i["profile"].first_name,
                    "photoUrl": i["profile"].primary_photo,
                    "isSuperLike": i["is_super_like"],
                }
                for i in items
            ]
        }
    )


@login_required
@require_GET
def likes_count(request):
    return JsonResponse({"count": likes_controller.count_unread_incoming(request.user.profile)})


@login_required
@require_GET
def matches(request):
    items = match_controller.list_for(request.user.profile)
    return JsonResponse(
        {
            "matches": [
                {
                    "matchId": str(i["match"].id),
                    "partnerId": str(i["partner"].id),
                    "firstName": i["partner"].first_name,
                    "photoUrl": i["partner"].primary_photo,
                }
                for i in items
            ]
        }
    )


@login_required
@require_POST
def unmatch(request, partner_id):
    ok, msg = match_controller.unmatch(request.user.profile, partner_id)
    return JsonResponse({"ok": ok, "message": msg})


@login_required
@require_http_methods(["GET", "POST"])
def messages(request):
    if request.method == "GET":
        partner_id = request.GET.get("partner_id")
        msgs = message_controller.messages_for(request.user.profile, partner_id)
        return JsonResponse(
            {
                "messages": [
                    {
                        "id": str(m.id),
                        "content": m.content,
                        "type": m.message_type,
                        "mine": m.sender_id == request.user.profile.id,
                        "createdAt": m.created_at.isoformat(),
                    }
                    for m in msgs
                ]
            }
        )
    data = _json(request) or request.POST
    ok, msg, message = message_controller.send_text(
        request.user.profile, data.get("partner_id"), data.get("content", "")
    )
    payload = {"ok": ok, "message": msg}
    if not ok:
        from core.controllers import quota_controller

        code = quota_controller.limit_code_for(request.user.profile)
        if code:
            payload["code"] = code
    if message:
        payload["id"] = str(message.id)
        payload["item"] = message_controller._serialize_message_ws(message)
    return JsonResponse(payload, status=200 if ok else 400)


@login_required
@require_http_methods(["DELETE"])
def message_delete(request, message_id):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    ok, msg = message_controller.delete_message(profile, message_id)
    return JsonResponse({"ok": ok, "message": msg}, status=200 if ok else 400)


@login_required
@require_POST
def messages_open(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    data = _json(request) or request.POST
    partner_id = data.get("partner_id")
    ok, msg, match = message_controller.ensure_conversation(profile, partner_id)
    if not ok:
        return JsonResponse({"ok": False, "message": msg}, status=400)
    return JsonResponse(
        {
            "ok": True,
            "partner_id": str(partner_id),
            "match_id": str(match.id) if match else None,
            "thread_url": f"/discussions/{partner_id}/",
        }
    )


@login_required
@require_GET
def unread_messages(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"count": 0})
    return JsonResponse({"count": message_controller.unread_count(profile)})


@login_required
@require_GET
def unread_notifications_count(request):
    from core.controllers import notification_controller

    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"count": 0})
    return JsonResponse({"count": notification_controller.unread_count(profile)})


@login_required
@require_GET
def messages_inbox(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"items": [], "total_unread": 0})
    items = message_controller.inbox_feed(profile)
    return JsonResponse(
        {
            "items": items,
            "total_unread": message_controller.unread_count(profile),
        }
    )


@login_required
@require_GET
def message_read_receipts(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"read_ids": []})
    partner_id = request.GET.get("partner_id")
    return JsonResponse({"read_ids": message_controller.read_receipts(profile, partner_id)})


@login_required
@require_http_methods(["GET", "POST"])
def message_mark_read(request):
    """Marque les messages du partenaire comme lus (accusés de lecture temps réel)."""
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    partner_id = request.GET.get("partner_id")
    if not partner_id and request.method == "POST":
        try:
            payload = json.loads(request.body or b"{}")
        except json.JSONDecodeError:
            payload = {}
        partner_id = payload.get("partner_id") or request.POST.get("partner_id")
    if not partner_id:
        return JsonResponse({"ok": False, "message": "Partenaire manquant."}, status=400)
    count = message_controller.mark_read(profile, partner_id)
    return JsonResponse({"ok": True, "marked": count})


@require_GET
def compatibility_score_api(request, profile_id):
    viewer = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    ok, msg, score = matching_controller.compatibility_for_profile_id(viewer, profile_id)
    if not ok:
        return JsonResponse({"ok": False, "message": msg}, status=404)
    return JsonResponse(
        {
            "ok": True,
            "profile_id": str(profile_id),
            "compatibility": score,
        }
    )


@login_required
@require_http_methods(["GET", "PATCH"])
def notifications(request):
    if request.method == "PATCH":
        notification_controller.mark_read(request.user.profile)
        return JsonResponse({"ok": True})
    items = notification_controller.list_for(request.user.profile)
    return JsonResponse(
        {
            "notifications": [
                {
                    "id": str(n.id),
                    "type": n.type,
                    "title": n.title,
                    "message": n.message,
                    "isRead": n.is_read,
                }
                for n in items
            ]
        }
    )


@login_required
@require_POST
def payments_checkout(request):
    data = _json(request) or request.POST
    if (data.get("kind") or "") == "boost":
        result = payment_controller.create_boost_checkout(request.user.profile)
    else:
        result = payment_controller.create_checkout(request.user.profile, data.get("tier"))
    if not result.get("ok"):
        return JsonResponse({"ok": False, "message": result.get("error") or result.get("message") or "Erreur"}, status=400)
    return JsonResponse(result)


@require_GET
def payments_confirm(request):
    order_id = request.GET.get("order_id") or request.GET.get("transaction_id") or ""
    simulate = request.GET.get("simulate") == "1"
    ok, msg = payment_controller.confirm_order(order_id, simulate=simulate)
    if request.user.is_authenticated:
        messages_mod = __import__("django.contrib.messages", fromlist=["messages"]).messages
        if ok:
            messages_mod.success(request, msg)
        else:
            messages_mod.error(request, msg)
        return redirect(f"{reverse('app:profil')}?tab=settings")
    return JsonResponse({"ok": ok, "message": msg})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def cinetpay_notify(request):
    if request.method == "GET":
        return HttpResponse("OK", status=200)
    payload = {key: request.POST.get(key, "") for key in request.POST}
    if not payload.get("cpm_trans_id"):
        payload.update(_json(request) or {})
    x_token = request.headers.get("x-token") or request.META.get("HTTP_X_TOKEN", "")
    ok, msg = payment_controller.handle_notify(payload, x_token)
    return HttpResponse("OK" if ok else msg, status=200)


@login_required
@require_POST
def reports(request):
    data = _json(request) or request.POST
    try:
        r = moderation_controller.create_report(request.user.profile, data)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)
    return JsonResponse({"ok": True, "id": str(r.id), "message": "Signalement envoyé. Merci pour votre vigilance."})


@login_required
@require_POST
def conversation_hide(request):
    data = _json(request) or request.POST
    partner_id = data.get("partner_id")
    if not partner_id:
        return JsonResponse({"ok": False, "message": "Conversation introuvable."}, status=400)
    ok, msg = message_controller.hide_conversation(request.user.profile, partner_id)
    return JsonResponse({"ok": ok, "message": msg}, status=200 if ok else 400)


@login_required
@require_http_methods(["POST", "DELETE"])
def blocked_users(request):
    data = _json(request) or request.POST
    blocked_id = data.get("blocked_id") or request.GET.get("blocked_id")
    if request.method == "DELETE":
        moderation_controller.unblock_user(request.user.profile, blocked_id)
        return JsonResponse({"ok": True})
    ok, msg = moderation_controller.block_user(request.user.profile, blocked_id)
    return JsonResponse({"ok": ok, "message": msg})


@require_POST
def coaching_checkout(request):
    data = _json(request) or request.POST
    profile = getattr(getattr(request, "user", None), "profile", None) if request.user.is_authenticated else None
    coaching = coaching_controller.create_request(data, user=profile)
    if profile:
        return JsonResponse(coaching_controller.checkout(coaching))
    return JsonResponse({"ok": True, "coaching_id": str(coaching.id), "message": "Demande enregistrée."})


@require_GET
def push_config(request):
    return JsonResponse(push_controller.public_config())


@login_required
@require_GET
def push_status(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    return JsonResponse({"ok": True, **push_controller.status_for(profile)})


@login_required
@require_POST
def push_test(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    try:
        result = notification_controller.send_test(profile)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)
    if result.get("sent", 0) < 1:
        errors = result.get("errors") or []
        detail = errors[0] if errors else "Push non envoyée. Vérifiez Firebase et l’appareil enregistré."
        return JsonResponse(
            {
                "ok": False,
                "message": detail,
                **result,
            },
            status=502,
        )
    return JsonResponse({"ok": True, "message": "Notification test envoyée.", "url": result.get("url"), **result})


@login_required
@require_POST
def push_register(request):
    data = _json(request) or request.POST
    token = data.get("token", "")
    platform = data.get("platform", "web")
    try:
        device = push_controller.register_device(
            request.user.profile,
            token=token,
            platform=platform,
            user_agent=request.META.get("HTTP_USER_AGENT", ""),
        )
        profile_controller.activate_push_preferences(request.user.profile)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)
    return JsonResponse({"ok": True, "id": str(device.id)})


@login_required
@require_http_methods(["POST", "DELETE"])
def push_unregister(request):
    data = _json(request) or request.POST
    token = data.get("token", "")
    if not token:
        return JsonResponse({"ok": False, "message": "Token requis."}, status=400)
    removed = push_controller.unregister_device(request.user.profile, token=token)
    return JsonResponse({"ok": removed})


@require_POST
def auth_google(request):
    return _auth_oauth(request, "google")


@require_POST
def auth_apple(request):
    return _auth_oauth(request, "apple")


def _signup_next(next_url: str) -> str:
    if next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/explorer/"


def _auth_oauth(request, provider: str):
    data = _json(request) or request.POST
    next_url = data.get("next") or request.GET.get("next") or ""

    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if auth_controller.is_profile_complete(profile):
            return JsonResponse({"ok": True, "redirect": _signup_next(next_url)})
        redirect_to = "/connexion/?signup=1"
        if next_url.startswith("/") and not next_url.startswith("//"):
            redirect_to = f"{redirect_to}&next={next_url}"
        return JsonResponse(
            {
                "ok": True,
                "needs_completion": True,
                "redirect": redirect_to,
                "profile": signup_controller.profile_prefill(profile),
            }
        )

    id_token = data.get("idToken") or data.get("id_token") or ""
    label = "Google" if provider == "google" else "Apple"
    if not id_token:
        return JsonResponse({"ok": False, "message": f"Jeton {label} manquant."}, status=400)

    hints = {}
    if provider == "apple":
        for key in ("given_name", "family_name", "display_name", "email"):
            val = (data.get(key) or "").strip()
            if val:
                hints[key] = val
        ok, msg, needs_completion = auth_controller.login_or_register_apple(
            request, id_token, hints=hints or None
        )
    else:
        ok, msg, needs_completion = auth_controller.login_or_register_google(request, id_token)
    if not ok:
        return JsonResponse({"ok": False, "message": msg}, status=400)

    if needs_completion:
        redirect_to = "/connexion/?signup=1"
        if next_url.startswith("/") and not next_url.startswith("//"):
            redirect_to = f"{redirect_to}&next={next_url}"
        profile = getattr(request.user, "profile", None)
        return JsonResponse(
            {
                "ok": True,
                "message": msg,
                "needs_completion": True,
                "redirect": redirect_to,
                "profile": signup_controller.profile_prefill(profile),
            }
        )
    return JsonResponse({"ok": True, "message": msg, "redirect": _signup_next(next_url)})


@require_POST
def signup_check(request):
    data = _json(request) or request.POST
    profile = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    errors = signup_controller.check_identifier(data, exclude_profile=profile)
    if errors:
        return JsonResponse({"ok": False, "errors": errors}, status=400)
    return JsonResponse({"ok": True})


@require_POST
def signup_complete(request):
    data = _json(request) or request.POST
    profile = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    next_url = data.get("next") or request.GET.get("next") or ""

    if request.user.is_authenticated and profile:
        ok, msg, errors, step = signup_controller.complete_oauth_profile(profile, data)
        created_profile = profile
    else:
        ok, msg, created_profile, errors, step = signup_controller.register_from_draft(data)
        if ok and created_profile is not None:
            login(request, created_profile.user, backend="django.contrib.auth.backends.ModelBackend")

    if not ok:
        return JsonResponse(
            {"ok": False, "message": msg, "errors": errors, "step": step},
            status=400,
        )

    token = (data.get("fcm_token") or "").strip()
    notifications_push = bool(data.get("notifications_push"))
    if created_profile is not None and (token or notifications_push):
        if token:
            try:
                push_controller.register_device(
                    created_profile,
                    token=token,
                    platform="web",
                    user_agent=request.META.get("HTTP_USER_AGENT", ""),
                )
            except ValueError:
                pass
        if notifications_push or token:
            profile_controller.activate_push_preferences(created_profile)

    return JsonResponse({"ok": True, "message": msg, "redirect": _signup_next(next_url)})


@require_POST
def signup_location(request):
    data = _json(request) or request.POST
    profile = getattr(request.user, "profile", None) if request.user.is_authenticated else None
    result = signup_controller.save_signup_location(data, profile=profile)
    status = 200 if result.get("ok") else 400
    return JsonResponse(result, status=status)


@login_required
@require_POST
def onboarding_step(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    data = _json(request) or request.POST
    if (data.get("action") or "") == "location":
        ok, msg = onboarding_controller.save_location(profile, data)
        if not ok:
            return JsonResponse({"ok": False, "message": msg}, status=400)
        return JsonResponse(
            {
                "ok": True,
                "message": msg,
                "latitude": str(profile.latitude) if profile.latitude is not None else None,
                "longitude": str(profile.longitude) if profile.longitude is not None else None,
            }
        )
    try:
        step = int(data.get("step") or 1)
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "message": "Étape inconnue."}, status=400)
    savers = {
        1: onboarding_controller.save_step_1,
        2: onboarding_controller.save_step_2,
        3: onboarding_controller.save_step_3,
        4: onboarding_controller.save_step_4,
    }
    saver = savers.get(step)
    if not saver:
        return JsonResponse({"ok": False, "message": "Étape inconnue."}, status=400)
    ok, msg = saver(profile, data)
    if not ok:
        return JsonResponse({"ok": False, "message": msg}, status=400)
    nxt = "/explorer/"
    if step < 4:
        nxt = f"/completer-profil/?etape={step + 1}"
    return JsonResponse(
        {
            "ok": True,
            "message": msg,
            "step": onboarding_controller.current_step(profile),
            "completed": profile.onboarding_completed,
            "redirect": nxt,
        }
    )


@login_required
@require_POST
def onboarding_photo(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    kind = request.POST.get("kind") or "profile"
    data_url = request.POST.get("data_url") or ""
    upload = request.FILES.get("file")
    try:
        url = onboarding_controller.save_image(profile, kind=kind, upload=upload, data_url=data_url)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)
    return JsonResponse({"ok": True, "url": url, "kind": kind})


def _truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "on", "yes"}


@login_required
@require_POST
def profile_update(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    data = _json(request) or {}
    payload: dict = {}
    str_fields = (
        "first_name",
        "last_name",
        "phone",
        "city",
        "commune",
        "country",
        "residence_country",
        "profession",
        "bio",
        "looking_for",
        "life_project",
        "relationship_intent",
        "gender",
    )
    for key in str_fields:
        if key in data:
            value = data.get(key)
            payload[key] = (value or "").strip() if isinstance(value, str) else value
    if "religion" in data:
        payload["religion"] = data.get("religion") or None
    if "age" in data:
        payload["age"] = data.get("age")
    if "hide_age" in data:
        payload["hide_age"] = _truthy(data.get("hide_age"))
    if "is_hidden" in data:
        payload["is_hidden"] = _truthy(data.get("is_hidden"))
    if "last_seen_visibility" in data:
        payload["last_seen_visibility"] = data.get("last_seen_visibility")
    if "notification_preferences" in data and isinstance(data.get("notification_preferences"), dict):
        payload["notification_preferences"] = data["notification_preferences"]
    if "interests" in data:
        interests = data.get("interests") if isinstance(data.get("interests"), list) else []
        payload["interests"] = [str(x) for x in interests]
    if "personality_traits" in data:
        traits = data.get("personality_traits") if isinstance(data.get("personality_traits"), list) else []
        payload["personality_traits"] = [str(x) for x in traits]
    if "life_values" in data:
        values = data.get("life_values") if isinstance(data.get("life_values"), list) else []
        payload["life_values"] = [str(x) for x in values]
    if not payload:
        return JsonResponse({"ok": False, "message": "Rien à enregistrer."}, status=400)
    profile_controller.update_profile(profile, payload)
    fresh = profile_controller.get_own(profile)
    return JsonResponse({"ok": True, "message": "Enregistré.", "member": profile_controller.serialize_visit(fresh)})


@login_required
@require_POST
def profile_email(request):
    from core.controllers import auth_controller

    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    data = _json(request) or {}
    ok, msg = auth_controller.change_email(
        profile,
        str(data.get("email") or ""),
        str(data.get("current_password") or ""),
    )
    if not ok:
        return JsonResponse({"ok": False, "message": msg}, status=400)
    email = profile_controller.account_context(profile)["account_email"]
    return JsonResponse({"ok": True, "message": msg, "email": email})


@login_required
@require_POST
def profile_password(request):
    from core.controllers import auth_controller

    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    data = _json(request) or {}
    ok, msg = auth_controller.change_password(
        profile,
        str(data.get("current_password") or ""),
        str(data.get("new_password") or ""),
        str(data.get("confirm_password") or ""),
    )
    if not ok:
        return JsonResponse({"ok": False, "message": msg}, status=400)
    return JsonResponse({"ok": True, "message": msg})


@login_required
@require_POST
def profile_photo(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    kind = request.POST.get("kind") or "gallery"
    data_url = request.POST.get("data_url") or ""
    upload = request.FILES.get("file")
    try:
        if kind == "avatar":
            url = profile_controller.set_avatar(profile, upload=upload, data_url=data_url)
            return JsonResponse({"ok": True, "url": url, "kind": "avatar", "id": "primary", "is_primary": True})
        photo = profile_controller.add_gallery_photo(profile, upload=upload, data_url=data_url)
        return JsonResponse({"ok": True, **photo})
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)


@login_required
@require_POST
def profile_photo_delete(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    data = _json(request) or request.POST
    photo_id = str(data.get("id") or data.get("photo_id") or "")
    if not photo_id:
        return JsonResponse({"ok": False, "message": "Photo manquante."}, status=400)
    try:
        profile_controller.delete_gallery_photo(profile, photo_id)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)
    fresh = profile_controller.get_own(profile)
    return JsonResponse({"ok": True, "photos": profile_controller.gallery_urls(fresh)})


@login_required
@require_POST
def profile_photo_primary(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    data = _json(request) or request.POST
    photo_id = str(data.get("id") or "")
    try:
        url = profile_controller.set_primary_photo(profile, photo_id)
    except ValueError as exc:
        return JsonResponse({"ok": False, "message": str(exc)}, status=400)
    fresh = profile_controller.get_own(profile)
    return JsonResponse({"ok": True, "url": url, "photos": profile_controller.gallery_urls(fresh)})


@login_required
@require_POST
def profile_filters(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    data = _json(request) or {}
    filters = profile_controller.update_filters(
        profile,
        {
            "age_min": data.get("age_min"),
            "age_max": data.get("age_max"),
            "gender": data.get("gender"),
            "religion": data.get("religion"),
            "country": data.get("country"),
            "verified_only": _truthy(data.get("verified_only")),
            "online_only": _truthy(data.get("online_only")),
        },
    )
    return JsonResponse({"ok": True, "message": "Filtres enregistrés.", "filters": filters})


@login_required
@require_POST
def profile_delete(request):
    profile = getattr(request.user, "profile", None)
    if not profile:
        return JsonResponse({"ok": False, "message": "Profil introuvable."}, status=400)
    logout(request)
    profile_controller.delete_account(profile)
    return JsonResponse({"ok": True, "redirect": "/"})

