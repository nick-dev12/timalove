"""WebSocket consumers — chat & notifications."""

from __future__ import annotations

import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


@database_sync_to_async
def _profile_id_for(user) -> str | None:
    if not user or not getattr(user, "is_authenticated", False):
        return None
    from core.models import Profile

    try:
        return str(Profile.objects.values_list("id", flat=True).get(user_id=user.pk))
    except Profile.DoesNotExist:
        return None


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        profile_id = await _profile_id_for(user)
        if not profile_id:
            await self.close(code=4401)
            return
        self.profile_id = profile_id
        self.partner_id = str(self.scope["url_route"]["kwargs"]["partner_id"])
        lo, hi = sorted([self.profile_id, self.partner_id])
        self.room_name = f"chat_{lo}_{hi}"
        await self.accept()
        try:
            await self.channel_layer.group_add(self.room_name, self.channel_name)
        except Exception:
            logger.exception("[ws] chat group_add a échoué")

    async def disconnect(self, code):
        if hasattr(self, "room_name"):
            try:
                await self.channel_layer.group_discard(self.room_name, self.channel_name)
            except Exception:
                pass

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
            await self.close(code=4401)
            return
        self.profile_id = profile_id
        self.group = f"notif_{profile_id}"
        # Accepter et répondre tout de suite pour que Nginx envoie le 101
        # avant tout appel Redis (sinon le navigateur voit un 1006).
        await self.accept()
        await self.send(text_data=json.dumps({"event": "connected", "ok": True}))
        if self.channel_layer is None:
            logger.warning("[ws] channel layer absent")
            await self._mark_connected()
            return
        try:
            await self.channel_layer.group_add(self.group, self.channel_name)
            await self.channel_layer.group_add("presence", self.channel_name)
        except Exception:
            logger.exception("[ws] notification group_add a échoué")
        became_online = await self._mark_connected()
        if became_online:
            await self._broadcast_presence(True)

    async def disconnect(self, code):
        became_offline = False
        if hasattr(self, "profile_id"):
            became_offline = await self._mark_disconnected()
        if hasattr(self, "group"):
            try:
                await self.channel_layer.group_discard(self.group, self.channel_name)
            except Exception:
                pass
        try:
            await self.channel_layer.group_discard("presence", self.channel_name)
        except Exception:
            pass
        if became_offline:
            await self._broadcast_presence(False)

    async def receive(self, text_data=None, bytes_data=None):
        data = json.loads(text_data or "{}")
        if data.get("type") == "ping" or data.get("event") == "ping":
            if hasattr(self, "profile_id"):
                await self._heartbeat()
            await self.send(text_data=json.dumps({"event": "pong"}))

    async def notify(self, event):
        await self.send(text_data=json.dumps(event.get("payload", {})))

    async def presence_event(self, event):
        await self.send(text_data=json.dumps(event.get("payload", {})))

    async def _broadcast_presence(self, online: bool):
        if self.channel_layer is None or not hasattr(self, "profile_id"):
            return
        from core.controllers.presence_controller import presence_payload

        try:
            await self.channel_layer.group_send(
                "presence",
                {"type": "presence_event", "payload": presence_payload(self.profile_id, online)},
            )
        except Exception:
            logger.exception("[ws] broadcast présence a échoué")

    @database_sync_to_async
    def _mark_connected(self) -> bool:
        from core.controllers import presence_controller

        return presence_controller.mark_socket_connected(self.profile_id)

    @database_sync_to_async
    def _mark_disconnected(self) -> bool:
        from core.controllers import presence_controller

        return presence_controller.mark_socket_disconnected(self.profile_id)

    @database_sync_to_async
    def _heartbeat(self) -> None:
        from core.controllers import presence_controller

        presence_controller.heartbeat(self.profile_id)
