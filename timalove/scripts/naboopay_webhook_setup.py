#!/usr/bin/env python
"""Affiche les URLs webhook NabooPay (production + ngrok) pour le dashboard."""

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


def webhook_url(base: str) -> str:
    return f"{base.rstrip('/')}{reverse('api:naboo_webhook')}"


def confirm_url(base: str) -> str:
    return f"{base.rstrip('/')}{reverse('api:payments_confirm')}?order_id=ORDER_ID"


def main() -> int:
    prod = (getattr(settings, "NABOOPAY_PRODUCTION_SITE_URL", "") or "").strip().rstrip("/")
    ngrok = (getattr(settings, "NGROK_URL", "") or "").strip().rstrip("/")
    public = (getattr(settings, "NABOOPAY_PUBLIC_SITE_URL", "") or "").strip().rstrip("/")
    local = (settings.SITE_URL or "").rstrip("/")

    print("=== NabooPay — URLs webhook TimaLove ===\n")

    print("PRODUCTION (a enregistrer dans platform.naboopay.com)")
    print("  Site        :", prod or "(NABOOPAY_PRODUCTION_SITE_URL manquant)")
    if prod:
        print("  Webhook     :", webhook_url(prod))
        print("  Retour OK   :", confirm_url(prod))
    print("  Tache       : payment_status")
    print()

    if ngrok or public:
        base = ngrok or public
        label = "NGROK (tests locaux)" if ngrok else "PUBLIC (dev)"
        print(f"{label} — tunnel actif")
        print("  Webhook     :", webhook_url(base))
        print("  Retour OK   :", confirm_url(base))
        print("  Copiez l'URL webhook dans NabooPay le temps du test local.")
        print()

    print("LOCAL (127.0.0.1 — NabooPay ne peut pas appeler directement)")
    print("  Webhook     :", webhook_url(local))
    print("  Demarrer ngrok : .\\scripts\\start_ngrok_webhook.ps1")
    print()

    print("Dashboard : https://platform.naboopay.com/ > Parametres > Integrations")
    print("  1. Modifier le webhook Supabase existant OU en creer un second pour ngrok")
    print("  2. Coller l'URL webhook production ci-dessus")
    print("  3. Copier la cle secrete dans NABOOPAY_WEBHOOK_SECRET (.env)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
