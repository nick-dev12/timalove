#!/usr/bin/env python
"""Teste l'envoi push FCM pour les comptes test — affiche les erreurs détaillées."""

from __future__ import annotations

import os
import sys

import django

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model

from core.controllers import notification_controller, push_controller
from core.models import PushDevice

TEST_EMAILS = ("teste1@gmail.com", "teste2@gmail.com")


def main() -> None:
    User = get_user_model()
    print("=== Test envoi push FCM ===\n")
    print(f"SITE_URL     : {settings.SITE_URL}")
    print(f"FCM_ENABLED  : {getattr(settings, 'FCM_ENABLED', False)}")
    print(f"Credentials  : {settings.FIREBASE_CREDENTIALS_PATH} (exists={settings.FIREBASE_CREDENTIALS_PATH.exists()})")
    print(f"Firebase app : {push_controller._get_firebase_app() is not None}\n")

    for email in TEST_EMAILS:
        user = User.objects.filter(email__iexact=email).select_related("profile").first()
        if not user or not getattr(user, "profile", None):
            print(f"{email} — compte introuvable\n")
            continue

        profile = user.profile
        devices = list(PushDevice.objects.filter(profile=profile))
        print(f"--- {email} ({profile.first_name}) ---")
        print(f"  Appareils : {len(devices)}")
        for d in devices:
            print(f"  · token={d.token[:24]}… platform={d.platform} last={d.last_used_at}")

        if not devices:
            print("  SKIP : aucun token FCM\n")
            continue

        try:
            result = notification_controller.send_test(profile)
            print(f"  Résultat  : {result}")
            if result.get("sent", 0) >= 1:
                print("  OK : push envoyée\n")
            else:
                print(f"  ERREUR : push non envoyée — {result.get('errors')}\n")
        except Exception as exc:
            print(f"  EXCEPTION : {type(exc).__name__}: {exc}\n")


if __name__ == "__main__":
    main()
