"""Capture des erreurs HTTP / exceptions pour la page Monitoring."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse


class ExceptionLoggingMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        response = self.get_response(request)
        status = getattr(response, "status_code", 200) or 200
        if status >= 500:
            try:
                from core.controllers import monitoring_controller

                monitoring_controller.record_http_error(request, status)
            except Exception:  # noqa: BLE001
                pass
        return response

    def process_exception(self, request: HttpRequest, exception: Exception):
        try:
            from core.controllers import monitoring_controller

            monitoring_controller.record_exception(request, exception)
        except Exception:  # noqa: BLE001
            pass
        return None
