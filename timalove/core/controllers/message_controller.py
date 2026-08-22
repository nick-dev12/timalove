"""Messages & freemium."""

from __future__ import annotations

import logging
import re

from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.controllers import notification_controller, site_settings_controller
from core.controllers.moderation_controller import has_blocked, is_blocked_between
from core.controllers.swipe_controller import models_q_participant
from core.models import ConversationHide, Match, Message, Profile
from core.models.choices import MatchStatus, MessageType

logger = logging.getLogger(__name__)

PHONE_RE = re.compile(r"(?:\+?\d[\d\s.\-]{7,}\d)")
PREVIEW_MAX = 52


def _chat_room_name(match: Match) -> str:
    lo, hi = sorted([str(match.user_1_id), str(match.user_2_id)])
    return f"chat_{lo}_{hi}"


def _broadcast_chat(match: Match, payload: dict) -> None:
    try:
        from asgiref.sync import async_to_sync
        from channels.layers import get_channel_layer

        layer = get_channel_layer()
        if not layer:
            return
        async_to_sync(layer.group_send)(
            _chat_room_name(match),
            {"type": "chat.message", "payload": payload},
        )
    except Exception as exc:
        logger.debug("[chat] websocket indisponible : %s", exc)


def _serialize_message_ws(msg: Message) -> dict:
    sender = msg.sender
    name = (sender.first_name or "Membre").strip() or "Membre"
    local = timezone.localtime(msg.created_at)
    is_voice = msg.message_type == MessageType.VOICE
    is_image = msg.message_type == MessageType.IMAGE
    seconds = msg.voice_duration_seconds or 0
    return {
        "id": str(msg.id),
        "content": "" if is_image else msg.content,
        "is_voice": is_voice,
        "is_image": is_image,
        "image_url": msg.content if is_image else "",
        "voice_url": msg.voice_url or "",
        "voice_duration": seconds,
        "voice_label": f"{seconds // 60}:{seconds % 60:02d}",
        "time": local.strftime("%H:%M"),
        "read": bool(msg.is_read),
        "photo_url": sender.primary_photo or "",
        "initial": name[:1].upper(),
        "sender_id": str(msg.sender_id),
    }


def _broadcast_new_message(match: Match, msg: Message) -> None:
    _broadcast_chat(
        match,
        {
            "event": "message",
            "sender_id": str(msg.sender_id),
            "item": _serialize_message_ws(msg),
        },
    )


def _broadcast_read_receipts(match: Match, reader: Profile) -> None:
    sender = match.partner_of(reader)
    read_ids = [
        str(mid)
        for mid in match.messages.filter(sender=sender, is_read=True).values_list("id", flat=True)
    ]
    if not read_ids:
        return
    _broadcast_chat(match, {"event": "read_receipts", "read_ids": read_ids})


def _format_list_time(dt) -> str:
    local = timezone.localtime(dt)
    today = timezone.localtime(timezone.now()).date()
    if local.date() == today:
        return local.strftime("%H:%M")
    if local.date() == today - timedelta(days=1):
        return "Hier"
    return local.strftime("%d/%m")


def _preview_text(last: Message | None, me: Profile) -> str:
    if not last:
        return "Nouvelle conversation"
    if last.message_type == MessageType.VOICE:
        text = "Vocal"
    elif last.message_type == MessageType.IMAGE:
        text = "Photo"
    else:
        text = (last.content or "").replace("\n", " ").strip() or "Nouvelle conversation"
    if last.sender_id == me.id:
        text = f"Vous : {text}"
    if len(text) > PREVIEW_MAX:
        return text[: PREVIEW_MAX - 1].rstrip() + "…"
    return text


def get_active_match(profile: Profile, partner_id) -> Match | None:
    try:
        partner = Profile.objects.get(pk=partner_id)
    except Profile.DoesNotExist:
        return None
    return (
        Match.objects.filter(models_q_participant(profile), models_q_participant(partner))
        .filter(status=MatchStatus.ACTIVE)
        .first()
    )


