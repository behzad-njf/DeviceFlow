from datetime import timedelta
import time

from django.db import OperationalError, transaction
from django.utils import timezone

from apps.common.crypto import (
    generate_device_token,
    generate_pairing_code,
    hash_secret,
)
from apps.devices.models import Device, DeviceEvent, SimSlot
from apps.devices.services.capabilities import (
    DEFAULT_CAPABILITIES,
    normalize_capabilities,
)
from apps.realtime.events import (
    handle_permission_changes,
    publish_device_updated,
)


def _retry_on_db_lock(fn, *, attempts: int = 5, delay: float = 0.05):
    """SQLite can briefly lock under concurrent heartbeat/command writes."""
    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except OperationalError as exc:
            last_exc = exc
            if "locked" not in str(exc).lower() or i == attempts - 1:
                raise
            time.sleep(delay * (2**i))
    if last_exc:
        raise last_exc
    return None


class DeviceService:
    @staticmethod
    @transaction.atomic
    def create_pairing(*, tenant, name: str, ttl_minutes: int = 15) -> tuple[Device, str]:
        code = generate_pairing_code()
        device = Device.objects.create(
            tenant=tenant,
            name=name or f"Device-{generate_pairing_code(4)}",
            status=Device.Status.PENDING,
            pairing_code_hash=hash_secret(code),
            pairing_code_expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
            capabilities=list(DEFAULT_CAPABILITIES),
        )
        DeviceEvent.objects.create(
            device=device,
            type="pairing.created",
            payload={"expires_at": device.pairing_code_expires_at.isoformat()},
        )
        return device, code

    @staticmethod
    @transaction.atomic
    def pair_device(*, code: str, device_info: dict) -> tuple[Device, str]:
        code_hash = hash_secret(code.upper().strip())
        device = (
            Device.objects.select_for_update()
            .filter(pairing_code_hash=code_hash, status=Device.Status.PENDING)
            .first()
        )
        if device is None:
            raise ValueError("Invalid or already used pairing code")
        if (
            device.pairing_code_expires_at
            and device.pairing_code_expires_at < timezone.now()
        ):
            raise ValueError("Pairing code expired")

        token = generate_device_token()
        device.device_token_hash = hash_secret(token)
        device.pairing_code_hash = None
        device.pairing_code_expires_at = None
        device.status = Device.Status.ONLINE
        device.last_seen_at = timezone.now()
        device.agent_version = str(device_info.get("agent_version") or "")
        device.capabilities = normalize_capabilities(
            device_info.get("capabilities") or DEFAULT_CAPABILITIES
        )
        device.meta = {
            **device.meta,
            "model": device_info.get("model"),
            "android_version": device_info.get("android_version"),
            "manufacturer": device_info.get("manufacturer"),
        }
        device.save()

        sims = device_info.get("sims") or []
        for sim in sims:
            slot_index = int(sim.get("slot_index") or sim.get("slot") or 1)
            SimSlot.objects.update_or_create(
                device=device,
                slot_index=slot_index,
                defaults={
                    "subscription_id": str(sim.get("subscription_id") or ""),
                    "operator": str(sim.get("operator") or ""),
                    "phone_number": str(sim.get("phone_number") or sim.get("number") or ""),
                    "iccid": str(sim.get("iccid") or ""),
                    "is_active": True,
                },
            )

        DeviceEvent.objects.create(
            device=device,
            type="device.paired",
            payload={"agent_version": device.agent_version},
        )
        publish_device_updated(device)
        return device, token

    @staticmethod
    def ingest_heartbeat(*, device: Device, payload: dict) -> Device:
        return _retry_on_db_lock(lambda: DeviceService._ingest_heartbeat(device=device, payload=payload))

    @staticmethod
    def _ingest_heartbeat(*, device: Device, payload: dict) -> Device:
        previous_health = dict(device.health or {})
        sims = payload.get("sims") or []
        for sim in sims:
            slot_index = int(sim.get("slot_index") or sim.get("slot") or 1)
            SimSlot.objects.update_or_create(
                device=device,
                slot_index=slot_index,
                defaults={
                    "subscription_id": str(sim.get("subscription_id") or ""),
                    "operator": str(sim.get("operator") or ""),
                    "phone_number": str(
                        sim.get("phone_number") or sim.get("number") or ""
                    ),
                    "iccid": str(sim.get("iccid") or ""),
                    "is_active": bool(sim.get("is_active", True)),
                },
            )

        health = {
            "battery": payload.get("battery"),
            "charging": payload.get("charging"),
            "signal": payload.get("signal"),
            "network": payload.get("network"),
            "queue_size": payload.get("queue_size"),
            "permissions": payload.get("permissions") or {},
            "storage_free": payload.get("storage_free"),
        }
        was_offline = device.status == Device.Status.OFFLINE
        device.mark_seen(
            health=health,
            agent_version=str(payload.get("agent_version") or device.agent_version),
            capabilities=payload.get("capabilities"),
        )
        _apply_location_from_heartbeat(device, payload)
        _apply_security_from_heartbeat(device, payload)
        handle_permission_changes(device, previous_health, health)
        if was_offline:
            DeviceEvent.objects.create(device=device, type="device.online", payload={})
            from apps.notifications.services.notify import notify

            notify(
                tenant=device.tenant,
                event="device.online",
                severity="info",
                title="Device online",
                body=f"{device.name} is back online",
                meta={"device_id": str(device.id)},
            )
            for link in device.project_links.select_related("project"):
                from apps.webhooks.services.delivery import enqueue_event

                enqueue_event(
                    project=link.project,
                    event_type="device.online",
                    payload={"device_id": str(device.id), "name": device.name},
                )
        publish_device_updated(device)
        return device


