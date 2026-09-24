"""Feed public style explorer (scroll vertical type TikTok)."""

from __future__ import annotations

import random
import secrets
import uuid

from django.db.models import Case, IntegerField, Q, Value, When
from django.http import Http404

from core.controllers import matching_controller, swipe_controller
from core.data.onboarding import INTERESTS, TRAITS, looking_for_free_text, looking_for_ids, looking_for_labels, life_value_labels
from core.models import Profile, Swipe
from core.models.choices import RegistrationStatus, UserRole

PAGE_SIZE = 20
PHOTOS_PER_CARD = 8

SESSION_QUEUE_KEY = "explorer_queue"
SESSION_SERVED_KEY = "explorer_served"
SESSION_RECENT_SHOWN_KEY = "explorer_recent_shown"
SESSION_SEED_KEY = "explorer_feed_seed"
SESSION_ELIGIBILITY_KEY = "explorer_eligibility"
SESSION_DEPLOY_REV_KEY = "explorer_deploy_rev"

RECENT_SHOWN_CAP = 50
RECENT_RECYCLE_BLOCK = 30


def _chip_catalog(catalog: list[dict], selected_raw) -> list[dict]:
    selected = {str(item).strip().lower() for item in (selected_raw or []) if str(item).strip()}
    return [
        {
            "id": item["id"],
            "label": item["label"],
            "icon": item.get("icon", ""),
            "selected": item["id"].lower() in selected or item["label"].lower() in selected,
        }
        for item in catalog
    ]


def _public_place(value: str | None) -> str:
    text = (value or "").strip()
    if not text or "@" in text:
        return ""
    return text


def _location_label(profile: Profile) -> str:
    parts = [p for p in (_public_place(profile.commune), _public_place(profile.city), _public_place(profile.country)) if p]
    return ", ".join(parts) if parts else "TimaLove"


def collect_photos(profile: Profile, limit: int = PHOTOS_PER_CARD) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for raw in (profile.photo_url, profile.photo_url_2, profile.photo_url_3):
        url = (raw or "").strip()
        if url and url not in seen:
            urls.append(url)
            seen.add(url)
    gallery = getattr(profile, "_prefetched_objects_cache", {}).get("gallery_photos")
    extras = gallery if gallery is not None else profile.gallery_photos.all()
    for item in extras:
        if len(urls) >= limit:
            break
        url = (item.photo_url or "").strip()
        if url and url not in seen:
            urls.append(url)
            seen.add(url)
    return urls[:limit]


def compatibility_score(profile: Profile, viewer: Profile | None = None) -> int:
    """Score affiché — compatibilité réelle si viewer connecté."""
    return matching_controller.compatibility_percent(viewer, profile)


def _eligible_queryset():
    return (
        Profile.objects.filter(
            registration_status=RegistrationStatus.APPROVED,
            is_hidden=False,
            is_shadowbanned=False,
            role=UserRole.MEMBER,
        )
        .exclude(banned_at__isnull=False)
        .exclude(photo_url__isnull=True)
        .exclude(photo_url="")
    )


def _search_queryset():
    """Profils trouvables par nom — sans exiger de photo (inscription récente)."""
    return (
        Profile.objects.filter(
            registration_status=RegistrationStatus.APPROVED,
            is_hidden=False,
            is_shadowbanned=False,
            role=UserRole.MEMBER,
        )
        .exclude(banned_at__isnull=False)
        .exclude(suspended_at__isnull=False)
    )


