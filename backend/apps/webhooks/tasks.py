from celery import shared_task
from django.utils import timezone

from apps.webhooks.models import WebhookDelivery
from apps.webhooks.services.delivery import deliver_once


@shared_task(name="webhooks.deliver_webhook")
def deliver_webhook(delivery_id: str) -> str:
    delivery = (
        WebhookDelivery.objects.select_related("endpoint", "endpoint__project")
        .filter(id=delivery_id)
        .first()
    )
    if delivery is None:
        return "missing"
    deliver_once(delivery)
    return delivery.status


@shared_task(name="webhooks.retry_due_deliveries")
def retry_due_deliveries() -> int:
    due = WebhookDelivery.objects.filter(
        status=WebhookDelivery.Status.RETRYING,
        next_retry_at__lte=timezone.now(),
    )[:100]
    count = 0
    for delivery in due:
        deliver_webhook.delay(str(delivery.id))
        count += 1
    return count
