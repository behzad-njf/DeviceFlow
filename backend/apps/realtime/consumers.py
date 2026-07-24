import json
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework_simplejwt.tokens import AccessToken

from apps.common.crypto import hash_secret
from apps.devices.models import Device
from apps.realtime.broadcast import device_group, tenant_group
from apps.tenants.models import Membership

User = get_user_model()


class DashboardConsumer(AsyncJsonWebsocketConsumer):
    tenant_id = None

    async def connect(self):
        user, tenant_id = await self._authenticate()
        if user is None or user.is_anonymous or not tenant_id:
            await self.close(code=4401)
            return
        self.user = user
        self.tenant_id = str(tenant_id)
        await self.channel_layer.group_add(tenant_group(self.tenant_id), self.channel_name)
        await self.accept()
        await self.send_json(
            {
                "v": 1,
                "type": "connection.ack",
                "ts": None,
                "payload": {
                    "tenant_id": self.tenant_id,
                    "user_id": str(user.id),
                },
            }
        )

    async def disconnect(self, code):
        if self.tenant_id:
            await self.channel_layer.group_discard(
                tenant_group(self.tenant_id), self.channel_name
            )

    async def receive_json(self, content, **kwargs):
        event_type = content.get("type")
        if event_type == "ping":
            await self.send_json({"v": 1, "type": "pong", "payload": {}})
        elif event_type == "subscribe":
            # Tenant room already joined; acknowledge for protocol compatibility.
            await self.send_json(
                {
                    "v": 1,
                    "type": "subscribe.ack",
                    "payload": content.get("payload") or {},
                }
            )

    async def dashboard_event(self, event):
        await self.send_json(event["message"])

    async def _authenticate(self):
        query = parse_qs(self.scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        if not token:
            headers = dict(self.scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode()
            if auth.lower().startswith("bearer "):
                token = auth.split(" ", 1)[1]
        if not token:
            return AnonymousUser(), None
        return await self._user_from_token(token)

    @database_sync_to_async
    def _user_from_token(self, token: str):
        try:
            access = AccessToken(token)
            user_id = access.get("user_id") or access.get("sub")
            user = User.objects.get(id=user_id)
            tenant_id = access.get("tenant_id")
            if not tenant_id:
                membership = Membership.objects.filter(user=user, is_active=True).first()
                tenant_id = membership.tenant_id if membership else None
            elif not Membership.objects.filter(
                user=user, tenant_id=tenant_id, is_active=True
            ).exists():
                return AnonymousUser(), None
            return user, tenant_id
        except Exception:
            return AnonymousUser(), None


class AgentConsumer(AsyncJsonWebsocketConsumer):
    device = None

    async def connect(self):
        device = await self._authenticate_device()
        if device is None:
            await self.close(code=4401)
            return
        self.device = device
        await self.channel_layer.group_add(device_group(device.id), self.channel_name)
        await self.accept()
        await self.send_json(
            {
                "v": 1,
                "type": "connection.ack",
                "payload": {"device_id": str(device.id)},
            }
        )

    async def disconnect(self, code):
        if self.device is not None:
            await self.channel_layer.group_discard(
                device_group(self.device.id), self.channel_name
            )

    async def receive_json(self, content, **kwargs):
        if content.get("type") == "ping":
            await self.send_json({"v": 1, "type": "pong", "payload": {}})

    async def agent_event(self, event):
        await self.send_json(event["message"])

    async def _authenticate_device(self):
        query = parse_qs(self.scope.get("query_string", b"").decode())
        token = (query.get("token") or [None])[0]
        if not token:
            headers = dict(self.scope.get("headers") or [])
            auth = headers.get(b"authorization", b"").decode()
            if auth.lower().startswith("device "):
                token = auth.split(" ", 1)[1]
        if not token:
            # First-frame auth is handled after connect in some clients; require query/header for now.
            return None
        return await self._device_from_token(token)

    @database_sync_to_async
    def _device_from_token(self, token: str):
        try:
            return Device.objects.select_related("tenant").get(
                device_token_hash=hash_secret(token)
            )
        except Device.DoesNotExist:
            return None