def serialize_card(
    profile: Profile,
    *,
    liked: bool = False,
    super_liked: bool = False,
    viewer=None,
) -> dict:
    from core.controllers import subscription_controller

    photos = collect_photos(profile)
    city = _public_place(profile.city)
    country = _public_place(profile.country)
    location_parts = [p for p in (city, country) if p]
    return {
        "id": str(profile.pk),
        "first_name": profile.first_name or "Membre",
        "age": None if profile.hide_age else profile.age,
        "city": city,
        "country": country,
        "location": ", ".join(location_parts) if location_parts else "TimaLove",
        "photo_url": photos[0] if photos else profile.primary_photo,
        "photos": photos,
        "is_verified": bool(profile.is_verified),
        "bio": (profile.bio or "")[:140],
        "profession": (profile.profession or "").strip(),
        "relationship_intent": profile.get_relationship_intent_display() if profile.relationship_intent else "",
        "compatibility": compatibility_score(profile, viewer),
        "profile_url": f"/explorer/profil/{profile.pk}/",
        "liked": liked,
        "super_liked": super_liked,
        "subscription_badge": subscription_controller.badge_for(profile),
        "is_online": _is_present(profile),
    }


def _eligible_ids(viewer=None) -> list:
    """IDs éligibles au feed explorer : genre opposé, hors bannis / déjà croisés."""
    qs = _eligible_queryset()
    if viewer is not None:
        qs = qs.exclude(pk=viewer.pk)
        from core.controllers.profile_controller import apply_discover_filters, apply_opposite_gender_filter

        qs = apply_opposite_gender_filter(qs, viewer)
        qs = apply_discover_filters(qs, viewer)
        qs = swipe_controller.apply_feed_exclusions(qs, viewer)
    return list(qs.values_list("pk", flat=True))


def _cards_for_ids(page_ids: list, viewer=None) -> list[dict]:
    if not page_ids:
        return []
    by_id = Profile.objects.prefetch_related("gallery_photos").in_bulk(page_ids)
    profiles = [by_id[i] for i in page_ids if i in by_id]
    liked_ids: set = set()
    super_ids: set = set()
    if viewer is not None and page_ids:
        for swiped_id, is_like, is_super in Swipe.objects.filter(
            swiper=viewer, swiped_id__in=page_ids
        ).filter(Q(is_like=True) | Q(is_super_like=True)).values_list(
            "swiped_id", "is_like", "is_super_like"
        ):
            if is_like:
                liked_ids.add(swiped_id)
            if is_super:
                super_ids.add(swiped_id)
    return [
        serialize_card(p, liked=p.pk in liked_ids, super_liked=p.pk in super_ids, viewer=viewer)
        for p in profiles
    ]


def reset_feed_session(session) -> None:
    if session is None:
        return
    session.pop(SESSION_QUEUE_KEY, None)
    session.pop(SESSION_SERVED_KEY, None)
    session.pop(SESSION_RECENT_SHOWN_KEY, None)
    session.pop(SESSION_SEED_KEY, None)
    reset_curated_session(session)


def mark_profiles_seen_in_feed(session, profile_ids) -> None:
    """Profils déjà montrés ou swipés — ne pas les reproposer tout de suite au retour sur Parcours."""
    if session is None:
        return
    served = {str(x) for x in session.get(SESSION_SERVED_KEY, []) if str(x).strip()}
    recent = [str(x) for x in session.get(SESSION_RECENT_SHOWN_KEY, []) if str(x).strip()]
    for raw in profile_ids or []:
        key = str(raw).strip()
        if not key:
            continue
        served.add(key)
        recent.append(key)
    session[SESSION_SERVED_KEY] = list(served)
    session[SESSION_RECENT_SHOWN_KEY] = recent[-RECENT_SHOWN_CAP:]
    session.modified = True


def _remaining_for_feed(eligible: list, session) -> list:
    """Exclut les profils déjà servis ; recycle le pool en gardant un cooldown anti-répétition."""
    served = {str(pk) for pk in session.get(SESSION_SERVED_KEY, [])}
    recent = [str(x) for x in session.get(SESSION_RECENT_SHOWN_KEY, [])]
    recent_block = set(recent[-RECENT_RECYCLE_BLOCK:])

    remaining = [pk for pk in eligible if str(pk) not in served]
    if remaining:
        return remaining

    remaining = [pk for pk in eligible if str(pk) not in recent_block]
    if remaining:
        session[SESSION_SERVED_KEY] = []
        session.modified = True
        return remaining

    soft_block = set(recent[-10:])
    remaining = [pk for pk in eligible if str(pk) not in soft_block]
    if remaining:
        session[SESSION_SERVED_KEY] = []
        session.modified = True
        return remaining

    session[SESSION_SERVED_KEY] = []
    session.modified = True
    return list(eligible)


