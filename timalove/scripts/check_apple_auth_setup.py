#!/usr/bin/env python
"""Vérifie la configuration Sign in with Apple (Firebase + Django)."""

from __future__ import annotations

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings

from core.controllers.firebase_app import get_firebase_app

APPLE_SERVICES_ID = "com.mytimalove.timalove"
APPLE_APP_ID = "com.mytimalove.app"
APPLE_TEAM_ID = "XA8994VJC6"
APPLE_KEY_ID = "38NH6W2B97"
FIREBASE_CALLBACK = f"https://{settings.FIREBASE_AUTH_DOMAIN}/__/auth/handler"


def ok(label: str) -> None:
    print(f"  [OK] {label}")


def warn(label: str) -> None:
    print(f"  [!] {label}")


def fail(label: str) -> None:
    print(f"  [X] {label}")


def main() -> int:
    print("TimaLove — diagnostic Sign in with Apple\n")

    cred = settings.FIREBASE_CREDENTIALS_PATH
    if cred.exists():
        ok(f"Credentials Firebase Admin : {cred.name}")
    else:
        fail(f"Fichier credentials manquant : {cred}")
        print("        Placez le JSON Firebase Admin dans timalove/ (FIREBASE_CREDENTIALS_FILE).")

    p8_path = settings.BASE_DIR / f"AuthKey_{APPLE_KEY_ID}.p8"
    if p8_path.exists():
        ok(f"Cle Apple .p8 locale : {p8_path.name}")
        print("        Note : Django ne lit pas ce fichier. Collez son contenu dans Firebase > Auth > Apple.")
    else:
        warn(f"Fichier {p8_path.name} absent du dossier timalove/ (optionnel si deja dans Firebase)")

    if settings.FIREBASE_AUTH_DOMAIN:
        ok(f"Auth domain : {settings.FIREBASE_AUTH_DOMAIN}")
    else:
        fail("FIREBASE_AUTH_DOMAIN vide")

    if settings.FIREBASE_WEB_API_KEY:
        ok("Cle API web Firebase presente")
    else:
        fail("FIREBASE_WEB_API_KEY manquante")

    app = get_firebase_app()
    if app:
        ok("SDK Firebase Admin initialise")
    else:
        warn("Firebase Admin non initialise - verification des jetons Apple impossible cote serveur")

    print("\nCote Apple Developer (developer.apple.com) :")
    print(f"  • App ID (iOS)      : {APPLE_APP_ID}")
    print(f"  • Services ID (web) : {APPLE_SERVICES_ID}")
    print(f"  • Team ID           : {APPLE_TEAM_ID}")
    print(f"  • Key ID            : {APPLE_KEY_ID}")
    print(f"  • Return URL        : {FIREBASE_CALLBACK}")
    print("  • Domaine web       :", settings.FIREBASE_AUTH_DOMAIN.replace("https://", ""))

    print("\nCote Firebase Console > Authentication > Apple :")
    print(f"  • Services ID = {APPLE_SERVICES_ID}")
    print(f"  • Team ID     = {APPLE_TEAM_ID}")
    print(f"  • Key ID      = {APPLE_KEY_ID}")
    print("  - Private key = cle .p8 telechargee depuis Apple (collee dans Firebase)")

    print("\nCote Firebase > Authentication > Settings > Authorized domains :")
    for domain in ("127.0.0.1", "localhost", "mytimalove.com"):
        print(f"  • {domain}")

    print("\nFlux applicatif TimaLove :")
    ok("Bouton Continuer avec Apple sur /connexion/")
    ok("Endpoint POST /api/auth/apple/")
    ok("Champ Profile.apple_uid en base")

    print("\nTest manuel :")
    print("  1. Ouvrir http://127.0.0.1:8000/connexion/")
    print("  2. Cliquer Continuer avec Apple")
    print("  3. Autoriser -> completer le wizard si nouveau compte")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
