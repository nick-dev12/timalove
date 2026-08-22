#!/usr/bin/env python
"""Diagnostic production — Apple Auth + CinetPay."""

from __future__ import annotations

import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from django.conf import settings


def main() -> int:
    print("=" * 60)
    print("TimaLove — checklist production")
    print("=" * 60)
    print(f"SITE_URL actuel : {settings.SITE_URL}")
    print()

    scripts = [
        ("Apple Auth", os.path.join(ROOT, "scripts", "check_apple_auth_setup.py")),
        ("CinetPay", os.path.join(ROOT, "scripts", "check_cinetpay_setup.py")),
    ]
    code = 0
    for label, path in scripts:
        print(f"\n--- {label} ---")
        result = subprocess.run([sys.executable, path], cwd=ROOT)
        if result.returncode:
            code = 1

    print("\n" + "=" * 60)
    if code:
        print("Actions manuelles avant test réel :")
        print("  • Firebase : Authorized domains → timalove.goo-bridge.com")
        print("  • Apple Developer : Services ID → domaine goo-bridge.com")
        print("  • Firebase Hosting : firebase deploy --only hosting (apple-signin.html)")
        print("  • CinetPay : contacter le support si DNS api-checkout.cinetpay.com mort")
    else:
        print("Prêt pour les tests manuels sur https://timalove.goo-bridge.com")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
