"""Limites de fréquence (connexion, inscription, messages)."""

from __future__ import annotations

from django.core.cache import cache


def is_limited(key: str, max_attempts: int) -> bool:
    return int(cache.get(key, 0) or 0) >= max_attempts


def hit(key: str, window_seconds: int) -> int:
    try:
        return int(cache.incr(key))
    except ValueError:
        cache.set(key, 1, window_seconds)
        return 1


def clear(key: str) -> None:
    cache.delete(key)
