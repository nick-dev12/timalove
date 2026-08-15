from __future__ import annotations

from django.urls import path

from core.consumers import ChatConsumer, NotificationConsumer

websocket_urlpatterns = [
    path("ws/chat/<uuid:partner_id>/", ChatConsumer.as_asgi()),
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]
