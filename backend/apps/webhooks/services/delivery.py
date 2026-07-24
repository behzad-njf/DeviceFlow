import hashlib
import hmac
import ipaddress
import json
import socket
from datetime import timedelta
from urllib.parse import urlparse

from django.db import transaction
from django.utils import timezone

from apps.webhooks.models import WebhookDelivery, WebhookEndpoint

RETRY_SECONDS = [30, 60, 300, 900, 3600]
MAX_ATTEMPTS = 5

ALL_EVENTS = [
    "message.queued",
    "message.assigned",
    "message.sent",
    "message.delivered",
    "message.failed",
    "message.dead_letter",
    "inbound.received",
    "device.offline",
    "device.online",
    "automation.triggered",
]


def sign_payload(*, secret: str, timestamp: str, body: bytes) -> str:
    digest = hmac.new(
        secret.encode("utf-8"),
        msg=f"{timestamp}.".encode("utf-8") + body,
        digestmod=hashlib.sha256,
    ).hexdigest()
    return f"sha256={digest}"


def is_safe_webhook_url(url: str, *, allow_private: bool = False) -> bool:
    """Basic SSRF guard: block obvious private/link-local hosts."""
    from django.conf import settings

    if allow_private or getattr(settings, "DEBUG", False):
        try:
            parsed = urlparse(url)
            return parsed.scheme in {"http", "https"} and bool(parsed.hostname)
        except Exception:
            return False
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = parsed.hostname
    if not host:
        return False
    if host in {"localhost", "metadata.google.internal"}:
        return False
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return False
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
        ):
            return False
    return True


@transaction.atomic
def enqueue_event(*, project, event_type: str, payload: dict) -> list[WebhookDelivery]:
    if project is None:
        return []
    endpoints = WebhookEndpoint.objects.filter(project=project, is_active=True)
    created = []
    for endpoint in endpoints:
        events = endpoint.events or []
        if events and event_type not in events and "*" not in events:
            continue
        delivery = WebhookDelivery.objects.create(
            endpoint=endpoint,
            event_type=event_type,
            payload={
                "id": None,  # filled after create
                "type": event_type,
                "created_at": timezone.now().isoformat(),
                "data": payload,
            },
            status=WebhookDelivery.Status.PENDING,
        )
        delivery.payload["id"] = str(delivery.id)
        delivery.save(update_fields=["payload"])
        created.append(delivery)
        from apps.webhooks.tasks import deliver_webhook

        deliver_webhook.delay(str(delivery.id))
    return created


def deliver_once(delivery: WebhookDelivery) -> WebhookDelivery:
    import urllib.error
    import urllib.request

    endpoint = delivery.endpoint
    body = json.dumps(delivery.payload, separators=(",", ":"), default=str).encode(
        "utf-8"
    )
    timestamp = str(int(timezone.now().timestamp()))
    signature = sign_payload(secret=endpoint.secret, timestamp=timestamp, body=body)
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "DeviceFlow-Webhooks/1.0",
        "X-DeviceFlow-Event": delivery.event_type,
        "X-DeviceFlow-Delivery": str(delivery.id),
        "X-DeviceFlow-Timestamp": timestamp,
        "X-DeviceFlow-Signature": signature,
    }

    if not is_safe_webhook_url(endpoint.url):
        delivery.attempts += 1
        delivery.status = WebhookDelivery.Status.FAILED
        delivery.response_code = 0
        delivery.response_body = "URL blocked by SSRF guard"
        delivery.next_retry_at = None
        delivery.save()
        endpoint.failure_count += 1
        endpoint.save(update_fields=["failure_count", "updated_at"])
        return delivery

    req = urllib.request.Request(
        endpoint.url, data=body, headers=headers, method="POST"
    )
    delivery.attempts += 1
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            delivery.response_code = resp.getcode()
            delivery.response_body = resp.read(2048).decode("utf-8", errors="replace")
            if 200 <= resp.getcode() < 300:
                delivery.status = WebhookDelivery.Status.SUCCESS
                delivery.next_retry_at = None
                endpoint.failure_count = 0
                endpoint.save(update_fields=["failure_count", "updated_at"])
            else:
                _schedule_retry(delivery, endpoint)
    except urllib.error.HTTPError as exc:
        delivery.response_code = exc.code
        delivery.response_body = exc.read(2048).decode("utf-8", errors="replace")
        _schedule_retry(delivery, endpoint)
    except Exception as exc:  # noqa: BLE001 — network errors
        delivery.response_code = 0
        delivery.response_body = str(exc)[:2000]
        _schedule_retry(delivery, endpoint)

    delivery.save()
    return delivery


def _schedule_retry(delivery: WebhookDelivery, endpoint: WebhookEndpoint) -> None:
    endpoint.failure_count += 1
    endpoint.save(update_fields=["failure_count", "updated_at"])
    if delivery.attempts >= MAX_ATTEMPTS:
        delivery.status = WebhookDelivery.Status.FAILED
        delivery.next_retry_at = None
        return
    delay = RETRY_SECONDS[min(delivery.attempts - 1, len(RETRY_SECONDS) - 1)]
    delivery.status = WebhookDelivery.Status.RETRYING
    delivery.next_retry_at = timezone.now() + timedelta(seconds=delay)


def redeliver(delivery: WebhookDelivery) -> WebhookDelivery:
    delivery.status = WebhookDelivery.Status.PENDING
    delivery.next_retry_at = None
    delivery.save(update_fields=["status", "next_retry_at", "updated_at"])
    from apps.webhooks.tasks import deliver_webhook

    deliver_webhook.delay(str(delivery.id))
    return delivery
