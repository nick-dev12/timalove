"""Messages & freemium."""

from __future__ import annotations

import re

from datetime import timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.controllers import notification_controller, site_settings_controller
from core.controllers.swipe_controller import models_q_participant
from core.models import ConversationHide, Match, Message, Profile
from core.models.choices import Gender, MatchStatus, MessageType, NotificationType


PHONE_RE = re.compile(r"(?:\+?\d[\d\s.\-]{7,}\d)")
PREVIEW_MAX = 52


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
        results.append(
            {
                "match": m,
                "partner": partner,
                "last_message": last,
                "preview": _preview_text(last, profile),
                "unread": unread,
                "last_time": _format_list_time(last.created_at) if last else "",
            }
        )
    return results


def unread_count(profile: Profile) -> int:
    match_ids = Match.objects.filter(
        models_q_participant(profile), status=MatchStatus.ACTIVE
    ).values_list("id", flat=True)
    return Message.objects.filter(match_id__in=match_ids, is_read=False).exclude(sender=profile).count()


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


def can_send(profile: Profile, match: Match) -> tuple[bool, str]:
    if profile.gender == Gender.FEMALE or profile.has_active_subscription:
        return True, ""
    limit = int(site_settings_controller.get("free_messages_limit", 3))
    count = _sender_message_count(match, profile)
    if count >= limit:
        return False, "Limite de messages gratuits atteinte. Passez Premium pour continuer."
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
    partner = match.partner_of(profile)
    notification_controller.create(
        user=partner,
        type=NotificationType.NEW_MESSAGE,
        title="Nouveau message",
        message=f"{profile.first_name} vous a écrit.",
        related_user=profile,
        related_match=match,
    )
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
    return True, "Envoyé.", msg


def mark_read(profile: Profile, partner_id) -> int:
    match = get_active_match(profile, partner_id)
    if not match:
        return 0
    qs = match.messages.filter(is_read=False).exclude(sender=profile)
    return qs.update(is_read=True, read_at=timezone.now())


def hide_conversation(profile: Profile, partner_id) -> None:
    partner = Profile.objects.get(pk=partner_id)
    ConversationHide.objects.get_or_create(user=profile, partner=partner)


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
    return {
        "mine": msg.sender_id == me.id,
        "content": msg.content,
        "is_voice": msg.message_type == MessageType.VOICE,
        "voice_duration": msg.voice_duration_seconds or 0,
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
    items = [_serialize_message(msg, profile) for msg in messages_for(profile, partner_id)]
    return {
        "me": _person_card(profile),
        "partner": _person_card(partner),
        "thread_items": items,
        "match": match,
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
