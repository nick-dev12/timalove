"""Parcours d’intention : 1 vocal de 15 s (ou texte de secours) avant le chat libre."""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from core.controllers import chat_media_controller, notification_controller
from core.data.guided_prompts import GUIDED_STEPS, prompts_for_match
from core.models import GuidedIntroClip, Match, Message, Profile, Swipe
from core.models.choices import ConversationStatus, MessageType, NotificationType

GUIDED_VOICE_MAX_SECONDS = chat_media_controller.GUIDED_VOICE_MAX_SECONDS
GUIDED_TEXT_MIN = 20
GUIDED_TEXT_MAX = 400
REVIEW_TTL = timedelta(hours=48)
DECLINE_NOTICE = "La discussion a été refusée. Veuillez retenter votre chance."
TIMEOUT_NOTICE = "Pas de réponse cette fois. Vous pouvez retenter votre chance."


def _name(profile: Profile) -> str:
    return (profile.first_name or "cette personne").strip() or "cette personne"


def prompts_for(match: Match, partner: Profile) -> tuple[str, ...]:
    from core.controllers import app_config_controller

    if not app_config_controller.guided_messages_enabled():
        return ()
    return prompts_for_match(match.id, _name(partner))


def opener_of(match: Match) -> Profile | None:
    if match.conversation_initiator_id:
        return match.conversation_initiator
    clip = match.guided_clips.select_related("sender").order_by("step", "created_at").first()
    return clip.sender if clip else None


def is_opener(match: Match, profile: Profile) -> bool:
    opener = opener_of(match)
    return bool(opener and opener.id == profile.id)


def is_recipient(match: Match, profile: Profile) -> bool:
    opener = opener_of(match)
    return bool(opener and opener.id != profile.id and match.is_participant(profile))


def needs_guided_intro(match: Match) -> bool:
    if match.guided_intro_completed:
        return False
    from core.controllers import app_config_controller

    if not app_config_controller.guided_messages_enabled():
        return False
    if match.messages.exists() and not match.guided_intro_submitted:
        return False
    return True


def occupies_conversation_slot(match: Match) -> bool:
    if match.conversation_status != ConversationStatus.ACCEPTED:
        return False
    if match.guided_intro_completed:
        return True
    if match.guided_intro_submitted:
        return False
    return match.messages.exists()


def recorded_count(match: Match, sender: Profile) -> int:
    return match.guided_clips.filter(sender=sender).count()


def clips_payload(match: Match) -> list[dict]:
    rows = []
    for clip in match.guided_clips.select_related("sender").order_by("step", "created_at"):
        seconds = int(clip.duration_seconds or 0)
        rows.append(
            {
                "id": str(clip.id),
                "step": clip.step,
                "question": clip.question,
                "voice_url": clip.voice_url or "",
                "answer_text": clip.answer_text or "",
                "is_text": bool(clip.answer_text and not clip.voice_url),
                "duration": seconds,
                "voice_label": f"{seconds // 60}:{seconds % 60:02d}" if seconds else "",
                "sender_name": _name(clip.sender),
            }
        )
    return rows


def thread_state(match: Match, viewer: Profile) -> str:
    if not needs_guided_intro(match):
        return "open"
    opener = opener_of(match)
    if match.guided_intro_submitted:
        if opener and viewer.id == opener.id:
            return "waiting"
        return "review"
    if opener is None or viewer.id == opener.id:
        return "recording"
    return "hidden"


def _ensure_opener(match: Match, profile: Profile) -> Match:
    if match.conversation_initiator_id:
        return match
    match.conversation_initiator = profile
    match.save(update_fields=["conversation_initiator", "updated_at"])
    return match


def _notify(*, user: Profile, title: str, message: str, related: Profile, match: Match | None = None) -> None:
    notification_controller.create(
        user=user,
        type=NotificationType.NEW_MESSAGE,
        title=title,
        message=message,
        related_user=related,
        related_match=match,
    )


def _prepare_recording(profile: Profile, partner_id) -> tuple[bool, str, Match | None, list[str]]:
    from core.controllers import message_controller

    opened, err, match = message_controller._match_for_send(profile, partner_id)
    if not opened or match is None:
        return False, err or "Conversation introuvable.", None, []
    if not needs_guided_intro(match):
        return False, "Le parcours d’intention est déjà terminé.", match, []
    match = _ensure_opener(match, profile)
    opener = opener_of(match)
    if opener and opener.id != profile.id:
        return False, "C’est à l’autre personne d’écouter cette intention.", match, []
    if match.guided_intro_submitted:
        return False, "Votre intention a déjà été envoyée.", match, []
    partner = match.partner_of(profile)
    prompts = list(prompts_for(match, partner))
    if len(prompts) < GUIDED_STEPS:
        return False, "La question d’intention est indisponible.", match, []
    if recorded_count(match, profile) >= GUIDED_STEPS:
        match.guided_intro_submitted = True
        match.save(update_fields=["guided_intro_submitted", "updated_at"])
        return False, "Votre intention a déjà été envoyée.", match, prompts
    return True, "", match, prompts


