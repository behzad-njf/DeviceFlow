from celery import shared_task

from apps.notifications.models import NotificationLog
from apps.notifications.services.notify import deliver_log


@shared_task(name="notifications.deliver_notification")
def deliver_notification(log_id: str) -> str:
    log = NotificationLog.objects.filter(id=log_id).select_related("tenant").first()
    if not log:
        return "missing"
    deliver_log(log)
    return log.status
