"""Présentation vocale de profil (max 30 secondes)."""

from __future__ import annotations

from core.controllers import chat_media_controller as media
from core.controllers.profile_controller import _voice_intro_public_payload
from core.models import Profile

VOICE_INTRO_MAX_SECONDS = 30


def public_payload(profile: Profile | None) -> dict:
    return _voice_intro_public_payload(profile)


def save_for(profile: Profile, upload, duration) -> dict:
    try:
        seconds = int(duration or 0)
    except (TypeError, ValueError):
        seconds = 0
    if seconds > VOICE_INTRO_MAX_SECONDS:
        raise ValueError("La présentation vocale dure 30 secondes maximum.")
    if seconds < 1:
        seconds = 1
    url = media.store_voice_intro(profile.id, upload)
    previous = (profile.voice_intro_url or "").strip()
    profile.voice_intro_url = url
    profile.voice_intro_duration_seconds = seconds
    profile.save(update_fields=["voice_intro_url", "voice_intro_duration_seconds", "updated_at"])
    if previous and previous != url:
        media.delete_media_file(previous)
    return public_payload(profile)


def delete_for(profile: Profile) -> dict:
    previous = (profile.voice_intro_url or "").strip()
    profile.voice_intro_url = None
    profile.voice_intro_duration_seconds = None
    profile.save(update_fields=["voice_intro_url", "voice_intro_duration_seconds", "updated_at"])
    if previous:
        media.delete_media_file(previous)
    return public_payload(profile)