def sync_feed_session(session, viewer=None, *, deploy_revision: str = "") -> None:
    """
    Réinitialise la file explorer si le genre du membre ou la révision deploy a changé.
    Permet un effet immédiat après mise à jour profil ou déploiement VPS.
    """
    if session is None:
        return
    from core.controllers.profile_controller import feed_eligibility_key

    expected = feed_eligibility_key(viewer)
    stored = session.get(SESSION_ELIGIBILITY_KEY)
    stored_rev = str(session.get(SESSION_DEPLOY_REV_KEY) or "")
    rev = (deploy_revision or "").strip()
    needs_reset = stored != expected or (rev and stored_rev != rev)
    if not needs_reset:
        return
    reset_feed_session(session)
    session[SESSION_ELIGIBILITY_KEY] = expected
    if rev:
        session[SESSION_DEPLOY_REV_KEY] = rev
    session.modified = True


ORDER_WINDOW = 80


def _order_feed_ids(remaining: list, viewer=None, *, seed: str = "", served_count: int = 0) -> list:
    """Priorise les profils complets (>60 %) puis Premium/VIP, sans charger tout le catalogue."""
    import random

    from core.controllers import profile_controller, subscription_controller

    if not remaining:
        return []
    rng = random.Random(f"{seed}:order:{served_count}")
    pool = list(remaining)
    rng.shuffle(pool)
    window = pool[:ORDER_WINDOW]
    rest = pool[ORDER_WINDOW:]
    profiles = Profile.objects.in_bulk(window)
    scored: list[tuple[float, int, object]] = []
    for pk in window:
        profile = profiles.get(pk)
        if not profile:
            rest.append(pk)
            continue
        mult = subscription_controller.visibility_multiplier(profile)
        if profile.is_boosted:
            mult *= 2
        score = rng.random() * mult
        completion = profile_controller.completion_score(profile)
        scored.append((score, completion, pk))
    scored.sort(key=lambda row: (-(1 if row[1] > 60 else 0), -row[0]))
    return [pk for _, _, pk in scored] + rest


def public_feed(
    *,
    offset: int = 0,
    limit: int = PAGE_SIZE,
    seed: str | None = None,
    viewer=None,
    session=None,
    reset: bool = False,
) -> tuple[list[dict], bool]:
    """Retourne (cartes, has_more). Avec session : file persistante, sans offset cassé par les swipes."""
    limit = min(max(1, limit), 20)
    seed = seed or "timalove"

    if session is not None:
        from core.deploy_revision import get_deploy_revision

        sync_feed_session(session, viewer, deploy_revision=get_deploy_revision())
        if session.get(SESSION_SEED_KEY) != seed:
            session[SESSION_SEED_KEY] = seed
            session.modified = True

        eligible = _eligible_ids(viewer)
        remaining = _remaining_for_feed(eligible, session)
        if not remaining:
            session[SESSION_QUEUE_KEY] = []
            session.modified = True
            return [], False

        order_seed = secrets.token_hex(16)
        served_count = len(session.get(SESSION_SERVED_KEY, []) or [])
        ordered = _order_feed_ids(remaining, viewer, seed=order_seed, served_count=served_count)
        page_ids = ordered[:limit]
        mark_profiles_seen_in_feed(session, page_ids)
        session[SESSION_QUEUE_KEY] = []
        session.modified = True

        has_more = len(remaining) > len(page_ids)
        return _cards_for_ids(page_ids, viewer), has_more

    ids = _eligible_ids(viewer)
    rng = random.Random(seed)
    rng.shuffle(ids)
    offset = max(0, offset)
    chunk = ids[offset : offset + limit + 1]
    has_more = len(chunk) > limit
    page_ids = chunk[:limit]
    return _cards_for_ids(page_ids, viewer), has_more


