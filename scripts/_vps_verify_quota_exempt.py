#!/usr/bin/env python
"""Verifie qu'un compte est exempt de tous les quotas freemium."""
import os
import sys

ROOT = os.environ.get("TIMALOVE_ROOT", "/home/jomas/timalove/timalove")
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings

from core.controllers import discover_controller, quota_controller
from core.models import Profile

EMAIL = (sys.argv[1] if len(sys.argv) > 1 else "gooteste@gmail.com").strip().lower()

print("QUOTA_EXEMPT_EMAILS", getattr(settings, "QUOTA_EXEMPT_EMAILS", []))

profile = (
    Profile.objects.filter(email__iexact=EMAIL).select_related("user").first()
    or Profile.objects.filter(user__email__iexact=EMAIL).select_related("user").first()
)

if not profile:
    print("NOT_FOUND", EMAIL)
    sys.exit(1)

print("FOUND", profile.first_name, profile.email or profile.user.email, profile.gender)
print("is_quota_exempt", quota_controller.is_quota_exempt(profile))
print("is_freemium", quota_controller.is_freemium(profile))
print("is_male_freemium", quota_controller.is_male_freemium(profile))
print("messages_remaining", quota_controller.messages_remaining(profile))
print("history_limit_for", quota_controller.history_limit_for(profile))
print("likes_visible_cap", quota_controller.likes_visible_cap(profile))
print("should_blur_photos", discover_controller.should_blur_photos(profile))
ok, err, code = quota_controller.check_swipe(profile, profile.pk, "like")
print("check_swipe", ok, code, err[:60] if err else "")

if quota_controller.is_quota_exempt(profile) and not quota_controller.is_freemium(profile):
    print("STATUS OK — aucune restriction freemium")
    sys.exit(0)

print("STATUS FAIL — restrictions encore actives")
sys.exit(2)
