#!/usr/bin/env python
"""Simule un webhook NabooPay (dev) pour tester l'activation sans paiement reel."""

from __future__ import annotations

import argparse
import json
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

from core.models import Transaction


def main() -> int:
    parser = argparse.ArgumentParser(description="Test webhook NabooPay local/ngrok")
    parser.add_argument("order_id", nargs="?", help="order_id interne (sub_...) ou NabooPay UUID")
    parser.add_argument("--url", help="URL webhook (defaut: NGROK_URL ou SITE_URL)")
    parser.add_argument("--status", default="completed", help="transaction_status NabooPay")
    args = parser.parse_args()

    order_id = (args.order_id or "").strip()
    if not order_id:
        tx = Transaction.objects.filter(status="pending").order_by("-created_at").first()
        if not tx:
            print("Aucune transaction pending. Passez order_id en argument.")
            return 1
        details = tx.payment_details or {}
        order_id = details.get("naboo_order_id") or tx.order_id
        print(f"Transaction pending : {tx.order_id} -> naboo {order_id}")

    base = (args.url or getattr(settings, "NGROK_URL", "") or settings.SITE_URL or "").rstrip("/")
    webhook = f"{base}/api/payments/naboo-webhook/"
    payload = {
        "order_id": order_id,
        "transaction_status": args.status,
        "amount": 2990,
        "currency": "XOF",
        "selected_payment_method": "wave",
    }
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    req = urllib.request.Request(
        webhook,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"POST {webhook}")
            print(f"Status HTTP : {resp.status}")
            print(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        print(f"Erreur HTTP {exc.code} : {exc.read().decode('utf-8', errors='replace')}")
        return 1
    except Exception as exc:
        print(f"Echec : {exc}")
        print("Verifiez que Django ecoute et que ngrok est actif (scripts/start_ngrok_webhook.ps1)")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