def get_public_profile(profile_id, viewer=None) -> dict | None:
    """Détail public d'un profil visitable depuis l'explorer."""
    from core.controllers import subscription_controller

    try:
        uid = uuid.UUID(str(profile_id))
    except (TypeError, ValueError):
        return None

    profile = (
        _eligible_queryset()
        .prefetch_related("gallery_photos")
        .filter(pk=uid)
        .first()
    )
    if not profile:
        return None

    if viewer is not None:
        from core.controllers.profile_controller import can_view_profile_by_gender

        if not can_view_profile_by_gender(viewer, profile):
            return None

    photos = collect_photos(profile, limit=12)

    religion_label = profile.get_religion_display() if profile.religion else ""
    intent_label = profile.get_relationship_intent_display() if profile.relationship_intent else ""
    gender_label = profile.get_gender_display() if profile.gender else ""
    interest_map = {i["id"]: i["label"] for i in INTERESTS}
    trait_map = {t["id"]: t["label"] for t in TRAITS}

    return {
        "id": str(profile.pk),
        "first_name": profile.first_name or "Membre",
        "last_name": (profile.last_name or "").strip(),
        "full_name": profile.display_name,
        "age": None if profile.hide_age else profile.age,
        "city": _public_place(profile.city),
        "commune": _public_place(profile.commune),
        "country": _public_place(profile.country),
        "residence_country": profile.residence_country or "",
        "location": _location_label(profile),
        "photo_url": profile.primary_photo,
        "photos": photos or ([profile.primary_photo] if profile.primary_photo else []),
        "is_verified": bool(profile.is_verified),
        "compatibility": compatibility_score(profile, viewer),
        "bio": (profile.bio or "").strip(),
        "looking_for": (profile.looking_for or "").strip(),
        "looking_for_ids": looking_for_ids(profile.looking_for),
        "looking_for_labels": looking_for_labels(profile.looking_for),
        "looking_for_text": looking_for_free_text(profile.looking_for),
        "profession": (profile.profession or "").strip(),
        "religion": religion_label,
        "gender": profile.gender or "",
        "gender_label": gender_label,
        "relationship_intent": profile.relationship_intent or "",
        "relationship_intent_label": intent_label,
        "life_project": (profile.life_project or "").strip(),
        "is_online": _is_present(profile),
        "is_boosted": bool(profile.is_boosted),
        "member_since": profile.created_at.year if profile.created_at else None,
        "followers": int(profile.likes_received_count or 0),
        "following": int(profile.likes_given_count or 0),
        "favorites": int(profile.matches_count or 0),
        "interest_labels": [
            interest_map.get(i, i) for i in (profile.interests or [])
        ],
        "trait_labels": [
            trait_map.get(t, t) for t in (profile.personality_traits or [])
        ],
        "interest_chips": _chip_catalog(INTERESTS, profile.interests),
        "trait_chips": _chip_catalog(TRAITS, profile.personality_traits),
        "life_values": [str(v).strip() for v in (profile.life_values or []) if str(v).strip()],
        "life_value_labels": life_value_labels(profile.life_values),
        "subscription_badge": subscription_controller.badge_for(profile),
    }


def get_public_profile_or_404(profile_id, viewer=None) -> dict:
    data = get_public_profile(profile_id, viewer=viewer)
    if not data:
        raise Http404("Profil introuvable")
    return data