@transaction.atomic
def ensure_conversation(profile: Profile, partner_id) -> tuple[bool, str, Match | None]:
    """Ouvre une conversation : match existant ou création après like envoyé."""
    from core.controllers.swipe_controller import LIKE_Q, _ordered_pair
    from core.models import Swipe

    try:
        partner = Profile.objects.select_for_update().get(pk=partner_id)
    except Profile.DoesNotExist:
        return False, "Profil introuvable.", None

    if partner.pk == profile.pk:
        return False, "Action invalide.", None

    existing = get_active_match(profile, partner_id)
    if existing:
        return True, "", existing

    liked = Swipe.objects.filter(swiper=profile, swiped=partner).filter(LIKE_Q).exists()
    if not liked:
        return False, "Like requis pour démarrer une conversation.", None

    they_liked = Swipe.objects.filter(swiper=partner, swiped=profile).filter(LIKE_Q).exists()

    u1, u2 = _ordered_pair(profile, partner)
    match, _created = Match.objects.get_or_create(
        user_1=u1,
        user_2=u2,
        defaults={"status": MatchStatus.ACTIVE, "is_one_sided": not they_liked},
    )
    update_fields: list[str] = []
    if match.status != MatchStatus.ACTIVE:
        match.status = MatchStatus.ACTIVE
        update_fields.extend(["status", "updated_at"])
    target_one_sided = not they_liked
    if match.is_one_sided != target_one_sided:
        match.is_one_sided = target_one_sided
        update_fields.extend(["is_one_sided", "updated_at"])
    if update_fields:
        match.save(update_fields=list(dict.fromkeys(update_fields)))

    for p in (profile, partner):
        p.matches_count = Match.objects.filter(
            status=MatchStatus.ACTIVE
        ).filter(models_q_participant(p)).count()
        p.save(update_fields=["matches_count", "updated_at"])

    return True, "", match


def _block_flags(profile: Profile, partner: Profile) -> dict:
    blocked_by_me = has_blocked(profile, partner.id)
    blocked_me = has_blocked(partner, profile.id)
    return {
        "blocked_by_me": blocked_by_me,
        "blocked_me": blocked_me,
        "is_blocked": blocked_by_me or blocked_me,
    }


def _messaging_denied(profile: Profile, partner: Profile) -> str:
    if has_blocked(profile, partner.id):
        return "Vous avez bloqué ce profil. Débloquez-le pour envoyer un message."
    if has_blocked(partner, profile.id):
        return "Impossible d'envoyer un message à ce profil."
    return ""


def list_conversations(profile: Profile, include_hidden: bool = False) -> list[dict]:
    hidden_ids = set(
        ConversationHide.objects.filter(user=profile).values_list("partner_id", flat=True)
    )
    matches = (
        Match.objects.filter(models_q_participant(profile), status=MatchStatus.ACTIVE)
        .select_related("user_1", "user_2")
        .order_by("-updated_at")
    )
    results = []
    for m in matches:
        partner = m.partner_of(profile)
        if not include_hidden and partner.id in hidden_ids:
            continue
        if include_hidden and partner.id not in hidden_ids:
            continue
        last = m.messages.order_by("-created_at").first()
        unread = m.messages.filter(is_read=False).exclude(sender=profile).count()
        flags = _block_flags(profile, partner)
        preview = _preview_text(last, profile)
        if flags["blocked_by_me"]:
            preview = "Bloqué"
        results.append(
            {
                "match": m,
                "partner": partner,
                "last_message": last,
                "preview": preview,
                "unread": 0 if flags["blocked_by_me"] else unread,
                "last_time": _format_list_time(last.created_at) if last else "",
                **flags,
            }
        )
    return results


def unread_count(profile: Profile) -> int:
    match_ids = Match.objects.filter(
        models_q_participant(profile), status=MatchStatus.ACTIVE
    ).values_list("id", flat=True)
    return Message.objects.filter(match_id__in=match_ids, is_read=False).exclude(sender=profile).count()


def inbox_feed(profile: Profile) -> list[dict]:
    """Feed JSON pour l'inbox messages (temps réel)."""
    items: list[dict] = []
    for c in list_conversations(profile):
        partner = c["partner"]
        name = (partner.first_name or "Membre").strip() or "Membre"
        items.append(
            {
                "partner_id": str(partner.id),
                "partner_name": name,
                "partner_photo": partner.primary_photo or "",
                "partner_initial": name[:1].upper(),
                "partner_online": bool(partner.is_online),
                "preview": c["preview"] or "Nouvelle conversation",
                "last_time": c["last_time"] or "",
                "unread": int(c["unread"] or 0),
                "blocked_by_me": bool(c["blocked_by_me"]),
                "thread_url": f"/discussions/{partner.id}/",
            }
        )
    return items


