from django.db import transaction

from apps.devices.models import Device, DeviceEvent
from apps.messaging.models import Message, MessageAttempt
from apps.routing.models import TenantRoutingConfig
from apps.routing.services.engine import get_or_create_config, route_message


@transaction.atomic
def failover_device_messages(device: Device) -> int:
    """Re-route assigned/retrying messages away from an offline/unhealthy device."""
    config = get_or_create_config(device.tenant)
    if not config.ha_enabled:
        return 0

    qs = (
        Message.objects.select_for_update()
        .filter(
            device=device,
            status__in=[
                Message.Status.ASSIGNED,
                Message.Status.RETRYING,
                Message.Status.QUEUED,
            ],
        )
        .select_related("project")
    )
    moved = 0
    for message in qs:
        result = route_message(
            tenant=message.tenant,
            to_number=message.to_number,
            mode=message.mode,
            project=message.project,
            exclude_device_ids={device.id},
        )
        if result.device is None or result.device.id == device.id:
            continue
        message.device = result.device
        message.sim_slot = result.sim_slot
        message.status = Message.Status.ASSIGNED
        message.next_retry_at = None
        message.error_code = ""
        message.error_message = ""
        message.save()
        MessageAttempt.objects.create(
            message=message,
            device=result.device,
            result="failover",
            detail=f"HA moved from {device.name}",
        )
        DeviceEvent.objects.create(
            device=result.device,
            type="sms.failover",
            payload={"message_id": str(message.id), "from_device": str(device.id)},
        )
        from apps.realtime.events import publish_message_updated

        publish_message_updated(message)
        moved += 1
    return moved


def maybe_failover_on_failure(message: Message) -> Message | None:
    """On send failure, try another device when HA is enabled."""
    if message.device is None:
        return None
    config = get_or_create_config(message.tenant)
    if not config.ha_enabled:
        return None
    result = route_message(
        tenant=message.tenant,
        to_number=message.to_number,
        mode=message.mode,
        project=message.project,
        exclude_device_ids={message.device_id},
    )
    if result.device is None:
        return None
    message.device = result.device
    message.sim_slot = result.sim_slot
    message.status = Message.Status.ASSIGNED
    message.next_retry_at = None
    message.error_code = ""
    message.error_message = ""
    message.save()
    MessageAttempt.objects.create(
        message=message,
        device=result.device,
        result="ha_reroute",
        detail="Re-routed after failure",
    )
    from apps.realtime.events import publish_message_updated

    publish_message_updated(message)
    return message
