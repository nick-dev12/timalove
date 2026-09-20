#!/usr/bin/env python
"""Tests E2E Lot B+C sur le VPS (Django test client)."""
import os
import sys

ROOT = os.environ.get("TIMALOVE_ROOT", "/home/jomas/timalove/timalove")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.contrib.auth import authenticate
from django.test import Client

from core.controllers import app_config_controller, message_controller
from core.models import Profile

EMAIL = (sys.argv[1] if len(sys.argv) > 1 else "test.lotc@timalove.local").strip().lower()
PASSWORD = sys.argv[2] if len(sys.argv) > 2 else "AppleReview2026!"

client = Client(HTTP_HOST="mytimalove.com", secure=True)
checks: list[tuple[str, bool, str]] = []


def ok(name: str, cond: bool, detail: str = "") -> None:
    checks.append((name, bool(cond), detail))
    status = "OK" if cond else "FAIL"
    suffix = f" | {detail}" if detail else ""
    print(f"{status} | {name}{suffix}")


for path in ["/connexion/", "/explorer/", "/coaching/", "/politique-de-confidentialite/"]:
    response = client.get(path, follow=True)
    ok(f"GET {path}", response.status_code == 200, str(response.status_code))

user = authenticate(username=EMAIL, password=PASSWORD)
ok("auth", user is not None, EMAIL)
if not user:
    sys.exit(2)

client.force_login(user)

response = client.get("/explorer/", follow=True)
content = response.content
ok("explorer 200", response.status_code == 200)
ok("curated list", b"curated-list" in content)
ok("no pass swipe", b'data-swipe="pass"' not in content)
ok("objectif banner", b"matrimonial-objective" in content)

response = client.get("/likes/", follow=True)
ok("likes page", response.status_code == 200, str(response.status_code))
ok("likes sections", b"data-likes-section" in response.content)

response = client.get("/historique/", follow=True)
final_path = getattr(response, "request", {}).get("PATH_INFO", "")
ok("historique to likes", "/likes" in final_path, final_path)

response = client.get("/likes/?tab=sent", follow=True)
ok(
    "likes sent tab",
    response.status_code == 200 and b'data-likes-panel="sent"' in response.content,
    str(response.status_code),
)

flags = app_config_controller.feature_flags()
ok("search off", flags["explorer_search_enabled"] is False)
ok("curated on", flags["explorer_curated_mode"] is True)
ok("guided on", flags["guided_messages_enabled"] is True)

profile = Profile.objects.get(email=EMAIL)
fatou = Profile.objects.filter(email="fatou.demo@timalove.local").first()
if fatou:
    match = message_controller.get_active_match(profile, fatou.id)
    prompts = message_controller.guided_intro_prompts(match) if match else ()
    ok("guided prompts", len(prompts) == 3, str(len(prompts)))

failed = [item for item in checks if not item[1]]
print("---")
print(f"Total: {len(checks)}, Failed: {len(failed)}")
sys.exit(1 if failed else 0)
