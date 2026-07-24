from apps.devices.models import Device, DeviceEvent
from apps.messaging.models import Message
from apps.realtime.broadcast import broadcast_device, broadcast_tenant


def device_summary(device: Device) -> dict:
    meta = device.meta or {}
    summary = {
        "id": str(device.id),
        "name": device.name,
        "status": device.status,
        "agent_version": device.agent_version,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
        "health": device.health,
        "health_score": device.health_score,
        "is_paired": device.is_paired,
        "meta": meta,
    }
    lat, lng = meta.get("lat"), meta.get("lng")
    if lat is not None and lng is not None:
        summary["lat"] = lat
        summary["lng"] = lng
        summary["city"] = meta.get("city") or ""
        if meta.get("accuracy_m") is not None:
            summary["accuracy_m"] = meta.get("accuracy_m")
        if meta.get("location_received_at"):
            summary["location_received_at"] = meta.get("location_received_at")
    return summary


def message_summary(message: Message) -> dict:
    return {
        "id": str(message.id),
        "to_number": message.to_number,
        "status": message.status,
        "device": str(message.device_id) if message.device_id else None,
        "device_name": message.device.name if message.device_id else None,
        "retry_count": message.retry_count,
        "error_message": message.error_message,
        "updated_at": message.updated_at.isoformat() if message.updated_at else None,
    }


def queue_summary_for_device(device: Device) -> dict:
    qs = Message.objects.filter(device=device)
    return {
        "device_id": str(device.id),
        "pending": qs.filter(
            status__in=[
                Message.Status.QUEUED,
                Message.Status.ASSIGNED,
                Message.Status.SCHEDULED,
                Message.Status.RETRYING,
            ]
        ).count(),
        "sending": qs.filter(status=Message.Status.SENDING).count(),
        "failed": qs.filter(status=Message.Status.FAILED).count(),
        "dead_letter": qs.filter(status=Message.Status.DEAD_LETTER).count(),
    }


def publish_device_updated(device: Device) -> None:
    broadcast_tenant(device.tenant_id, "device.updated", device_summary(device))
    broadcast_tenant(device.tenant_id, "device.health", {
        "device_id": str(device.id),
        "health": device.health,
        "status": device.status,
        "last_seen_at": device.last_seen_at.isoformat() if device.last_seen_at else None,
    })


def publish_message_updated(message: Message) -> None:
    broadcast_tenant(message.tenant_id, "message.updated", message_summary(message))
    if message.device_id:
        broadcast_tenant(
            message.tenant_id,
            "queue.updated",
            queue_summary_for_device(message.device),
        )
    # Map message status → webhook event
    status_map = {
        Message.Status.QUEUED: "message.queued",
        Message.Status.ASSIGNED: "message.assigned",
        Message.Status.SENT: "message.sent",
        Message.Status.DELIVERED: "message.delivered",
        Message.Status.FAILED: "message.failed",
        Message.Status.DEAD_LETTER: "message.dead_letter",
    }
    event_type = status_map.get(message.status)
    if event_type and message.project_id:
        from apps.webhooks.services.delivery import enqueue_event

        enqueue_event(
            project=message.project,
            event_type=event_type,
            payload=message_summary(message),
        )


def publish_control_command(command) -> None:
    broadcast_device(
        command.device_id,
        "command.control",
        {
            "command_id": str(command.id),
            "action": command.action,
            "params": command.params,
        },
    )


def handle_permission_changes(device: Device, previous_health: dict, new_health: dict) -> None:
    prev_perms = (previous_health or {}).get("permissions") or {}
    new_perms = (new_health or {}).get("permissions") or {}
    for key in ("sms", "phone"):
        was = bool(prev_perms.get(key, True))
        now = bool(new_perms.get(key, True))
        if was and not now:
            DeviceEvent.objects.create(
                device=device,
                type="permission.revoked",
                payload={"permission": key},
            )
            from apps.notifications.services.notify import notify

            notify(
                tenant=device.tenant,
                event="permission.revoked",
                severity="critical",
                title="Permission revoked",
                body=f"{device.name}: {key} permission revoked",
                meta={"device_id": str(device.id), "permission": key},
            )
