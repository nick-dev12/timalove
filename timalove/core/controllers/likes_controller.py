"""Likes entrants et historique des likes envoyés."""

from __future__ import annotations

from django.db.models import Case, IntegerField, Q, Value, When

from core.models import Match, Profile, Swipe
from core.models.choices import MatchStatus, SwipeAction
from core.controllers.swipe_controller import models_q_participant

LIKE_Q = (
    Q(is_like=True)
    | Q(is_super_like=True)
    | Q(action=SwipeAction.LIKE)
    | Q(action=SwipeAction.SUPER_LIKE)
)
INCOMING_PAGE_SIZE = 60


def _is_incoming_super_like(swipe: Swipe) -> bool:
    return bool(swipe.is_super_like or swipe.action == SwipeAction.SUPER_LIKE)


def _should_hide_incoming_liker(profile: Profile, swiper_id) -> bool:
    """Masquer uniquement si l'utilisateur a passé après avoir reçu le like."""
    their_like = (
        Swipe.objects.filter(swiper_id=swiper_id, swiped=profile)
        .filter(LIKE_Q)
        .order_by("-created_at")
        .first()
    )
    if not their_like:
        return False
    my_swipe = Swipe.objects.filter(swiper=profile, swiped_id=swiper_id).first()
    if not my_swipe or my_swipe.is_like or my_swipe.is_super_like:
        return False
    if my_swipe.action != SwipeAction.PASS:
        return False
    return my_swipe.created_at >= their_like.created_at


def _matched_ids(profile: Profile) -> set:
    ids: set = set()
    for match in Match.objects.filter(models_q_participant(profile), status=MatchStatus.ACTIVE):
        ids.add(match.partner_of(profile).id)
    return ids


def _liked_me_ids(profile: Profile) -> set:
    return set(
        Swipe.objects.filter(swiped=profile).filter(LIKE_Q).values_list("swiper_id", flat=True)
    )


def _they_liked_me(profile: Profile, partner_id) -> bool:
    return partner_id in _liked_me_ids(profile)


def _match_with_partner(profile: Profile, partner_id) -> Match | None:
    try:
        partner = Profile.objects.get(pk=partner_id)
    except Profile.DoesNotExist:
        return None
    return (
        Match.objects.filter(models_q_participant(profile), models_q_participant(partner))
        .filter(status=MatchStatus.ACTIVE)
        .first()
    )


def _should_include_match_on_incoming(profile: Profile, partner_id) -> bool:
    """Exclut les conversations ouvertes sans like retour."""
    if _they_liked_me(profile, partner_id):
        return True
    match = _match_with_partner(profile, partner_id)
    if match and match.is_one_sided:
        return False
    return True


def _is_visible_partner(partner: Profile) -> bool:
    return not getattr(partner, "banned_at", None) and not getattr(partner, "suspended_at", None)


def _incoming_item(
    partner: Profile,
    *,
    is_super_like: bool,
    is_matched: bool,
    already_liked_back: bool,
    created_at,
) -> dict:
    return {
        "profile": partner,
        "is_super_like": is_super_like,
        "is_matched": is_matched,
        "already_liked_back": already_liked_back,
        "created_at": created_at,
    }