def _finalize_clip(match: Match, profile: Profile, partner: Profile) -> dict:
    match.guided_intro_submitted = True
    match.save(update_fields=["guided_intro_submitted", "updated_at"])
    _notify(
        user=partner,
        title="Nouvelle intention",
        message=f"{_name(profile)} souhaite vous écrire. Écoutez et décidez.",
        related=profile,
        match=match,
    )
    return {
        "step": GUIDED_STEPS,
        "done": True,
        "next_step": None,
        "next_prompt": "",
        "headline": f"Pourquoi voulez-vous écrire à {_name(partner)} ?",
        "partner_name": _name(partner),
        "message": f"Votre intention a été envoyée à {_name(partner)}. Une réponse arrive en général sous 48 h.",
    }


@transaction.atomic
def submit_clip(profile: Profile, partner_id, upload, duration: int) -> tuple[bool, str, dict]:
    ok, err, match, prompts = _prepare_recording(profile, partner_id)
    if not ok or match is None:
        return False, err, {}
    partner = match.partner_of(profile)
    try:
        seconds = max(1, min(int(duration or 1), GUIDED_VOICE_MAX_SECONDS))
    except (TypeError, ValueError):
        seconds = 1
    try:
        url = chat_media_controller.store_guided_voice(profile.id, upload)
    except ValueError as exc:
        return False, str(exc), {}
    GuidedIntroClip.objects.create(
        match=match,
        sender=profile,
        step=1,
        question=prompts[0],
        voice_url=url,
        answer_text="",
        duration_seconds=seconds,
    )
    payload = _finalize_clip(match, profile, partner)
    return True, payload["message"], payload


@transaction.atomic
def submit_text(profile: Profile, partner_id, content: str) -> tuple[bool, str, dict]:
    ok, err, match, prompts = _prepare_recording(profile, partner_id)
    if not ok or match is None:
        return False, err, {}
    text = " ".join((content or "").split()).strip()
    if len(text) < GUIDED_TEXT_MIN:
        return False, f"Écrivez au moins {GUIDED_TEXT_MIN} caractères.", {}
    if len(text) > GUIDED_TEXT_MAX:
        return False, f"{GUIDED_TEXT_MAX} caractères maximum.", {}
    partner = match.partner_of(profile)
    GuidedIntroClip.objects.create(
        match=match,
        sender=profile,
        step=1,
        question=prompts[0],
        voice_url="",
        answer_text=text,
        duration_seconds=0,
    )
    payload = _finalize_clip(match, profile, partner)
    return True, payload["message"], payload


def _materialize_clips(match: Match) -> None:
    if match.messages.exists():
        return
    for clip in match.guided_clips.select_related("sender").order_by("step", "created_at"):
        if clip.voice_url:
            Message.objects.create(
                match=match,
                sender=clip.sender,
                content=clip.question,
                message_type=MessageType.VOICE,
                voice_url=clip.voice_url,
                voice_duration_seconds=clip.duration_seconds,
            )
        else:
            Message.objects.create(
                match=match,
                sender=clip.sender,
                content=f"{clip.question}\n\n{clip.answer_text}".strip(),
                message_type=MessageType.TEXT,
            )


@transaction.atomic
def accept_intro(profile: Profile, partner_id) -> tuple[bool, str]:
    from core.controllers import message_controller

    match = message_controller.get_active_match(profile, partner_id)
    if not match:
        return False, "Conversation introuvable."
    if not match.guided_intro_submitted or match.guided_intro_completed:
        return False, "Aucune introduction à valider."
    if is_opener(match, profile):
        return False, "Seul le destinataire peut continuer la discussion."

    opener = opener_of(match) or match.partner_of(profile)
    _materialize_clips(match)
    match.guided_intro_completed = True
    match.conversation_status = ConversationStatus.ACCEPTED
    match.save(update_fields=["guided_intro_completed", "conversation_status", "updated_at"])
    _notify(
        user=opener,
        title="Discussion acceptée",
        message=f"{_name(profile)} a accepté de poursuivre la discussion.",
        related=profile,
        match=match,
    )
    return True, "Vous pouvez continuer la discussion."


def _delete_clip_files(match: Match) -> None:
    urls = list(match.guided_clips.values_list("voice_url", flat=True))
    urls.extend(match.messages.exclude(voice_url="").exclude(voice_url__isnull=True).values_list("voice_url", flat=True))
    seen: set[str] = set()
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            chat_media_controller.delete_media_file(url)


