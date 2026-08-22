"""Swipes & création de matchs."""

from __future__ import annotations

from datetime import timedelta

from django.db import transaction
from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from core.controllers import notification_controller
from core.models import Match, Profile, Swipe
from core.models.choices import MatchStatus, SwipeAction

PASS_COOLDOWN_DAYS = 14
LIKE_Q = Q(is_like=True) | Q(is_super_like=True)


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


def pass_cooldown_cutoff():
    return timezone.now() - timedelta(days=PASS_COOLDOWN_DAYS)


def excluded_swiped_ids(viewer: Profile) -> set:
    """Profils masqués du feed : likes permanents, pass actif (< 14 jours)."""
    cutoff = pass_cooldown_cutoff()
    return set(
        Swipe.objects.filter(swiper=viewer)
        .filter(LIKE_Q | Q(is_like=False, is_super_like=False, created_at__gte=cutoff))
        .values_list("swiped_id", flat=True)
    )


def apply_feed_exclusions(qs, viewer: Profile):
    """Exclut du queryset les profils déjà likés ou passés récemment."""
    cutoff = pass_cooldown_cutoff()
    active_pass = Swipe.objects.filter(
        swiper=viewer,
        swiped_id=OuterRef("pk"),
        is_like=False,
        is_super_like=False,
        created_at__gte=cutoff,
    )
    already_liked = Swipe.objects.filter(swiper=viewer, swiped_id=OuterRef("pk")).filter(LIKE_Q)
    return qs.annotate(
        _hide_active_pass=Exists(active_pass),
        _hide_liked=Exists(already_liked),
    ).filter(_hide_active_pass=False, _hide_liked=False)


@transaction.atomic
def set_flags(swiper: Profile, swiped_id, *, is_like: bool, is_super_like: bool) -> dict:
    from core.controllers import quota_controller

    try:
        swiped = Profile.objects.select_for_update().get(pk=swiped_id)
    except Profile.DoesNotExist:
        return {"ok": False, "error": "Profil introuvable."}

    if swiped.pk == swiper.pk:
        return {"ok": False, "error": "Action invalide."}

    is_like = bool(is_like)
    is_super_like = bool(is_super_like)
    action = _stored_action(is_like, is_super_like)
    ok, err, code = quota_controller.check_swipe(swiper, swiped_id, action)
    if not ok:
        return {
            "ok": False,
            "error": err,
            "code": code,
            "quota": quota_controller.snapshot(swiper),
        }
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
    # Horodater chaque décision (like, super like, pass) — cooldown pass 14 jours.
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
        reciprocal = Swipe.objects.filter(swiper=swiped, swiped=swiper).filter(like_q).first()
        if reciprocal:
            u1, u2 = _ordered_pair(swiper, swiped)
            match, _ = Match.objects.get_or_create(
                user_1=u1,
                user_2=u2,
                defaults={"status": MatchStatus.ACTIVE, "is_one_sided": False},
            )
            if match.status != MatchStatus.ACTIVE or match.is_one_sided:
                match.status = MatchStatus.ACTIVE
                match.is_one_sided = False
                match.save(update_fields=["status", "is_one_sided", "updated_at"])
            matched = True
            for p in (swiper, swiped):
                p.matches_count = Match.objects.filter(
                    status=MatchStatus.ACTIVE
                ).filter(models_q_participant(p)).count()
                p.save(update_fields=["matches_count", "updated_at"])
                partner = swiped if p.pk == swiper.pk else swiper
                notification_controller.notify_match(profile=p, partner=partner, match=match)
        else:
            if is_super_like and not was_super:
                notification_controller.notify_like(recipient=swiped, sender=swiper, is_super_like=True)
            elif is_like and not was_like:
                notification_controller.notify_like(recipient=swiped, sender=swiper, is_super_like=False)

    return {
        "ok": True,
        "swipe_id": str(swipe.id),
        "matched": matched,
        "match_id": str(match.id) if match else None,
        "created": created,
        "is_like": is_like,
        "is_super_like": is_super_like,
        "partner_name": swiped.first_name or "Membre",
        "partner_photo": swiped.primary_photo or "",
        "at": timezone.now().isoformat(),
        "quota": quota_controller.snapshot(swiper),
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