def search_profiles(query: str, *, viewer=None, limit: int = 8) -> list[dict]:
    """Recherche live : prénom, nom, ville, commune, profession — sans exclusions swipe."""
    q = " ".join((query or "").split())
    if len(q) < 2:
        return []

    qs = _search_queryset()
    if viewer is not None:
        qs = qs.exclude(pk=viewer.pk)
        from core.controllers.profile_controller import apply_opposite_gender_filter

        qs = apply_opposite_gender_filter(qs, viewer)

    text_q = (
        Q(first_name__icontains=q)
        | Q(last_name__icontains=q)
        | Q(city__icontains=q)
        | Q(commune__icontains=q)
        | Q(profession__icontains=q)
        | Q(country__icontains=q)
    )
    if " " in q:
        parts = [p for p in q.split() if len(p) >= 2]
        if len(parts) >= 2:
            text_q = text_q | Q(first_name__icontains=parts[0], last_name__icontains=parts[-1])
            text_q = text_q | Q(first_name__icontains=parts[-1], last_name__icontains=parts[0])
    for token in q.split():
        if len(token) >= 2:
            text_q = text_q | Q(first_name__icontains=token) | Q(last_name__icontains=token)

    qs = (
        qs.filter(text_q)
        .annotate(
            rank=Case(
                When(first_name__istartswith=q, then=Value(0)),
                When(last_name__istartswith=q, then=Value(1)),
                When(first_name__icontains=q, then=Value(2)),
                When(last_name__icontains=q, then=Value(3)),
                default=Value(4),
                output_field=IntegerField(),
            )
        )
        .order_by("rank", "first_name", "last_name")[: max(1, min(limit, 12))]
    )

    results = []
    for profile in qs:
        first = (profile.first_name or "Membre").strip() or "Membre"
        last = (profile.last_name or "").strip()
        display = f"{first} {last}".strip() if last else first
        photo = (profile.primary_photo or "").strip()
        results.append(
            {
                "id": str(profile.pk),
                "first_name": display,
                "age": None if profile.hide_age else profile.age,
                "photo_url": photo,
                "city": profile.city or "",
                "profile_url": f"/explorer/profil/{profile.pk}/",
                "initial": first[:1].upper(),
            }
        )
    return results


SESSION_CURATED_DATE_KEY = "curated_date"
SESSION_CURATED_IDS_KEY = "curated_ids"
SESSION_CURATED_TARGET_KEY = "curated_target"
SESSION_CURATED_SEED_KEY = "curated_seed"


def reset_curated_session(session) -> None:
    if session is None:
        return
    session.pop(SESSION_CURATED_DATE_KEY, None)
    session.pop(SESSION_CURATED_IDS_KEY, None)
    session.pop(SESSION_CURATED_TARGET_KEY, None)
    session.pop(SESSION_CURATED_SEED_KEY, None)
    session.modified = True


