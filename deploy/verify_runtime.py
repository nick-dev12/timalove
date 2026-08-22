"""Vérifications post-déploiement : push config + WebSocket notifications."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "timalove"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def check_push_config(site_url: str) -> tuple[bool, str]:
    url = site_url.rstrip("/") + "/api/push/config/"
    try:
        with urllib.request.urlopen(url, timeout=12) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            if resp.status != 200:
                return False, f"HTTP {resp.status}"
            data = json.loads(body)
            if "enabled" not in data or "firebase" not in data:
                return False, "JSON push config incomplet"
            return True, "push config OK"
    except urllib.error.HTTPError as exc:
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def check_websocket(site_url: str) -> tuple[bool, str, bool]:
    """Retourne (ok, message, warn_only). warn_only=True si Daphne local OK mais pas le public."""
    import django

    django.setup()

    from scripts.test_ws_notifications import main as ws_main

    os.environ["TIMALOVE_SITE_URL"] = site_url.rstrip("/")
    code = ws_main(site_url=site_url.rstrip("/"))
    if code == 0:
        return True, "WebSocket OK (public + stack)", False
    if code == 4:
        return True, "WebSocket OK en local (Daphne) — vérifier le proxy Nginx /wss public", True
    if code == 3:
        return False, "WebSocket indisponible (public et local)", False
    return False, f"WebSocket échec interne (code {code})", False


def main() -> int:
    parser = argparse.ArgumentParser(description="Vérifications runtime TimaLove")
    parser.add_argument(
        "--site-url",
        default=os.environ.get("SITE_URL", "https://timalove.goo-bridge.com"),
        help="URL publique du site",
    )
    args = parser.parse_args()
    site = args.site_url.rstrip("/")

    push_ok, push_msg = check_push_config(site)
    print(f"notifications/push: {'OK' if push_ok else 'FAIL'} — {push_msg}")

    ws_ok, ws_msg, ws_warn = check_websocket(site)
    if ws_ok and ws_warn:
        print(f"websocket: WARN — {ws_msg}")
    elif ws_ok:
        print(f"websocket: OK — {ws_msg}")
    else:
        print(f"websocket: FAIL — {ws_msg}")

    if push_ok and ws_ok:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
