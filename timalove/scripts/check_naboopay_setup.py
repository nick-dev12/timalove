#!/usr/bin/env python
"""Diagnostic NabooPay — local ou vérification post-déploiement."""

from __future__ import annotations

import argparse
import os
import sys
import urllib.error
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings
from django.urls import reverse

from core.controllers import naboopay_controller, payment_controller
from core.utils.site_url import is_local_site_url, site_url_is_public


def webhook(base: str) -> str:
    return f"{base.rstrip('/')}{reverse('api:naboo_webhook')}"


def check_webhook_http(base: str) -> tuple[bool, str]:
    url = webhook(base)
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = resp.read().decode("utf-8", errors="replace").strip()
            if resp.status == 200 and body == "OK":
                return True, url
            return False, f"{url} -> HTTP {resp.status} ({body[:80] or 'vide'})"
    except urllib.error.HTTPError as exc:
        return False, f"{url} -> HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, f"{url} -> {exc}"


def run_deploy_checks(site_url: str) -> int:
    print("=== NabooPay — vérification déploiement ===\n")
    errors: list[str] = []
    warnings: list[str] = []

    explicit = (getattr(settings, "PAYMENT_PROVIDER", "") or "").strip().lower()
    provider = payment_controller._provider()

    if explicit == "cinetpay":
        print("Prestataire : CinetPay (NabooPay ignoré)")
        return 0

    print(f"Prestataire actif : {provider or '(aucun)'}")
    if provider != "naboopay":
        errors.append(
            "PAYMENT_PROVIDER doit etre 'naboopay' ou laisse vide avec NABOOPAY_API_KEY renseignee."
        )

    if not naboopay_controller.is_configured():
        errors.append("NABOOPAY_API_KEY manquante dans .env")
    else:
        key = settings.NABOOPAY_API_KEY
        print(f"OK Clé API : {key[:18]}...{key[-6:]}")

    if not naboopay_controller.webhook_secret_configured():
        errors.append("NABOOPAY_WEBHOOK_SECRET manquant — requis en production pour valider les webhooks.")

    site = (getattr(settings, "SITE_URL", "") or "").rstrip("/")
    checkout_base = (payment_controller._site_url() or "").rstrip("/")
    prod = (getattr(settings, "NABOOPAY_PRODUCTION_SITE_URL", "") or site_url or site).rstrip("/")

    print(f"\n--- URLs ---")
    print(f"  SITE_URL (.env)     : {site}")
    print(f"  Checkout / webhook  : {checkout_base}")
    print(f"  Production ref.     : {prod}")

    if is_local_site_url(site):
        errors.append(f"SITE_URL locale ({site}) — définissez SITE_URL={site_url} dans .env")
    elif not site_url_is_public(site, debug=settings.DEBUG):
        errors.append(f"SITE_URL doit être HTTPS en production ({site})")

    if is_local_site_url(checkout_base):
        errors.append(
            f"URL checkout locale ({checkout_base}) — vérifiez SITE_URL ou NABOOPAY_PUBLIC_SITE_URL"
        )

    webhook_prod = webhook(prod)
    print(f"\n--- Endpoints ---")
    print(f"  Webhook dashboard : {webhook_prod}")
    print(f"  Retour client     : {prod}{reverse('api:payments_confirm')}?order_id=ORDER_ID")
    print(f"  Méthodes          : {', '.join(naboopay_controller.methods())}")

    check_url = prod if site_url_is_public(prod, debug=settings.DEBUG) else checkout_base
    if check_url and not is_local_site_url(check_url):
        ok, detail = check_webhook_http(check_url)
        if ok:
            print(f"\nOK Webhook accessible : GET {detail} -> OK")
        else:
            errors.append(f"Webhook inaccessible : {detail}")
    else:
        errors.append("Impossible de tester le webhook (URL publique absente)")

    try:
        from core.controllers import site_settings_controller

        plans = site_settings_controller.active_subscription_plans_list()
        if not plans:
            warnings.append("Aucune formule d'abonnement active.")
        else:
            print(f"\nOK Formules actives : {len(plans)}")
    except Exception as exc:  # noqa: BLE001
        warnings.append(f"Formules d'abonnement non vérifiables : {exc}")

    print("")
    for msg in warnings:
        print(f"! {msg}")
    for msg in errors:
        print(f"ERREUR {msg}")

    if errors:
        print("\nÉchec — corrigez .env / dashboard NabooPay puis relancez deploy.sh")
        print("Aide : python scripts/naboopay_webhook_setup.py")
        return 1

    print("\nOK NabooPay prêt pour la production")
    return 0


def run_diagnostic() -> int:
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


def main() -> int:
    parser = argparse.ArgumentParser(description="Diagnostic NabooPay TimaLove")
    parser.add_argument(
        "--deploy",
        action="store_true",
        help="Vérification stricte post-déploiement (échoue si config prod incomplète)",
    )
    parser.add_argument(
        "--site-url",
        default=os.environ.get("SITE_URL", "https://timalove.goo-bridge.com"),
        help="URL publique attendue en production",
    )
    args = parser.parse_args()
    if args.deploy:
        return run_deploy_checks(args.site_url.rstrip("/"))
    return run_diagnostic()


if __name__ == "__main__":
    raise SystemExit(main())
