"""Swipes & création de matchs."""

from __future__ import annotations

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from core.controllers import notification_controller
from core.models import Match, Profile, Swipe
from core.models.choices import MatchStatus, NotificationType, SwipeAction


def _ordered_pair(a: Profile, b: Profile) -> tuple[Profile, Profile]:
    return (a, b) if str(a.id) < str(b.id) else (b, a)


def models_q_participant(profile: Profile):
    return Q(user_1=profile) | Q(user_2=profile)


def _counts_as_like(is_like: bool, is_super_like: bool) -> bool:
    return bool(is_like or is_super_like)


def _stored_action(is_like: bool, is_super_like: bool) -> str:
    if is_super_like:
        return SwipeAction.SUPER_LIKE
    if is_like:
        return SwipeAction.LIKE
    return SwipeAction.PASS


@transaction.atomic
def set_flags(swiper: Profile, swiped_id, *, is_like: bool, is_super_like: bool) -> dict:
    try:
        swiped = Profile.objects.select_for_update().get(pk=swiped_id)
    except Profile.DoesNotExist:
        return {"ok": False, "error": "Profil introuvable."}

    if swiped.pk == swiper.pk:
        return {"ok": False, "error": "Action invalide."}

    is_like = bool(is_like)
    is_super_like = bool(is_super_like)
    action = _stored_action(is_like, is_super_like)
    counts = _counts_as_like(is_like, is_super_like)

    existing = Swipe.objects.filter(swiper=swiper, swiped=swiped).first()
    was_like = bool(existing and existing.is_like)
    was_super = bool(existing and existing.is_super_like)

    swipe, created = Swipe.objects.update_or_create(
        swiper=swiper,
        swiped=swiped,
        defaults={
            "action": action,
            "is_like": is_like,
            "is_super_like": is_super_like,
        },
    )
    if counts:
        Swipe.objects.filter(pk=swipe.pk).update(created_at=timezone.now())
        swipe.refresh_from_db(fields=["created_at"])

    match = None
    matched = False
    like_q = Q(is_like=True) | Q(is_super_like=True)
    swiper.likes_given_count = Swipe.objects.filter(swiper=swiper).filter(like_q).count()
    swiper.save(update_fields=["likes_given_count", "updated_at"])
    swiped.likes_received_count = Swipe.objects.filter(swiped=swiped).filter(like_q).count()
    swiped.save(update_fields=["likes_received_count", "updated_at"])

    if counts:
        if is_super_like and not was_super:
            notification_controller.create(
                user=swiped,
                type=NotificationType.NEW_LIKE,
                title="Super like",
                message=f"{swiper.first_name} vous a envoyé un Super like.",
                related_user=swiper,
            )
        elif is_like and not was_like:
            notification_controller.create(
                user=swiped,
                type=NotificationType.NEW_LIKE,
                title="Nouveau like",
                message=f"{swiper.first_name} a aimé votre profil.",
                related_user=swiper,
            )

        reciprocal = Swipe.objects.filter(swiper=swiped, swiped=swiper).filter(like_q).first()
        if reciprocal:
            u1, u2 = _ordered_pair(swiper, swiped)
            match, _ = Match.objects.get_or_create(
                user_1=u1,
                user_2=u2,
                defaults={"status": MatchStatus.ACTIVE},
            )
            if match.status != MatchStatus.ACTIVE:
                match.status = MatchStatus.ACTIVE
                match.save(update_fields=["status", "updated_at"])
            matched = True
            for p in (swiper, swiped):
                p.matches_count = Match.objects.filter(
                    status=MatchStatus.ACTIVE
                ).filter(models_q_participant(p)).count()
                p.save(update_fields=["matches_count", "updated_at"])
                notification_controller.create(
                    user=p,
                    type=NotificationType.NEW_MATCH,
                    title="Nouveau match",
                    message="Vous avez un nouveau match !",
                    related_user=swiped if p.pk == swiper.pk else swiper,
                    related_match=match,
                )

    return {
        "ok": True,
        "swipe_id": str(swipe.id),
        "matched": matched,
        "match_id": str(match.id) if match else None,
        "created": created,
        "is_like": is_like,
        "is_super_like": is_super_like,
        "at": timezone.now().isoformat(),
    }


@transaction.atomic
def record_swipe(swiper: Profile, swiped_id, action: str) -> dict:
    action = action if action in SwipeAction.values else SwipeAction.PASS
    existing = Swipe.objects.filter(swiper=swiper, swiped_id=swiped_id).first()
    prev_like = bool(existing and existing.is_like)
    prev_super = bool(existing and existing.is_super_like)

    if action == SwipeAction.PASS:
        is_like = False
        is_super = False
    elif action == SwipeAction.LIKE:
        is_like = True
        is_super = prev_super
    else:
        is_super = True
        is_like = prev_like

    return set_flags(swiper, swiped_id, is_like=is_like, is_super_like=is_super)