def messages_for(profile: Profile, partner_id, limit: int = 100) -> list[Message]:
    match = get_active_match(profile, partner_id)
    if not match:
        return []
    return list(match.messages.select_related("sender").order_by("created_at")[:limit])


def _mask_phone(content: str) -> tuple[str, str | None]:
    if not site_settings_controller.get("phone_masking_enabled", True):
        return content, None
    if PHONE_RE.search(content):
        masked = PHONE_RE.sub("[numéro masqué]", content)
        return masked, content
    return content, None


def _sender_message_count(match: Match, sender: Profile) -> int:
    if match.user_1_id == sender.id:
        return match.user_1_message_count
    return match.user_2_message_count


def _increment_count(match: Match, sender: Profile) -> None:
    if match.user_1_id == sender.id:
        match.user_1_message_count += 1
    else:
        match.user_2_message_count += 1
    match.save(update_fields=["user_1_message_count", "user_2_message_count", "updated_at"])


def _message_preview(sender: Profile, content: str) -> str:
    text = (content or "").strip()
    if not text:
        return f"{sender.first_name} vous a écrit."
    if len(text) > 120:
        return f"{text[:117]}…"
    return text


def _notify_new_message(profile: Profile, match: Match, preview: str) -> None:
    notification_controller.notify_new_message(sender=profile, match=match, preview=preview)


def can_send(profile: Profile, match: Match) -> tuple[bool, str]:
    from core.controllers import quota_controller

    partner = match.partner_of(profile)
    denied = _messaging_denied(profile, partner)
    if denied:
        return False, denied
    ok, err = quota_controller.check_message(profile)
    if not ok:
        return False, err
    return True, ""


@transaction.atomic
def send_text(profile: Profile, partner_id, content: str) -> tuple[bool, str, Message | None]:
    match = get_active_match(profile, partner_id)
    if not match:
        return False, "Conversation introuvable.", None
    ok, err = can_send(profile, match)
    if not ok:
        return False, err, None
    content = (content or "").strip()
    if not content:
        return False, "Message vide.", None
    banned = site_settings_controller.get("banned_words", []) or []
    lower = content.lower()
    if any(w and w.lower() in lower for w in banned):
        return False, "Message refusé par la modération.", None

    masked, original = _mask_phone(content)
    msg = Message.objects.create(
        match=match,
        sender=profile,
        content=masked,
        message_type=MessageType.TEXT,
        original_content=original,
        is_flagged=bool(original),
    )
    _increment_count(match, profile)
    _notify_new_message(profile, match, _message_preview(profile, masked))
    _broadcast_new_message(match, msg)
    return True, "Envoyé.", msg


@transaction.atomic
def send_voice(
    profile: Profile, partner_id, voice_url: str, duration: int
) -> tuple[bool, str, Message | None]:
    match = get_active_match(profile, partner_id)
    if not match:
        return False, "Conversation introuvable.", None
    ok, err = can_send(profile, match)
    if not ok:
        return False, err, None
    msg = Message.objects.create(
        match=match,
        sender=profile,
        content="",
        message_type=MessageType.VOICE,
        voice_url=voice_url,
        voice_duration_seconds=duration,
    )
    _increment_count(match, profile)
    _notify_new_message(profile, match, f"{profile.first_name} vous a envoyé un vocal.")
    _broadcast_new_message(match, msg)
    return True, "Envoyé.", msg


@transaction.atomic
def send_image(profile: Profile, partner_id, image_url: str) -> tuple[bool, str, Message | None]:
    match = get_active_match(profile, partner_id)
    if not match:
        return False, "Conversation introuvable.", None
    ok, err = can_send(profile, match)
    if not ok:
        return False, err, None
    url = (image_url or "").strip()
    if not url:
        return False, "Image manquante.", None
    msg = Message.objects.create(
        match=match,
        sender=profile,
        content=url,
        message_type=MessageType.IMAGE,
    )
    _increment_count(match, profile)
    _notify_new_message(profile, match, f"{profile.first_name} vous a envoyé une photo.")
    _broadcast_new_message(match, msg)
    return True, "Envoyé.", msg


