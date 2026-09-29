#!/usr/bin/env python
"""Vérifie que le navigateur web voit le deck swipe, l'app native la grille curated."""
import os
import sys

ROOT = os.environ.get("TIMALOVE_ROOT", "/home/jomas/timalove/timalove")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.chdir(ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.test import Client

from core.controllers import app_config_controller as cfg

EMAIL = "apple.review@timalove.local"
PASSWORD = "AppleReview2026!"


def fetch(ua: str) -> str:
    client = Client(HTTP_HOST="mytimalove.com", HTTP_USER_AGENT=ua, secure=True)
    ok = client.login(username=EMAIL, password=PASSWORD)
    if not ok:
        raise SystemExit(f"login failed for {EMAIL}")
    response = client.get("/explorer/", follow=True)
    return response.content.decode("utf-8", errors="ignore")


web = fetch("Mozilla/5.0 Chrome/120.0.0.0")
app = fetch("Mozilla/5.0 TimaLoveApp")

print("web_status_ok", "Sélection du jour" not in web and "explorer-page--curated" not in web)
print("web_has_swipe_class", "explorer-page" in web and "explorer-page--curated" not in web)
print("app_curated", "explorer-page--curated" in app or "Sélection du jour" in app)
print("cfg_curated", cfg.explorer_curated_mode_enabled())
print("cfg_native", cfg.explorer_curated_mode_active(user_agent="TimaLoveApp"))
print("cfg_chrome", cfg.explorer_curated_mode_active(user_agent="Chrome"))
