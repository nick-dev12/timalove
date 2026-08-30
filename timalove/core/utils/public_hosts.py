"""Enregistre un domaine public (ngrok, prod) dans ALLOWED_HOSTS / CSRF."""

from __future__ import annotations

from urllib.parse import urlparse


def host_from_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    netloc = parsed.netloc or parsed.path.split("/")[0]
    return netloc.split(":")[0].strip()


def origin_from_url(url: str) -> str:
    parsed = urlparse((url or "").strip())
    if not parsed.scheme or not parsed.netloc:
        return ""
    return f"{parsed.scheme}://{parsed.netloc}"


def extend_hosts(url: str, *, allowed_hosts: list[str], csrf_origins: list[str]) -> None:
    host = host_from_url(url)
    if not host:
        return
    if host not in allowed_hosts:
        allowed_hosts.append(host)
    origin = origin_from_url(url)
    if origin and origin not in csrf_origins:
        csrf_origins.append(origin)
