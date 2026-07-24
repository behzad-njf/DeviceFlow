from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.devices.models import Device, DeviceEvent
from apps.devices.services.health import refresh_health_score
from apps.notifications.services.notify import notify
from apps.realtime.events import publish_device_updated
from apps.routing.services.ha import failover_device_messages


@shared_task(name="devices.mark_stale_devices_offline")
def mark_stale_devices_offline() -> int:
    cutoff = timezone.now() - timedelta(
        seconds=getattr(settings, "DEVICE_OFFLINE_AFTER_SECONDS", 45)
    )
    stale = Device.objects.filter(
        status=Device.Status.ONLINE,
        last_seen_at__lt=cutoff,
    )
    count = 0
    for device in stale:
        device.status = Device.Status.OFFLINE
        device.save(update_fields=["status", "updated_at"])
        DeviceEvent.objects.create(device=device, type="device.offline", payload={})
        notify(
            tenant=device.tenant,
            event="device.offline",
            severity="high",
            title="Device offline",
            body=f"{device.name} missed heartbeats",
            meta={"device_id": str(device.id)},
        )
        for link in device.project_links.select_related("project"):
            from apps.webhooks.services.delivery import enqueue_event

            enqueue_event(
                project=link.project,
                event_type="device.offline",
                payload={"device_id": str(device.id), "name": device.name},
            )
        moved = failover_device_messages(device)
        if moved:
            notify(
                tenant=device.tenant,
                event="device.offline",
                severity="info",
                title="HA failover",
                body=f"Re-routed {moved} message(s) away from {device.name}",
                meta={"device_id": str(device.id), "moved": moved},
            )
        publish_device_updated(device)
        count += 1
    return count


@shared_task(name="devices.refresh_health_scores")
def refresh_health_scores() -> int:
    count = 0
    for device in Device.objects.exclude(status=Device.Status.DISABLED):
        refresh_health_score(device, save=True)
        count += 1
    return count


@shared_task(name="devices.reset_sim_daily_sent")
def reset_sim_daily_sent() -> int:
    from apps.devices.models import SimSlot

    return SimSlot.objects.filter(daily_sent__gt=0).update(daily_sent=0)
