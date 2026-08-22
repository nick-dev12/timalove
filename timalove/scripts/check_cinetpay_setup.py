#!/usr/bin/env python
"""Vérifie que CinetPay est prêt pour un paiement réel."""

from __future__ import annotations

import os
import socket
import sys
from urllib.parse import urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from django.urls import reverse

from core.controllers import cinetpay_controller


def ok(label: str) -> None:
    print(f"  [OK] {label}")


def warn(label: str) -> None:
    print(f"  [!] {label}")


def fail(label: str) -> None:
    print(f"  [X] {label}")


def main() -> int:
    print("TimaLove — diagnostic CinetPay\n")
    errors = 0

    if cinetpay_controller.is_configured():
        ok("Clés APIKEY + SITE_ID présentes")
    else:
        fail("CINETPAY_APIKEY ou CINETPAY_SITE_ID manquant dans .env")
        errors += 1

    if getattr(settings, "CINETPAY_SECRET_KEY", ""):
        ok("CINETPAY_SECRET_KEY présente (HMAC notify)")
    else:
        warn("CINETPAY_SECRET_KEY vide — le webhook sera accepté sans HMAC")

    site = (settings.SITE_URL or "").rstrip("/")
    notify = f"{site}{reverse('api:cinetpay_notify')}"
    print(f"  SITE_URL     : {site or '(vide)'}")
    print(f"  notify_url   : {notify}")
    print(f"  return_url   : {site}{reverse('api:payments_confirm')}")
    print(f"  API Checkout : {cinetpay_controller.init_url()}")

    local = any(token in site.lower() for token in ("127.0.0.1", "localhost", "[::1]"))
    https = site.lower().startswith("https://")
    if local:
        warn("SITE_URL est local — CinetPay ne peut pas appeler le webhook. Paiement réel impossible ici.")
        warn("Pour un test réel : tunnel HTTPS (cloudflared) + SITE_URL=https://….trycloudflare.com")
    elif not https:
        fail("SITE_URL doit être en HTTPS pour un paiement réel.")
        errors += 1
    else:
        ok("SITE_URL public en HTTPS — webhook joignable en théorie")

    if settings.DEBUG:
        warn("DEBUG=True — à désactiver en production")
    if settings.PAYMENT_SIMULATION and not local:
        fail("PAYMENT_SIMULATION=True hors local — un paiement pourrait être simulé")
        errors += 1
    elif settings.PAYMENT_SIMULATION:
        warn("PAYMENT_SIMULATION=True — fallback simulation si CinetPay est injoignable")

    host = urlparse(cinetpay_controller.base_url()).hostname or ""
    try:
        infos = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
        ip = infos[0][4][0] if infos else "?"
        ok(f"DNS {host} → {ip}")
    except OSError as exc:
        fail(f"DNS {host} injoignable ({exc})")
        print("        CinetPay doit rétablir ce hostname, ou te donner une nouvelle URL Checkout v2.")
        print("        Une fois reçue : CINETPAY_BASE_URL=https://nouvel-hote/v2 dans .env")
        errors += 1

    print()
    if errors:
        print("Résultat : pas prêt pour un paiement réel.")
        return 1
    print("Résultat : configuration prête. Un clic « Choisir » doit ouvrir le guichet CinetPay.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
