"""Capture des erreurs HTTP / exceptions pour la page Monitoring."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse


class ExceptionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        return self.get_response(request)

    def process_exception(self, request: HttpRequest, exception: Exception):
        try:
            from core.controllers import monitoring_controller

            monitoring_controller.record_exception(request, exception)
        except Exception:  # noqa: BLE001
            pass
        return None
