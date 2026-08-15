"""Likes entrants et historique des likes envoyés."""

from __future__ import annotations

from django.db.models import Case, IntegerField, Q, Value, When

from core.models import Match, Profile, Swipe
from core.models.choices import MatchStatus
from core.controllers.swipe_controller import models_q_participant

LIKE_Q = Q(is_like=True) | Q(is_super_like=True)


def incoming(profile: Profile) -> list[dict]:
    liked_me = (
        Swipe.objects.filter(swiped=profile)
        .filter(LIKE_Q)
        .select_related("swiper")
        .order_by("-created_at")
    )
    my_likes = set(
        Swipe.objects.filter(swiper=profile).filter(LIKE_Q).values_list("swiped_id", flat=True)
    )
    matched_ids = set()
    for m in Match.objects.filter(models_q_participant(profile), status=MatchStatus.ACTIVE):
        matched_ids.add(m.partner_of(profile).id)

    results = []
    for swipe in liked_me:
        if swipe.swiper_id in matched_ids:
            continue
        results.append(
            {
                "profile": swipe.swiper,
                "is_super_like": swipe.is_super_like,
                "already_liked_back": swipe.swiper_id in my_likes,
                "created_at": swipe.created_at,
            }
        )
    return results


def count_incoming(profile: Profile) -> int:
    return len(incoming(profile))


def incoming_cards(profile: Profile) -> list[dict]:
    """Likes reçus, format fiche pour la page Likes."""
    cards = []
    for item in incoming(profile):
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
                "is_online": bool(getattr(other, "is_online", False)),
                "is_new": True,
                "when": when,
            }
        )
    return cards


def _matched_ids(profile: Profile) -> set:
    ids: set = set()
    for match in Match.objects.filter(models_q_participant(profile), status=MatchStatus.ACTIVE):
        ids.add(match.partner_of(profile).id)
    return ids


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