def _teardown_intro(match: Match, *, notify_opener: str | None, related: Profile | None) -> Profile | None:
    from core.controllers.swipe_controller import LIKE_Q

    opener = opener_of(match)
    recipient = match.partner_of(opener) if opener else None
    _delete_clip_files(match)
    match.delete()
    if opener and recipient:
        Swipe.objects.filter(swiper=opener, swiped=recipient).filter(LIKE_Q).delete()
    if notify_opener and opener and related:
        _notify(
            user=opener,
            title="Discussion expirée" if "cette fois" in notify_opener else "Discussion refusée",
            message=notify_opener,
            related=related,
            match=None,
        )
    return opener


@transaction.atomic
def reject_intro(profile: Profile, partner_id) -> tuple[bool, str]:
    from core.controllers import message_controller

    match = message_controller.get_active_match(profile, partner_id)
    if not match:
        return False, "Conversation introuvable."
    if not match.guided_intro_submitted or match.guided_intro_completed:
        return False, "Aucune introduction à refuser."
    if is_opener(match, profile):
        return False, "Seul le destinataire peut refuser la discussion."
    _teardown_intro(match, notify_opener=DECLINE_NOTICE, related=profile)
    return True, "Discussion refusée."


@transaction.atomic
def withdraw_intro(profile: Profile, partner_id) -> tuple[bool, str]:
    from core.controllers import message_controller

    match = message_controller.get_active_match(profile, partner_id)
    if not match:
        return False, "Conversation introuvable."
    if match.guided_intro_completed:
        return False, "La discussion est déjà ouverte."
    if not is_opener(match, profile):
        return False, "Vous ne pouvez retirer que votre propre demande."
    _delete_clip_files(match)
    match.delete()
    return True, "Demande retirée. Votre place est libre."


@transaction.atomic
def block_intro(profile: Profile, partner_id) -> tuple[bool, str]:
    from core.controllers.moderation_controller import block_user

    ok, msg = reject_intro(profile, partner_id)
    if not ok:
        return False, msg
    blocked_ok, blocked_msg = block_user(profile, partner_id)
    if not blocked_ok:
        return True, msg
    return True, blocked_msg


@transaction.atomic
def expire_one(match: Match) -> bool:
    if not match.guided_intro_submitted or match.guided_intro_completed:
        return False
    recipient = match.partner_of(opener_of(match)) if opener_of(match) else match.user_1
    _teardown_intro(match, notify_opener=TIMEOUT_NOTICE, related=recipient)
    return True


def expire_stale_intros(*, limit: int = 80) -> int:
    cutoff = timezone.now() - REVIEW_TTL
    stale = list(
        Match.objects.filter(
            guided_intro_submitted=True,
            guided_intro_completed=False,
            updated_at__lt=cutoff,
        ).select_related("user_1", "user_2", "conversation_initiator")[:limit]
    )
    expired = 0
    for match in stale:
        if expire_one(match):
            expired += 1
    return expired


def expire_match_if_stale(match: Match | None) -> Match | None:
    if match is None:
        return None
    if not match.guided_intro_submitted or match.guided_intro_completed:
        return match
    if timezone.now() - match.updated_at < REVIEW_TTL:
        return match
    expire_one(match)
    return None


def context_for(match: Match, viewer: Profile) -> dict:
    partner = match.partner_of(viewer)
    prompts = list(prompts_for(match, partner))
    opener = opener_of(match)
    state = thread_state(match, viewer)
    count = recorded_count(match, opener or viewer) if opener or state == "recording" else 0
    current = prompts[0] if prompts and state == "recording" else ""
    remaining_hours = 48
    if state == "waiting":
        elapsed = timezone.now() - match.updated_at
        remaining_hours = max(0, int((REVIEW_TTL - elapsed).total_seconds() // 3600))
    return {
        "guided_intro_required": needs_guided_intro(match),
        "guided_state": state,
        "guided_waiting": state == "waiting",
        "guided_review_required": state == "review",
        "guided_recording": state == "recording",
        "guided_step": 1,
        "guided_step_total": GUIDED_STEPS,
        "guided_current_prompt": current,
        "guided_prompts": prompts,
        "guided_headline": f"Pourquoi voulez-vous écrire à {_name(partner)} ?",
        "guided_partner_name": _name(partner),
        "guided_clips": clips_payload(match) if state in {"review", "waiting"} else [],
        "guided_recorded_count": count,
        "guided_max_seconds": GUIDED_VOICE_MAX_SECONDS,
        "guided_text_max": GUIDED_TEXT_MAX,
        "guided_wait_hours": remaining_hours,
    }
