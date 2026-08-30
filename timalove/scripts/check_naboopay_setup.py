#!/usr/bin/env python
"""Met a jour check_naboopay_setup avec URLs prod + ngrok."""

from __future__ import annotations

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from django.urls import reverse

from core.controllers import naboopay_controller, payment_controller


def webhook(base: str) -> str:
    return f"{base.rstrip('/')}{reverse('api:naboo_webhook')}"


def main() -> int:
    print("=== NabooPay — diagnostic TimaLove ===\n")
    provider = payment_controller._provider()
    print(f"Prestataire actif : {provider or '(simulation)'}")

    if not naboopay_controller.is_configured():
        print("ERREUR NABOOPAY_API_KEY manquante dans .env")
        return 1

    key = settings.NABOOPAY_API_KEY
    print(f"OK Cle API : {key[:18]}...{key[-6:]}")

    prod = (getattr(settings, "NABOOPAY_PRODUCTION_SITE_URL", "") or "").rstrip("/")
    ngrok = (getattr(settings, "NGROK_URL", "") or "").rstrip("/")
    public = (getattr(settings, "NABOOPAY_PUBLIC_SITE_URL", "") or "").rstrip("/")
    site = (payment_controller._site_url() or "").rstrip("/")

    print(f"\n--- Production (dashboard NabooPay) ---")
    print(f"  Webhook     : {webhook(prod)}")
    print(f"  Retour OK   : {prod}{reverse('api:payments_confirm')}?order_id=ORDER_ID")

    if ngrok:
        print(f"\n--- Ngrok (test local actif) ---")
        print(f"  Webhook     : {webhook(ngrok)}")
    else:
        print(f"\n--- Ngrok (non demarre) ---")
        print("  Lancez : .\\scripts\\start_ngrok_webhook.ps1")

    print(f"\n--- Checkout actif ---")
    print(f"  Base URL    : {site}")
    print(f"  Webhook     : {webhook(site)}")
    print(f"  Methodes    : {', '.join(naboopay_controller.methods())}")

    if not naboopay_controller.webhook_secret_configured():
        print("\n! NABOOPAY_WEBHOOK_SECRET absent — dev seulement")
    else:
        print("\nOK Secret webhook configure")

    print("\nDetail : python scripts/naboopay_webhook_setup.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