def incoming(profile: Profile, limit: int | None = None) -> list[dict]:
    liked_me = Swipe.objects.filter(swiped=profile).filter(LIKE_Q).select_related("swiper")
    my_likes = set(
        Swipe.objects.filter(swiper=profile).filter(LIKE_Q).values_list("swiped_id", flat=True)
    )
    matched_ids = _matched_ids(profile)
    seen_swiper_ids: set = set()
    match_dates: dict = {}
    for match in Match.objects.filter(models_q_participant(profile), status=MatchStatus.ACTIVE):
        partner_id = match.partner_of(profile).id
        match_dates[partner_id] = match.updated_at or match.created_at

    results = []
    for swipe in liked_me:
        if swipe.swiper_id in seen_swiper_ids:
            continue
        if _should_hide_incoming_liker(profile, swipe.swiper_id):
            continue
        swiper = swipe.swiper
        if not _is_visible_partner(swiper):
            continue
        seen_swiper_ids.add(swipe.swiper_id)
        results.append(
            _incoming_item(
                swiper,
                is_super_like=_is_incoming_super_like(swipe),
                is_matched=swipe.swiper_id in matched_ids,
                already_liked_back=swipe.swiper_id in my_likes,
                created_at=swipe.created_at,
            )
        )

    missing_match_ids = matched_ids - seen_swiper_ids
    if missing_match_ids:
        partners = {p.id: p for p in Profile.objects.filter(pk__in=missing_match_ids)}
        for partner_id in missing_match_ids:
            if not _should_include_match_on_incoming(profile, partner_id):
                continue
            if _should_hide_incoming_liker(profile, partner_id):
                continue
            partner = partners.get(partner_id)
            if not partner or not _is_visible_partner(partner):
                continue
            seen_swiper_ids.add(partner_id)
            results.append(
                _incoming_item(
                    partner,
                    is_super_like=False,
                    is_matched=True,
                    already_liked_back=partner_id in my_likes,
                    created_at=match_dates.get(partner_id),
                )
            )

    results.sort(
        key=lambda item: (
            -int(item["is_super_like"]),
            -(item["created_at"].timestamp() if item["created_at"] else 0),
        )
    )
    if limit:
        results = results[:limit]
    return results


def count_incoming(profile: Profile) -> int:
    items = incoming(profile)
    if not items:
        return 0
    ids = [item["profile"].pk for item in items]
    return Profile.objects.filter(
        pk__in=ids, banned_at__isnull=True, suspended_at__isnull=True
    ).count()


def _is_unread_incoming(item: dict, seen_at) -> bool:
    if not seen_at:
        return True
    created = item.get("created_at")
    if not created:
        return False
    return created > seen_at


def count_unread_incoming(profile: Profile) -> int:
    seen_at = profile.likes_inbox_seen_at
    return sum(1 for item in incoming(profile) if _is_unread_incoming(item, seen_at))


def mark_inbox_seen(profile: Profile) -> None:
    from django.utils import timezone

    now = timezone.now()
    Profile.objects.filter(pk=profile.pk).update(likes_inbox_seen_at=now, updated_at=now)
    profile.likes_inbox_seen_at = now


def incoming_cards(profile: Profile, limit: int = INCOMING_PAGE_SIZE) -> list[dict]:
    """Likes reçus, format fiche pour la page Likes."""
    seen_at = profile.likes_inbox_seen_at
    cards = []
    for item in incoming(profile, limit=limit):
        other = item["profile"]
        created = item.get("created_at")
        when = ""
        if created:
            from django.utils import timezone as tz

            local = tz.localtime(created)
            when = local.strftime("%d/%m")
        cards.append(
            {
                "id": str(other.pk),
                "first_name": other.first_name or "Membre",
                "age": None if other.hide_age else other.age,
                "city": other.city or "",
                "photo_url": other.primary_photo or "",
                "profile_url": f"/explorer/profil/{other.pk}/",
                "profession": (getattr(other, "profession", None) or "").strip(),
                "is_super_like": bool(item.get("is_super_like")),
                "is_matched": bool(item.get("is_matched")),
                "already_liked_back": bool(item.get("already_liked_back")),
                "message_url": f"/discussions/{other.pk}/",
                "is_online": bool(getattr(other, "is_online", False)),
                "is_new": _is_unread_incoming(item, seen_at),
                "when": when,
                "is_locked": False,
            }
        )
    return cards


def _lock_incoming_card(item: dict) -> dict:
    from core.controllers import quota_controller

    return {
        **item,
        "is_locked": True,
        "first_name": "Membre",
        "age": None,
        "city": "",
        "profession": "",
        "profile_url": quota_controller.upgrade_path(),
        "message_url": "",
        "already_liked_back": False,
        "is_matched": False,
        "is_online": False,
    }


