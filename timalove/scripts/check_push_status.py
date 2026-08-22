#!/usr/bin/env python
"""Vérifie l'état des notifications push pour les comptes test."""

from __future__ import annotations

import os
import sys

import django

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model

from core.controllers import push_controller, profile_controller

TEST_EMAILS = ("teste1@gmail.com", "teste2@gmail.com")


def main() -> None:
    User = get_user_model()
    print("=== État notifications TimaLove ===\n")
    global_status = push_controller.public_config()
    print(f"FCM serveur activé : {global_status.get('enabled')}")
    print(f"Projet Firebase    : {global_status.get('firebase', {}).get('projectId')}\n")

    for email in TEST_EMAILS:
        user = User.objects.filter(email__iexact=email).select_related("profile").first()
        if not user or not getattr(user, "profile", None):
            print(f"{email} — compte introuvable")
            continue
        profile = user.profile
        status = push_controller.status_for(profile)
        prefs = status["preferences"]
        print(f"{email} ({profile.first_name})")
        print(f"  push activé profil : {status['push_enabled']}")
        print(f"  appareils FCM      : {status['devices_count']}")
        print(
            "  préférences        : "
            f"likes={prefs.get('likes')} super={prefs.get('super_likes')} "
            f"matchs={prefs.get('matches')} messages={prefs.get('messages')} "
            f"statut={prefs.get('status')}"
        )
        for device in status["devices"]:
            print(f"  · {device['platform']} — dernier usage {device['last_used_at']}")
        print()


if __name__ == "__main__":
    main()
