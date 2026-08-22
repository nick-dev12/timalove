"""Test WebSocket /ws/notifications/ (in-process + live Daphne si disponible)."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
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


def test_live_daphne(cookie: str, host: str = "127.0.0.1", port: int = 8000) -> bool:
    try:
        from websocket import create_connection
    except ImportError:
        print("SKIP live: pip install websocket-client")
        return False

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    try:
        sock.connect((host, port))
    except OSError:
        print(f"SKIP live: rien n'écoute sur {host}:{port}")
        return False
    finally:
        sock.close()

    ws = create_connection(
        f"ws://{host}:{port}/ws/notifications/",
        cookie=cookie,
        timeout=8,
    )
    ws.close()
    return True


def main() -> int:
    auth = session_cookie_for("teste1@gmail.com")
    if not auth:
        print("FAIL: utilisateur teste1@gmail.com introuvable ou session impossible")
        return 1

    email, cookie = auth
    inproc = asyncio.run(test_in_process(cookie.encode()))
    print("in-process:", "OK" if inproc else "FAIL")
    if not inproc:
        return 2

    live = test_live_daphne(cookie)
    print("live Daphne (ws://127.0.0.1:8000/ws/notifications/):", "OK" if live else "FAIL")

    payload = {"status": "ok", "user": email, "live_daphne": live}
    print(json.dumps(payload, ensure_ascii=False))
    return 0 if live else 3


if __name__ == "__main__":
    raise SystemExit(main())
