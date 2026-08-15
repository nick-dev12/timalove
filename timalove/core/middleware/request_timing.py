"""
Middleware de timing des requêtes (base pour monitoring / debug).
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)


class RequestTimingMiddleware:
    """Ajoute l'en-tête X-Response-Time et loggue la durée en DEBUG."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        start = time.perf_counter()
        response = self.get_response(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response["X-Response-Time"] = f"{duration_ms:.1f}ms"
        if duration_ms > 500:
            logger.warning("Slow request %s %s (%.1fms)", request.method, request.path, duration_ms)
        return response