def send_media(
    profile: Profile, partner_id, kind: str, upload, duration: int = 0
) -> tuple[bool, str, Message | None]:
    from core.controllers import chat_media_controller as media

    kind = (kind or "").strip().lower()
    if not upload:
        return False, "Fichier manquant.", None
    try:
        if kind in {"photo", "image", "photos"}:
            url = media.store_chat_image(profile.id, upload)
            return send_image(profile, partner_id, url)
        if kind in {"voice", "vocal"}:
            seconds = max(1, min(int(duration or 1), media.VOICE_MAX_SECONDS))
            url = media.store_chat_voice(profile.id, upload)
            return send_voice(profile, partner_id, url, seconds)
    except ValueError as exc:
        return False, str(exc), None
    return False, "Type de média inconnu.", None


def mark_read(profile: Profile, partner_id) -> int:
    match = get_active_match(profile, partner_id)
    if not match:
        return 0
    qs = match.messages.filter(is_read=False).exclude(sender=profile)
    count = qs.update(is_read=True, read_at=timezone.now())
    # Toujours notifier l'expéditeur (WS) même si les messages étaient déjà lus.
    _broadcast_read_receipts(match, profile)
    return count


def read_receipts(profile: Profile, partner_id) -> list[str]:
    """IDs des messages envoyés par l'utilisateur et lus par le partenaire."""
    match = get_active_match(profile, partner_id)
    if not match:
        return []
    return [
        str(mid)
        for mid in match.messages.filter(sender=profile, is_read=True).values_list("id", flat=True)
    ]


@transaction.atomic
def delete_message(profile: Profile, message_id) -> tuple[bool, str]:
    """Supprime un message envoyé par l'utilisateur connecté."""
    try:
        msg = Message.objects.select_related("match").get(pk=message_id)
    except Message.DoesNotExist:
        return False, "Message introuvable."

    if msg.sender_id != profile.id:
        return False, "Vous ne pouvez supprimer que vos propres messages."

    match = msg.match
    if profile.id not in (match.user_1_id, match.user_2_id):
        return False, "Accès refusé."

    msg.delete()
    return True, "Message supprimé."


def hide_conversation(profile: Profile, partner_id) -> tuple[bool, str]:
    try:
        partner = Profile.objects.get(pk=partner_id)
    except Profile.DoesNotExist:
        return False, "Profil introuvable."
    ConversationHide.objects.get_or_create(user=profile, partner=partner)
    return True, "Discussion supprimée."


def unhide_conversation(profile: Profile, partner_id) -> None:
    ConversationHide.objects.filter(user=profile, partner_id=partner_id).delete()


def _person_card(profile: Profile) -> dict:
    name = (profile.first_name or "Membre").strip() or "Membre"
    return {
        "id": profile.id,
        "first_name": name,
        "photo_url": profile.primary_photo or "",
        "is_online": bool(profile.is_online),
        "initial": name[:1].upper(),
    }


def _serialize_message(msg: Message, me: Profile) -> dict:
    sender = msg.sender
    name = (sender.first_name or "Membre").strip() or "Membre"
    local = timezone.localtime(msg.created_at)
    is_voice = msg.message_type == MessageType.VOICE
    is_image = msg.message_type == MessageType.IMAGE
    return {
        "id": str(msg.id),
        "mine": msg.sender_id == me.id,
        "content": "" if is_image else msg.content,
        "is_voice": is_voice,
        "is_image": is_image,
        "image_url": msg.content if is_image else "",
        "voice_url": msg.voice_url or "",
        "voice_duration": msg.voice_duration_seconds or 0,
        "voice_label": f"{(msg.voice_duration_seconds or 0) // 60}:{(msg.voice_duration_seconds or 0) % 60:02d}",
        "time": local.strftime("%H:%M"),
        "read": bool(msg.is_read),
        "photo_url": sender.primary_photo or "",
        "initial": name[:1].upper(),
    }


def thread_for(profile: Profile, partner_id) -> dict | None:
    match = get_active_match(profile, partner_id)
    if not match:
        return None
    partner = match.partner_of(profile)
    from core.controllers import quota_controller

    flags = _block_flags(profile, partner)
    items = [_serialize_message(msg, profile) for msg in messages_for(profile, partner_id)]
    denied = _messaging_denied(profile, partner)
    quota_ok, quota_err = quota_controller.check_message(profile)
    blocked = bool(flags["is_blocked"])
    return {
        "me": _person_card(profile),
        "partner": _person_card(partner),
        "thread_items": items,
        "match": match,
        **flags,
        "can_send": not blocked and not denied,
        "quota_locked": (not blocked) and not quota_ok,
        "quota_message": quota_err if (not blocked and not quota_ok) else "",
        "messages_remaining": quota_controller.messages_remaining(profile),
    }