def _apply_location_from_heartbeat(device: Device, payload: dict) -> None:
    """Persist GPS from agent heartbeat into device.meta for the map."""
    lat = payload.get("lat")
    lng = payload.get("lng")
    if lat is None or lng is None:
        return
    try:
        lat_f = float(lat)
        lng_f = float(lng)
    except (TypeError, ValueError):
        return
    if not (-90.0 <= lat_f <= 90.0 and -180.0 <= lng_f <= 180.0):
        return

    meta = dict(device.meta or {})
    meta["lat"] = lat_f
    meta["lng"] = lng_f
    accuracy = payload.get("accuracy_m")
    if accuracy is not None:
        try:
            meta["accuracy_m"] = float(accuracy)
        except (TypeError, ValueError):
            pass
    updated_ms = payload.get("location_updated_at_ms")
    if updated_ms is not None:
        try:
            meta["location_updated_at_ms"] = int(updated_ms)
        except (TypeError, ValueError):
            pass
    meta["location_received_at"] = timezone.now().isoformat()
    device.meta = meta
    device.save(update_fields=["meta", "updated_at"])


def _apply_security_from_heartbeat(device: Device, payload: dict) -> None:
    """Persist launcher/passcode UI state from agent heartbeat into device.meta."""
    bool_keys = ("launcher_hidden", "ui_locked", "passcode_set")
    if not any(k in payload for k in (*bool_keys, "dialer_code")):
        return
    meta = dict(device.meta or {})
    changed = False
    for key in bool_keys:
        if key not in payload:
            continue
        value = bool(payload.get(key))
        if meta.get(key) != value:
            meta[key] = value
            changed = True
    if "dialer_code" in payload:
        code = str(payload.get("dialer_code") or "").strip()
        if code.isdigit() and 3 <= len(code) <= 8 and meta.get("dialer_code") != code:
            meta["dialer_code"] = code
            changed = True
    if not changed:
        return
    device.meta = meta
    device.save(update_fields=["meta", "updated_at"])