def feed_context(profile: Profile, limit: int = INCOMING_PAGE_SIZE) -> dict:
    """Contexte partagé page Likes + fragment live."""
    from core.controllers import quota_controller

    likes_list = incoming_cards(profile, limit=limit)
    total = count_incoming(profile)
    locked_count = 0
    if quota_controller.is_freemium(profile):
        visible = quota_controller.likes_visible_limit()
        extra = likes_list[visible:]
        likes_list = likes_list[:visible] + [_lock_incoming_card(item) for item in extra]
        locked_count = max(0, total - visible)

    unlocked = [item for item in likes_list if not item.get("is_locked")]
    has_matches = Match.objects.filter(
        models_q_participant(profile), status=MatchStatus.ACTIVE
    ).exists()
    return {
        "likes": likes_list,
        "featured": None,
        "grid": likes_list,
        "pending_count": total,
        "has_matches": has_matches,
        "has_more": total > len(likes_list) and not quota_controller.is_freemium(profile),
        "locked_count": locked_count,
        "likes_restricted": quota_controller.is_freemium(profile),
    }


def has_liked(profile: Profile, other_id) -> bool:
    return Swipe.objects.filter(swiper=profile, swiped_id=other_id, is_like=True).exists()


def has_super_liked(profile: Profile, other_id) -> bool:
    return Swipe.objects.filter(swiper=profile, swiped_id=other_id, is_super_like=True).exists()


def _serialize_outgoing(swipe: Swipe, matched_ids: set) -> dict:
    other = swipe.swiped
    location_parts = [p for p in (other.city, other.country) if p]
    return {
        "id": str(other.pk),
        "first_name": other.first_name or "Membre",
        "age": None if other.hide_age else other.age,
        "city": other.city or "",
        "location": ", ".join(location_parts) if location_parts else "TimaLove",
        "photo_url": other.primary_photo,
        "is_verified": bool(other.is_verified),
        "is_super_like": bool(swipe.is_super_like),
        "matched": other.id in matched_ids,
        "liked": bool(swipe.is_like),
        "liked_at": swipe.created_at,
        "profile_url": f"/explorer/profil/{other.pk}/",
        "message_url": f"/discussions/{other.pk}/" if other.id in matched_ids else "",
    }


PAGE_SIZE = 20


def outgoing(profile: Profile, limit: int = PAGE_SIZE, offset: int = 0) -> dict:
    """Profils likés ou super likés, paginés du plus récent au plus ancien."""
    limit = max(1, min(int(limit or PAGE_SIZE), 50))
    offset = max(0, int(offset or 0))
    swipes = list(
        Swipe.objects.filter(swiper=profile)
        .filter(LIKE_Q)
        .select_related("swiped")
        .order_by("-created_at")[offset : offset + limit + 1]
    )
    has_more = len(swipes) > limit
    swipes = swipes[:limit]
    matched_ids = _matched_ids(profile)
    return {
        "items": [_serialize_outgoing(swipe, matched_ids) for swipe in swipes],
        "has_more": has_more,
        "next_offset": offset + len(swipes),
    }


def outgoing_item(profile: Profile, other_id) -> dict | None:
    swipe = (
        Swipe.objects.filter(swiper=profile, swiped_id=other_id)
        .filter(LIKE_Q)
        .select_related("swiped")
        .first()
    )
    if not swipe:
        return None
    return _serialize_outgoing(swipe, _matched_ids(profile))


