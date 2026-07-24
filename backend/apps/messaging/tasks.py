from celery import shared_task

from apps.messaging.services.bulk import process_campaign
from apps.messaging.services.exports import run_export
from apps.messaging.services.messages import MessageService
from apps.messaging.models import Message
from django.utils import timezone


@shared_task(name="messaging.promote_retries")
def promote_retries_task() -> int:
    return MessageService.promote_retries()


@shared_task(name="messaging.promote_scheduled")
def promote_scheduled_task() -> int:
    due = Message.objects.filter(
        status=Message.Status.SCHEDULED,
        scheduled_at__lte=timezone.now(),
    )
    count = 0
    for message in due.select_related("tenant", "project"):
        # Re-enqueue through routing by flipping to assigned via MessageService path
        message.status = Message.Status.QUEUED
        message.save(update_fields=["status", "updated_at"])
        try:
            # Assign device now
            from apps.routing.services.engine import route_message

            result = route_message(
                tenant=message.tenant,
                to_number=message.to_number,
                mode=message.mode,
                project=message.project,
            )
            if result.device is None:
                message.status = Message.Status.FAILED
                message.error_code = "NO_DEVICE_AVAILABLE"
                message.error_message = "No device when schedule fired"
                message.save()
            else:
                message.device = result.device
                message.sim_slot = result.sim_slot
                message.status = Message.Status.ASSIGNED
                message.save()
                from apps.realtime.events import publish_message_updated

                publish_message_updated(message)
            count += 1
        except Exception as exc:  # noqa: BLE001
            message.status = Message.Status.FAILED
            message.error_message = str(exc)[:500]
            message.save()
    return count


@shared_task(name="messaging.process_bulk_campaign")
def process_bulk_campaign(campaign_id: str) -> str:
    return process_campaign(campaign_id)


@shared_task(name="messaging.run_export_job")
def run_export_job(job_id: str) -> str:
    job = run_export(job_id)
    return job.status
