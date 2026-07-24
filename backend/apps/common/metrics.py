from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest
from django.http import HttpResponse
from django.views import View

from apps.devices.models import Device
from apps.messaging.models import Message


MESSAGES_ENQUEUED = Counter(
    "deviceflow_messages_enqueued_total",
    "Messages accepted into the outbound pipeline",
    ["mode"],
)
MESSAGES_SENT = Counter(
    "deviceflow_messages_sent_total",
    "Messages reported sent by agents",
)
MESSAGES_FAILED = Counter(
    "deviceflow_messages_failed_total",
    "Messages reported failed by agents",
)
AUTH_FAILURES = Counter(
    "deviceflow_auth_failures_total",
    "Authentication failures",
    ["kind"],
)
DEVICES_ONLINE = Gauge(
    "deviceflow_devices_online",
    "Online paired devices",
)
DEVICES_OFFLINE = Gauge(
    "deviceflow_devices_offline",
    "Offline paired devices",
)
QUEUE_DEPTH = Gauge(
    "deviceflow_queue_depth",
    "Pending outbound messages",
)


def refresh_gauges() -> None:
    DEVICES_ONLINE.set(
        Device.objects.filter(status=Device.Status.ONLINE)
        .exclude(device_token_hash="")
        .count()
    )
    DEVICES_OFFLINE.set(
        Device.objects.filter(status=Device.Status.OFFLINE)
        .exclude(device_token_hash="")
        .count()
    )
    QUEUE_DEPTH.set(
        Message.objects.filter(
            status__in=[
                Message.Status.QUEUED,
                Message.Status.ASSIGNED,
                Message.Status.SCHEDULED,
                Message.Status.RETRYING,
            ]
        ).count()
    )


class MetricsView(View):
    """Prometheus scrape endpoint (network-restricted in production)."""

    def get(self, request):
        refresh_gauges()
        return HttpResponse(generate_latest(), content_type=CONTENT_TYPE_LATEST)
