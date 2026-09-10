"""Révision de déploiement (git short hash) — invalidation cache feed / clients."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from django.conf import settings


@lru_cache(maxsize=1)
def get_deploy_revision() -> str:
    base = Path(settings.BASE_DIR)
    for path in (base / "deploy-revision.txt", base.parent / "deploy-revision.txt"):
        try:
            if path.is_file():
                value = path.read_text(encoding="utf-8").strip()
                if value:
                    return value[:64]
        except OSError:
            continue
    return "dev"
