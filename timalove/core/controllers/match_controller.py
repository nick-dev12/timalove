"""Matches."""

from __future__ import annotations

from django.utils import timezone

from core.controllers.swipe_controller import models_q_participant
from core.models import Match, Profile
from core.models.choices import MatchStatus


def list_for(profile: Profile) -> list[dict]:
    matches = (
        Match.objects.filter(models_q_participant(profile), status=MatchStatus.ACTIVE)
        .select_related("user_1", "user_2")
        .order_by("-updated_at")
    )
    return [
        {
            "match": m,
            "partner": m.partner_of(profile),
        }
        for m in matches
    ]


def unmatch(profile: Profile, partner_id) -> tuple[bool, str]:
    try:
        partner = Profile.objects.get(pk=partner_id)
    except Profile.DoesNotExist:
        return False, "Profil introuvable."
    m = (
        Match.objects.filter(models_q_participant(profile), models_q_participant(partner))
        .filter(status=MatchStatus.ACTIVE)
        .first()
    )
    if not m:
        return False, "Match introuvable."
    m.status = MatchStatus.UNMATCHED
    m.updated_at = timezone.now()
    m.save(update_fields=["status", "updated_at"])
    return True, "Match terminé."