def curated_daily_feed(viewer, session, *, expand_by: int = 0) -> tuple[list[dict], dict]:
    """
    Sélection Parcours curated — ordre aléatoire à chaque visite de la page.
    « Voir plus » conserve la sélection en cours et ajoute des profils sans réordonner.
    """
    from django.utils import timezone

    from core.controllers import app_config_controller

    initial_limit = app_config_controller.curated_daily_limit()
    daily_max = app_config_controller.curated_daily_max()
    today = timezone.localdate().isoformat()
    fresh_visit = expand_by == 0

    if session is not None:
        stored_date = session.get(SESSION_CURATED_DATE_KEY)
        stored_ids = session.get(SESSION_CURATED_IDS_KEY) or []
        if stored_date != today:
            stored_ids = []
            session[SESSION_CURATED_DATE_KEY] = today
            session[SESSION_CURATED_IDS_KEY] = []
            session[SESSION_CURATED_TARGET_KEY] = initial_limit
            session.pop(SESSION_CURATED_SEED_KEY, None)
            session.modified = True
        target = int(session.get(SESSION_CURATED_TARGET_KEY) or initial_limit)
        if expand_by > 0:
            target = min(target + expand_by, daily_max)
            session[SESSION_CURATED_TARGET_KEY] = target
            session.modified = True
        limit = min(max(target, initial_limit), daily_max)
        if fresh_visit or not session.get(SESSION_CURATED_SEED_KEY):
            session[SESSION_CURATED_SEED_KEY] = secrets.token_hex(16)
            session.modified = True
        seed = session[SESSION_CURATED_SEED_KEY]
    else:
        stored_ids = []
        limit = initial_limit
        seed = secrets.token_hex(16)

    eligible = _eligible_ids(viewer)
    eligible_set = {str(pk) for pk in eligible}

    curated_ids: list = []
    for raw in stored_ids:
        try:
            pk = uuid.UUID(str(raw))
        except (TypeError, ValueError):
            continue
        if str(pk) in eligible_set:
            curated_ids.append(pk)

    if len(curated_ids) < limit:
        already = {str(pk) for pk in curated_ids}
        remaining = [pk for pk in eligible if str(pk) not in already]
        if remaining:
            ordered = _order_feed_ids(remaining, viewer, seed=seed, served_count=len(curated_ids))
            need = limit - len(curated_ids)
            curated_ids.extend(ordered[:need])

    if fresh_visit:
        if len(curated_ids) > 1:
            shuffle_rng = random.Random(secrets.token_hex(16))
            shuffle_rng.shuffle(curated_ids)
        if session is not None:
            session[SESSION_CURATED_DATE_KEY] = today
            session[SESSION_CURATED_TARGET_KEY] = target
            session[SESSION_CURATED_IDS_KEY] = [str(pk) for pk in curated_ids]
            session.modified = True
    elif session is not None and len(curated_ids) > len(stored_ids):
        session[SESSION_CURATED_DATE_KEY] = today
        session[SESSION_CURATED_IDS_KEY] = [str(pk) for pk in curated_ids]
        session.modified = True

    cards = _cards_for_ids(curated_ids, viewer)
    eligible_total = len(eligible)
    meta = {
        "date_label": today,
        "limit": limit,
        "count": len(cards),
        "remaining": max(0, limit - len(cards)),
        "has_more": len(curated_ids) < eligible_total and len(curated_ids) < daily_max,
        "eligible_total": eligible_total,
    }
    return cards, meta


def consume_curated_profile(viewer, session, profile_id) -> tuple[list[dict], dict]:
    """Retire un profil liké de la sélection et le remplace par un nouveau si possible."""
    from core.controllers import app_config_controller

    consumed = str(profile_id or "").strip()
    stored = []
    if session is not None:
        stored = [str(raw) for raw in (session.get(SESSION_CURATED_IDS_KEY) or []) if str(raw).strip()]
    kept = [pk for pk in stored if pk != consumed]
    daily_max = app_config_controller.curated_daily_max()
    eligible = _eligible_ids(viewer)
    already = set(kept)
    already.add(consumed)
    remaining = [pk for pk in eligible if str(pk) not in already]

    replacement_ids: list = []
    if remaining and len(kept) < daily_max:
        pick = remaining[random.randrange(len(remaining))]
        replacement_ids.append(pick)
        kept.append(str(pick))

    if session is not None:
        session[SESSION_CURATED_IDS_KEY] = kept
        session[SESSION_CURATED_TARGET_KEY] = max(
            int(session.get(SESSION_CURATED_TARGET_KEY) or len(kept)),
            len(kept),
        )
        session.modified = True

    cards = _cards_for_ids(replacement_ids, viewer)
    eligible_total = len(eligible)
    meta = {
        "count": len(kept),
        "has_more": len(kept) < eligible_total and len(kept) < daily_max,
        "eligible_total": eligible_total,
        "replaced": bool(cards),
    }
    return cards, meta


def _is_present(profile: Profile) -> bool:
    from core.controllers import presence_controller

    return presence_controller.is_present(profile)


def online_status_for_ids(profile_ids: list) -> dict[str, bool]:
    """Statut en ligne réel (socket ouvert ou activité très récente)."""
    from core.controllers import presence_controller

    return presence_controller.status_for_ids(profile_ids)