def demo_conversations() -> list[dict]:
    """Inbox d’aperçu : conversations fictives pour le design, avant la logique live."""
    from core.controllers import explore_controller

    cards, _ = explore_controller.public_feed(offset=0, limit=8, seed="messages-demo")
    samples = [
        ("Kofi", "Avec plaisir. Un vocal rendrait la conversation plus personnelle.", "10:36", 2, True),
        ("Awa", "Vous : Merci pour votre message, j’ai lu votre profil avec attention.", "09:12", 0, True),
        ("Maguette", "Bonjour, ravi de notre match. Comment se passe votre semaine ?", "Hier", 1, False),
        ("Ibrahima", "Vous : Oui, la foi et la famille comptent beaucoup pour moi.", "Hier", 0, False),
        ("Sokhna", "J’aimerais beaucoup échanger, avec sincérité.", "Lun.", 3, True),
        ("Mamadou", "Vous : À très vite alors.", "12/08", 0, False),
    ]
    results = []
    for index, (name, preview, when, unread, online) in enumerate(samples):
        card = cards[index] if index < len(cards) else {}
        photo = card.get("photo_url") or ""
        pid = card.get("id") or f"demo-{index}"
        results.append(
            {
                "partner": {
                    "id": pid,
                    "first_name": card.get("first_name") or name,
                    "primary_photo": photo,
                    "is_online": online,
                },
                "preview": preview,
                "last_time": when,
                "unread": unread,
                "demo": True,
            }
        )
    return results


def demo_thread() -> dict:
    me = {
        "id": None,
        "first_name": "Ama",
        "photo_url": "",
        "is_online": True,
        "initial": "A",
    }
    partner = {
        "id": None,
        "first_name": "Kofi",
        "photo_url": "",
        "is_online": True,
        "initial": "K",
    }
    return {
        "me": me,
        "partner": partner,
        "thread_items": [
            {
                "mine": False,
                "content": "Bonjour Ama, ravi de notre match. Comment vas-tu aujourd’hui ?",
                "is_voice": False,
                "voice_duration": 0,
                "time": "10:30",
                "read": True,
                "photo_url": "",
                "initial": "K",
            },
            {
                "mine": True,
                "content": "Bonjour Kofi ! Très bien, merci. Ton profil m’a vraiment touchée.",
                "is_voice": False,
                "voice_duration": 0,
                "time": "10:32",
                "read": True,
                "photo_url": "",
                "initial": "A",
            },
            {
                "mine": False,
                "content": "Merci. J’aimerais beaucoup apprendre à te connaître, avec sincérité.",
                "is_voice": False,
                "voice_duration": 0,
                "time": "10:35",
                "read": True,
                "photo_url": "",
                "initial": "K",
            },
            {
                "mine": True,
                "content": "Avec plaisir. Un vocal rendrait la conversation plus personnelle.",
                "is_voice": False,
                "voice_duration": 0,
                "time": "10:36",
                "read": True,
                "photo_url": "",
                "initial": "A",
            },
        ],
    }


def demo_thread_for(member: dict | None = None, me: dict | None = None) -> dict:
    """Fil d’aperçu personnalisé avec le prénom et la photo du partenaire cliqué."""
    data = demo_thread()
    member = member or {}
    partner_name = member.get("first_name") or data["partner"]["first_name"]
    photo = member.get("photo_url") or member.get("primary_photo") or ""
    initial = partner_name[:1].upper()
    data["partner"] = {
        "id": member.get("id") or data["partner"]["id"],
        "first_name": partner_name,
        "photo_url": photo,
        "is_online": bool(member.get("is_online", True)),
        "initial": initial,
    }
    if me:
        merged = {**data["me"], **me}
        merged["initial"] = merged.get("initial") or (merged.get("first_name") or "M")[:1].upper()
        data["me"] = merged
    me_name = data["me"]["first_name"]
    for item in data["thread_items"]:
        if item["mine"]:
            item["photo_url"] = data["me"].get("photo_url") or ""
            item["initial"] = data["me"]["initial"]
            item["content"] = (
                item["content"].replace("Ama", me_name).replace("Kofi", partner_name)
            )
        else:
            item["photo_url"] = photo
            item["initial"] = initial
            item["content"] = (
                item["content"].replace("Ama", me_name).replace("Kofi", partner_name)
            )
    return data
