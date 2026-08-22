"""Test WebSocket /ws/notifications/ (in-process + live Daphne si disponible)."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from channels.testing import WebsocketCommunicator  # noqa: E402
from config.asgi import application  # noqa: E402
from django.contrib.auth import get_user_model  # noqa: E402
from django.test import Client  # noqa: E402


def session_cookie_for(email: str) -> tuple[str, str] | None:
    user = get_user_model().objects.filter(email__iexact=email).first()
    if not user:
        return None
    client = Client()
    client.force_login(user)
    session_key = client.session.session_key
    if not session_key:
        return None
    return user.email, f"sessionid={session_key}"


async def test_in_process(cookie: bytes) -> bool:
    communicator = WebsocketCommunicator(
        application,
        "/ws/notifications/",
        headers=[(b"cookie", cookie)],
    )
    connected, _ = await communicator.connect()
    if not connected:
        return False
    await communicator.disconnect()
    return True


def test_live_ws(cookie: str, site_url: str, *, label: str = "live") -> bool:
    try:
        from websocket import create_connection
    except ImportError:
        print(f"SKIP {label}: pip install websocket-client")
        return False

    parsed = urllib.parse.urlparse(site_url.rstrip("/"))
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port
    ws_scheme = "wss" if parsed.scheme == "https" else "ws"
    if port is None:
        port = 443 if parsed.scheme == "https" else 80

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        sock.connect((host, port))
    except OSError:
        print(f"SKIP {label}: rien n'écoute sur {host}:{port}")
        return False
    finally:
        sock.close()

    ws_url = f"{ws_scheme}://{host}:{port}/ws/notifications/"
    try:
        ws = create_connection(ws_url, cookie=cookie, timeout=12)
        ws.close()
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"FAIL {label}: {exc}")
        return False


def test_live_daphne(cookie: str, site_url: str = "http://127.0.0.1:8000") -> bool:
    return test_live_ws(cookie, site_url, label="live")


def main(site_url: str | None = None) -> int:
    site = (site_url or os.environ.get("TIMALOVE_SITE_URL") or "http://127.0.0.1:8000").rstrip("/")
    auth = session_cookie_for("teste1@gmail.com")
    if not auth:
        print("FAIL: utilisateur teste1@gmail.com introuvable ou session impossible")
        return 1

    email, cookie = auth
    inproc = asyncio.run(test_in_process(cookie.encode()))
    print("in-process:", "OK" if inproc else "FAIL")
    if not inproc:
        return 2

    live_public = test_live_daphne(cookie, site_url=site)
    print(f"live public ({site}/ws/notifications/):", "OK" if live_public else "FAIL")

    daphne_port = int(os.environ.get("DAPHNE_PORT", "8001"))
    live_local = test_live_ws(cookie, f"http://127.0.0.1:{daphne_port}", label="live-local")
    print(f"live local (127.0.0.1:{daphne_port}/ws/notifications/):", "OK" if live_local else "FAIL")

    live_ok = live_public or live_local
    payload = {
        "status": "ok" if live_ok else "degraded",
        "user": email,
        "live_public": live_public,
        "live_local": live_local,
        "site": site,
    }
    print(json.dumps(payload, ensure_ascii=False))
    if not live_ok:
        return 3
    if not live_public and live_local:
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
