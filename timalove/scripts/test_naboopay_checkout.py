#!/usr/bin/env python
"""Test checkout NabooPay (dev)."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from django.urls import reverse

from core.controllers import naboopay_controller, payment_controller, site_settings_controller
from core.models import Profile

site_settings_controller.seed_defaults()
profile = Profile.objects.filter(email="teste1@gmail.com").first()
if not profile:
    print("Profil teste1@gmail.com introuvable")
    raise SystemExit(1)

site = (settings.SITE_URL or "").rstrip("/")
oid = "sub_debug123"
success = f"{site}{reverse('api:payments_confirm')}?order_id={oid}"
error = f"{success}&status=error"
print("SITE_URL:", site)
print("success_url:", success)
print("error_url:", error)

result = naboopay_controller.initialize(
    amount=2990,
    description="TimaLove — Premium 1 mois",
    success_url=success,
    error_url=error,
    profile=profile,
)
print("naboopay init:", {k: result.get(k) for k in ("ok", "error", "order_id", "checkout_url")})
if result.get("raw"):
    print("raw error:", result["raw"])

out = payment_controller.create_checkout(profile, "premium_1m")
print("checkout:", {k: out.get(k) for k in ("ok", "error", "order_id", "checkout_url", "simulated")})
