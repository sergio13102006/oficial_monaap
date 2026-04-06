import json
import logging
from urllib.parse import parse_qs

from django.conf import settings
from asgiref.sync import sync_to_async

from .services.realtime_notifications import (
    ADMIN_GROUP,
    build_session_group_name,
    build_tablet_group_name,
    build_runtime_event,
    get_realtime_enabled,
    notify_tablet_connected,
)
from .services.realtime_service import validate_tablet_ws_token

if get_realtime_enabled():
    from channels.db import database_sync_to_async
    from channels.generic.websocket import AsyncJsonWebsocketConsumer
else:
    database_sync_to_async = sync_to_async

    class AsyncJsonWebsocketConsumer:  # pragma: no cover - fallback when channels is unavailable
        @classmethod
        def as_asgi(cls):
            raise RuntimeError("Channels no esta instalado o habilitado.")


logger = logging.getLogger(__name__)


async def _safe_json_send(consumer, payload):
    await consumer.send(text_data=json.dumps(payload))


class TabletConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        self.tablet_id = self.scope["url_route"]["kwargs"]["tablet_id"]
        self.tablet_group = build_tablet_group_name(self.tablet_id)
        self.session_group = None
        self.raw_query_string = (self.scope.get("query_string") or b"").decode()

        if not await self._is_authorized_tablet():
            logger.warning("Rejected tablet websocket for tablet_id=%s", self.tablet_id)
            await self.close(code=4403)
            return

        await self.channel_layer.group_add(self.tablet_group, self.channel_name)
        await self.accept()
        await self._mark_connected()
        logger.info("Tablet websocket connected for tablet_id=%s", self.tablet_id)
        await sync_to_async(notify_tablet_connected)(
            self.tablet_id,
            payload={"connection": "connected"},
        )

    async def disconnect(self, close_code):
        if getattr(self, "session_group", None):
            await self.channel_layer.group_discard(self.session_group, self.channel_name)
        if getattr(self, "tablet_group", None):
            await self.channel_layer.group_discard(self.tablet_group, self.channel_name)
        await self._mark_disconnected()
        logger.info("Tablet websocket disconnected for tablet_id=%s code=%s", self.tablet_id, close_code)

    async def receive_json(self, content, **kwargs):
        event_type = content.get("type")
        session_id = content.get("session_id")

        if session_id:
            session_group = build_session_group_name(session_id)
            if session_group != self.session_group:
                if self.session_group:
                    await self.channel_layer.group_discard(self.session_group, self.channel_name)
                self.session_group = session_group
                await self.channel_layer.group_add(self.session_group, self.channel_name)

        if event_type == "sync_request":
            await self._touch_activity()
            await _safe_json_send(
                self,
                build_runtime_event(
                    "sync_state",
                    tablet_id=self.tablet_id,
                    session_id=session_id,
                    status="ok",
                    payload={},
                    source="tablet_consumer",
                ),
            )

    async def session_assigned(self, event):
        await _safe_json_send(self, event["event"])

    async def session_cancelled(self, event):
        await _safe_json_send(self, event["event"])

    async def back_to_waiting(self, event):
        await _safe_json_send(self, event["event"])

    async def reconnect_required(self, event):
        await _safe_json_send(self, event["event"])

    @database_sync_to_async
    def _is_authorized_tablet(self):
        query_params = parse_qs(self.raw_query_string)
        access_token = (query_params.get("access_token") or [None])[0]
        return validate_tablet_ws_token(self.tablet_id, access_token)

    @database_sync_to_async
    def _mark_connected(self):
        from .services.tablet_service import mark_kiosk_connection

        mark_kiosk_connection(self.tablet_id, connected=True)

    @database_sync_to_async
    def _mark_disconnected(self):
        from .services.tablet_service import mark_kiosk_connection

        mark_kiosk_connection(self.tablet_id, connected=False)

    @database_sync_to_async
    def _touch_activity(self):
        from .services.tablet_service import touch_kiosk_activity

        touch_kiosk_activity(self.tablet_id)


class AdminConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        user = self.scope.get("user")
        if not user or not user.is_authenticated or not user.is_staff:
            logger.warning("Rejected admin websocket for anonymous or non-staff user")
            await self.close(code=4403)
            return
        self.admin_group = ADMIN_GROUP
        await self.channel_layer.group_add(self.admin_group, self.channel_name)
        await self.accept()
        logger.info("Admin websocket connected for user=%s", user)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.admin_group, self.channel_name)
        logger.info("Admin websocket disconnected code=%s", close_code)

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await _safe_json_send(
                self,
                build_runtime_event(
                    "pong",
                    status="ok",
                    payload={},
                    source="admin_consumer",
                ),
            )

    async def tablet_connected(self, event):
        await _safe_json_send(self, event["event"])

    async def session_opened(self, event):
        await _safe_json_send(self, event["event"])

    async def signature_completed(self, event):
        await _safe_json_send(self, event["event"])

    async def save_error(self, event):
        await _safe_json_send(self, event["event"])
