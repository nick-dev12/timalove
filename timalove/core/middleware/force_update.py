"""Middleware — force update des applications mobiles."""

from __future__ import annotations

from django.http import HttpRequest, HttpResponse, JsonResponse


class ForceUpdateMiddleware:
    API_PREFIX = "/api/"
    SKIP_PATHS = (
        "/api/health/",
        "/api/site-config/",
        "/api/app-config/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        path = request.path
        if path.startswith(self.API_PREFIX) and not any(path.startswith(p) for p in self.SKIP_PATHS):
            platform = (
                request.headers.get("X-TimaLove-Platform")
                or request.headers.get("X-App-Platform")
                or request.GET.get("platform")
                or ""
            )
            version = (
                request.headers.get("X-TimaLove-App-Version")
                or request.headers.get("X-App-Version")
                or request.GET.get("app_version")
                or ""
            )
            if platform and version:
                from core.controllers import app_config_controller

                block = app_config_controller.force_update_check(platform=platform, app_version=version)
                if block:
                    return JsonResponse(
                        {"ok": False, "error": "force_update_required", **block},
                        status=426,
                    )
        return self.get_response(request)