def search_outgoing(profile: Profile, query: str, limit: int = 8) -> list[dict]:
    """Recherche live parmi les profils likés et super likés."""
    q = " ".join((query or "").split())
    if len(q) < 2:
        return []

    swipes = (
        Swipe.objects.filter(swiper=profile)
        .filter(LIKE_Q)
        .filter(
            Q(swiped__first_name__icontains=q)
            | Q(swiped__city__icontains=q)
            | Q(swiped__profession__icontains=q)
        )
        .select_related("swiped")
        .annotate(
            rank=Case(
                When(swiped__first_name__istartswith=q, then=Value(0)),
                When(swiped__first_name__icontains=q, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by("rank", "-created_at")[: max(1, min(limit, 12))]
    )

    results = []
    for swipe in swipes:
        other = swipe.swiped
        name = (other.first_name or "Membre").strip() or "Membre"
        results.append(
            {
                "id": str(other.pk),
                "first_name": name,
                "age": None if other.hide_age else other.age,
                "city": other.city or "",
                "photo_url": other.primary_photo or "",
                "profile_url": f"/explorer/profil/{other.pk}/",
                "initial": name[:1].upper(),
                "liked": bool(swipe.is_like),
                "is_super_like": bool(swipe.is_super_like),
            }
        )
    return results


def toggle_outgoing(profile: Profile, other_id) -> dict:
    """Inverse le like envoyé sans retirer un super like existant."""
    from core.controllers import swipe_controller

    swipe = Swipe.objects.filter(swiper=profile, swiped_id=other_id).first()
    supered = bool(swipe and swipe.is_super_like)
    liked = bool(swipe and swipe.is_like)
    swipe_controller.set_flags(profile, other_id, is_like=not liked, is_super_like=supered)
    now_liked = not liked
    return {
        "liked": now_liked,
        "is_super_like": supered,
        "visible": now_liked or supered,
    }


def toggle_outgoing_super(profile: Profile, other_id) -> dict:
    """Inverse le super like sans retirer un like existant."""
    from core.controllers import swipe_controller

    swipe = Swipe.objects.filter(swiper=profile, swiped_id=other_id).first()
    liked = bool(swipe and swipe.is_like)
    supered = bool(swipe and swipe.is_super_like)
    swipe_controller.set_flags(profile, other_id, is_like=liked, is_super_like=not supered)
    now_super = not supered
    return {
        "liked": liked,
        "is_super_like": now_super,
        "visible": liked or now_super,
    }


def preview_incoming(limit: int = 8) -> list[dict]:
    """Aperçu visiteur / design : personnes qui auraient liké, avant la logique live."""
    from core.controllers import explore_controller

    cards, _ = explore_controller.public_feed(offset=0, limit=limit, seed="likes-demo")
    extras = [
        {"profession": "Architecte", "is_super_like": True, "is_online": True, "is_new": True, "when": "Il y a 12 min"},
        {"profession": "Enseignante", "is_super_like": False, "is_online": True, "is_new": True, "when": "Il y a 40 min"},
        {"profession": "Entrepreneur", "is_super_like": True, "is_online": False, "is_new": True, "when": "Aujourd’hui"},
        {"profession": "Infirmière", "is_super_like": False, "is_online": True, "is_new": False, "when": "Hier"},
        {"profession": "Juriste", "is_super_like": False, "is_online": False, "is_new": False, "when": "Hier"},
        {"profession": "Photographe", "is_super_like": True, "is_online": True, "is_new": False, "when": "Cette semaine"},
        {"profession": "Comptable", "is_super_like": False, "is_online": False, "is_new": False, "when": "Cette semaine"},
        {"profession": "Médecin", "is_super_like": False, "is_online": True, "is_new": False, "when": "Cette semaine"},
    ]
    items = []
    for index, card in enumerate(cards):
        extra = extras[index] if index < len(extras) else extras[-1]
        items.append(
            {
                "id": card["id"],
                "first_name": card["first_name"],
                "age": card.get("age"),
                "city": card.get("city") or card.get("location") or "",
                "photo_url": card.get("photo_url") or "",
                "profile_url": card.get("profile_url") or f"/explorer/profil/{card['id']}/",
                "profession": extra["profession"],
                "is_super_like": extra["is_super_like"],
                "is_online": extra["is_online"],
                "is_new": extra["is_new"],
                "when": extra["when"],
            }
        )
    if items:
        return items
    names = ["Awa", "Kofi", "Maguette", "Ibrahima", "Sokhna", "Mamadou", "Fatou", "Omar"]
    return [
        {
            "id": f"demo-{index}",
            "first_name": names[index],
            "age": 26 + index,
            "city": "Dakar",
            "photo_url": "",
            "profile_url": "#",
            "profession": extras[index]["profession"],
            "is_super_like": extras[index]["is_super_like"],
            "is_online": extras[index]["is_online"],
            "is_new": extras[index]["is_new"],
            "when": extras[index]["when"],
        }
        for index in range(len(names))
    ]
    """Aperçu visiteur : profils publics pour le design Historique."""
    from core.controllers import explore_controller

    cards, _ = explore_controller.public_feed(offset=0, limit=limit, seed="historique-demo")
    items = []
    for index, card in enumerate(cards):
        items.append(
            {
                "id": card["id"],
                "first_name": card["first_name"],
                "age": card.get("age"),
                "photo_url": card.get("photo_url"),
                "profile_url": card["profile_url"],
                "liked": index % 3 != 1,
                "matched": False,
                "is_super_like": index % 4 == 0 or index % 5 == 0,
            }
        )
    return items
