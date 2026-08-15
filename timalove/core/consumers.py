"""WebSocket consumers — chat & notifications."""

from __future__ import annotations

import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated:
            await self.close()
            return
        self.partner_id = str(self.scope["url_route"]["kwargs"]["partner_id"])
        self.room_name = f"chat_{min(str(user.profile.id), self.partner_id)}_{max(str(user.profile.id), self.partner_id)}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "room_name"):
            await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data or "{}")
        content = data.get("content", "")
        user = self.scope["user"]
        ok, msg, message = await self._send(user.profile.id, self.partner_id, content)
        payload = {
            "ok": ok,
            "message": msg,
            "content": content if ok else None,
            "sender_id": str(user.profile.id),
        }
        if ok:
            await self.channel_layer.group_send(
                self.room_name, {"type": "chat.message", "payload": payload}
            )
        else:
            await self.send(text_data=json.dumps(payload))

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
        if not user or not user.is_authenticated:
            await self.close()
            return
        self.group = f"notif_{user.profile.id}"
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group"):
            await self.channel_layer.group_discard(self.group, self.channel_name)

    async def notify(self, event):
        await self.send(text_data=json.dumps(event.get("payload", {})))
