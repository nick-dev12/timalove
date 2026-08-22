"""URL publique du site (notifications, emails, paiements)."""

from __future__ import annotations

LOCAL_HOST_MARKERS = ("127.0.0.1", "localhost", "[::1]")


def is_local_site_url(url: str) -> bool:
    lowered = (url or "").lower()
    return any(marker in lowered for marker in LOCAL_HOST_MARKERS)


def resolve_public_site_url(raw: str, *, debug: bool, allowed_hosts: list[str]) -> str:
    """Remplace un SITE_URL local par le premier domaine public des ALLOWED_HOSTS."""
    url = (raw or "").strip().rstrip("/") or "http://127.0.0.1:8000"
    if not is_local_site_url(url):
        return url
    for host in allowed_hosts:
        h = (host or "").strip().lstrip(".")
        if not h or h in {"localhost", "127.0.0.1", "*"}:
            continue
        scheme = "http" if debug else "https"
        return f"{scheme}://{h}"
    return url


def site_url_is_public(url: str, *, debug: bool = False) -> bool:
    if is_local_site_url(url):
        return False
    if url.lower().startswith("https://"):
        return True
    return bool(debug and url.lower().startswith("http://"))
