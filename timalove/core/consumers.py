"""WebSocket consumers — chat & notifications."""

from __future__ import annotations

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


@database_sync_to_async
def _profile_id_for(user) -> str | None:
    if not user or not user.is_authenticated:
        return None
    profile = getattr(user, "profile", None)
    if profile is None:
        return None
    return str(profile.id)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        profile_id = await _profile_id_for(user)
        if not profile_id:
            await self.close()
            return
        self.profile_id = profile_id
        self.partner_id = str(self.scope["url_route"]["kwargs"]["partner_id"])
        lo, hi = sorted([self.profile_id, self.partner_id])
        self.room_name = f"chat_{lo}_{hi}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data or "{}")
        content = data.get("content", "")
        ok, msg, message = await self._send(self.profile_id, self.partner_id, content)
        if not ok:
            await self.send(
                text_data=json.dumps({"event": "error", "ok": False, "message": msg, "code": "message_limit" if "limite" in (msg or "").lower() else ""})
            )
        elif message:
            await self.send(
                text_data=json.dumps(
                    {
                        "event": "sent",
                        "ok": True,
                        "message_id": str(message.id),
                    }
                )
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event["payload"]))

    @database_sync_to_async
    def _send(self, profile_id, partner_id, content):
        from core.controllers import message_controller
        from core.models import Profile

        profile = Profile.objects.get(pk=profile_id)
        return message_controller.send_text(profile, partner_id, content)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        profile_id = await _profile_id_for(user)
        if not profile_id:
            await self.close()
            return
        self.group = f"notif_{profile_id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data or "{}")
        if data.get("type") == "ping" or data.get("event") == "ping":
            await self.send(text_data=json.dumps({"event": "pong"}))

    async def notify(self, event):
        await self.send(text_data=json.dumps(event.get("payload", {})))
