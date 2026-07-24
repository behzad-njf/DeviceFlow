from apps.devices.models import Device, DeviceCommand, DeviceEvent
from apps.realtime.broadcast import broadcast_tenant
from apps.realtime.events import publish_control_command, publish_device_updated

SECURITY_META_BOOL_KEYS = ("launcher_hidden", "ui_locked", "passcode_set")
SECURITY_ACTIONS = {
    "hide_launcher",
    "show_launcher",
    "lock_ui",
    "unlock_ui",
    "set_passcode",
    "clear_passcode",
    "set_dialer_code",
}


class CommandService:
    @staticmethod
    def enqueue(*, device: Device, action: str, params: dict | None = None, user=None) -> DeviceCommand:
        if action not in DeviceCommand.Action.values:
            raise ValueError("Unsupported command action")
        command = DeviceCommand.objects.create(
            device=device,
            action=action,
            params=params or {},
            created_by=user if getattr(user, "is_authenticated", False) else None,
        )
        DeviceEvent.objects.create(
            device=device,
            type="command.created",
            payload={
                "command_id": str(command.id),
                "action": action,
                "params": command.params,
            },
        )
        publish_control_command(command)
        return command

    @staticmethod
    def pending_for_device(device: Device, limit: int = 20) -> list[DeviceCommand]:
        return list(
            DeviceCommand.objects.filter(
                device=device, status=DeviceCommand.Status.PENDING
            ).order_by("created_at")[:limit]
        )

    @staticmethod
    def ack(*, command: DeviceCommand, status: str, result: dict | None = None) -> DeviceCommand:
        if status not in {"acked", "failed", "accepted", "rejected"}:
            raise ValueError("Invalid ack status")
        command.status = (
            DeviceCommand.Status.ACKED
            if status in {"acked", "accepted"}
            else DeviceCommand.Status.FAILED
        )
        command.result = result or {"status": status}
        command.save(update_fields=["status", "result", "updated_at"])
        if command.status == DeviceCommand.Status.ACKED:
            _apply_security_meta_from_ack(command)
        payload = {
            "command_id": str(command.id),
            "action": command.action,
            "status": command.status,
            "result": command.result,
            "device_id": str(command.device_id),
        }
        DeviceEvent.objects.create(
            device=command.device,
            type="command.acked",
            payload=payload,
        )
        broadcast_tenant(command.device.tenant_id, "command.acked", payload)
        # Reload so publish_device_updated includes freshly written security meta.
        command.device.refresh_from_db()
        publish_device_updated(command.device)
        return command


def _apply_security_meta_from_ack(command: DeviceCommand) -> None:
    """Persist launcher/lock flags from agent ack so the dashboard updates without waiting for heartbeat."""
    if command.action not in SECURITY_ACTIONS:
        return
    result = command.result or {}
    if not any(key in result for key in (*SECURITY_META_BOOL_KEYS, "dialer_code")):
        return
    device = command.device
    meta = dict(device.meta or {})
    changed = False
    for key in SECURITY_META_BOOL_KEYS:
        if key not in result:
            continue
        value = bool(result.get(key))
        if meta.get(key) != value:
            meta[key] = value
            changed = True
    if "dialer_code" in result:
        code = str(result.get("dialer_code") or "").strip()
        if code.isdigit() and 3 <= len(code) <= 8 and meta.get("dialer_code") != code:
            meta["dialer_code"] = code
            changed = True
    if not changed:
        return
    device.meta = meta
    device.save(update_fields=["meta", "updated_at"])
