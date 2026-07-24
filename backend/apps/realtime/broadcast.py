"""WebSocket fan-out helpers for the dashboard."""
from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone


def _envelope(event_type: str, payload: dict, request_id: str | None = None) -> dict:
    return {
        "v": 1,
        "type": event_type,
        "request_id": request_id,
        "ts": timezone.now().isoformat(),
        "payload": payload,
    }


def tenant_group(tenant_id) -> str:
    return f"tenant.{tenant_id}"


def device_group(device_id) -> str:
    return f"device.{device_id}"


def broadcast_tenant(tenant_id, event_type: str, payload: dict) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        tenant_group(tenant_id),
        {"type": "dashboard.event", "message": _envelope(event_type, payload)},
    )


def broadcast_device(device_id, event_type: str, payload: dict) -> None:
    channel_layer = get_channel_layer()
    if channel_layer is None:
        return
    async_to_sync(channel_layer.group_send)(
        device_group(device_id),
        {"type": "agent.event", "message": _envelope(event_type, payload)},
    )


def broadcast_alert(tenant_id, *, severity: str, title: str, body: str, meta: dict | None = None):
    broadcast_tenant(
        tenant_id,
        "alert",
        {
            "severity": severity,
            "title": title,
            "body": body,
            "meta": meta or {},
        },
    )
