"""Vérifications post-déploiement : temps réel, notifications, Redis, Celery."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "timalove"
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


def _http_status(url: str, timeout: int = 12) -> tuple[int | None, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read(512).decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        return exc.code, str(exc.reason)
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def check_push_config(site_url: str) -> tuple[bool, str]:
    url = site_url.rstrip("/") + "/api/push/config/"
    status, detail = _http_status(url)
    if status != 200:
        return False, f"HTTP {status} — {detail[:120]}"
    try:
        with urllib.request.urlopen(url, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        if "enabled" not in data or "firebase" not in data:
            return False, "JSON push config incomplet"
        enabled = bool(data.get("enabled"))
        return True, f"push config OK (enabled={enabled})"
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def check_api_endpoints(site_url: str) -> tuple[bool, str]:
    base = site_url.rstrip("/")
    checks = [
        ("/api/notifications/unread-count/", {200, 302, 401, 403}),
        ("/api/messages/unread-count/", {200, 302, 401, 403}),
    ]
    results: list[str] = []
    ok = True
    for path, allowed in checks:
        status, _ = _http_status(base + path, timeout=8)
        if status in allowed:
            results.append(f"{path} → {status}")
        else:
            ok = False
            results.append(f"{path} → {status or 'ERR'} (attendu {sorted(allowed)})")
    return ok, "; ".join(results)


def check_redis_channels() -> tuple[bool, str]:
    import django

    django.setup()
    from django.conf import settings

    backend = settings.CHANNEL_LAYERS.get("default", {}).get("BACKEND", "")
    if "InMemory" in backend:
        return False, "ChannelLayer InMemory — USE_REDIS_CHANNELS=False en prod ?"

    redis_url = os.environ.get("REDIS_URL") or getattr(settings, "REDIS_URL", "")
    if not redis_url:
        return False, "REDIS_URL absent"

    try:
        import redis

        client = redis.from_url(redis_url, socket_connect_timeout=3)
        client.ping()
        return True, f"Redis Channels OK ({redis_url})"
    except Exception as exc:  # noqa: BLE001
        return False, f"Redis ping échoué — {exc}"


def check_celery_worker() -> tuple[bool, str]:
    import django

    django.setup()
    from config.celery import app

    try:
        replies = app.control.inspect(timeout=5).ping() or {}
    except Exception as exc:  # noqa: BLE001
        return False, f"Celery inspect — {exc}"

    if not replies:
        return False, "Aucun worker Celery ne répond au ping"
    nodes = ", ".join(sorted(replies))
    return True, f"workers OK ({nodes})"


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
        return True, "WebSocket OK en local (Daphne) — vérifier le proxy Nginx /ws public", True
    if code == 3:
        return False, "WebSocket indisponible (public et local)", False
    return False, f"WebSocket échec interne (code {code})", False


def main() -> int:
    parser = argparse.ArgumentParser(description="Vérifications runtime TimaLove")
    parser.add_argument(
        "--site-url",
        default=os.environ.get("SITE_URL", "https://mytimalove.com"),
        help="URL publique du site",
    )
    args = parser.parse_args()
    site = args.site_url.rstrip("/")

    failures = 0
    warnings = 0

    checks: list[tuple[str, tuple[bool, str] | tuple[bool, str, bool]]] = [
        ("redis/channels", check_redis_channels()),
        ("celery/worker", check_celery_worker()),
        ("api/endpoints", check_api_endpoints(site)),
        ("notifications/push", check_push_config(site)),
        ("websocket", check_websocket(site)),
    ]

    for label, result in checks:
        if len(result) == 3:
            ok, msg, warn_only = result
            if ok and warn_only:
                print(f"{label}: WARN — {msg}")
                warnings += 1
            elif ok:
                print(f"{label}: OK — {msg}")
            else:
                print(f"{label}: FAIL — {msg}")
                failures += 1
        else:
            ok, msg = result
            if ok:
                print(f"{label}: OK — {msg}")
            else:
                print(f"{label}: FAIL — {msg}")
                failures += 1

    print(f"summary: failures={failures} warnings={warnings}")
    if failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
