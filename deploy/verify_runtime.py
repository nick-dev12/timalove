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


def check_websocket(site_url: str) -> tuple[bool, str]:
    import django

    django.setup()

    from scripts.test_ws_notifications import main as ws_main

    os.environ["TIMALOVE_SITE_URL"] = site_url.rstrip("/")
    code = ws_main(site_url=site_url.rstrip("/"))
    if code == 0:
        return True, "WebSocket OK"
    if code == 3:
        return False, "WebSocket live indisponible"
    return False, f"WebSocket échec (code {code})"


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

    ws_ok, ws_msg = check_websocket(site)
    print(f"websocket: {'OK' if ws_ok else 'FAIL'} — {ws_msg}")

    if push_ok and ws_ok:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
