"""Anomaly detection for fleet failure / offline spikes."""
from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.common.features import feature_enabled
from apps.devices.models import Device
from apps.messaging.models import Message
from apps.notifications.services.notify import notify
from apps.routing.services import throttle
from apps.tenants.models import Tenant


def detect_tenant_anomalies(
    tenant, *, window_minutes: int = 60, notify_on_find: bool = True
) -> list[dict]:
    """
    Heuristic AI assist (no external LLM required):
    - Device failure rate >= 50% with >= 5 outcomes in throttle window
    - Tenant failed/sent ratio spike in last hour vs previous hour
    Returns list of anomaly dicts (also notifies when found).
    """
    if not feature_enabled(tenant, key="ai.anomaly_enabled", default=True):
        return []

    findings: list[dict] = []
    now = timezone.now()
    hour_ago = now - timedelta(minutes=window_minutes)
    two_hours_ago = now - timedelta(minutes=window_minutes * 2)

    devices = Device.objects.filter(tenant=tenant).exclude(
        status__in=[Device.Status.DISABLED, Device.Status.PENDING]
    )
    for device in devices:
        rate = throttle.failure_rate(device_id=str(device.id))
        if rate >= 0.5:
            findings.append(
                {
                    "type": "device_failure_spike",
                    "device_id": str(device.id),
                    "device_name": device.name,
                    "failure_rate": round(rate, 2),
                    "explanation": (
                        f"{device.name} has a {int(rate * 100)}% recent failure rate "
                        f"(adaptive window). Check signal, SIM quota, or operator blocks."
                    ),
                }
            )

    recent = Message.objects.filter(tenant=tenant, created_at__gte=hour_ago)
    previous = Message.objects.filter(
        tenant=tenant, created_at__gte=two_hours_ago, created_at__lt=hour_ago
    )
    recent_stats = recent.aggregate(
        failed=Count("id", filter=Q(status__in=[Message.Status.FAILED, Message.Status.DEAD_LETTER])),
        sent=Count(
            "id",
            filter=Q(status__in=[Message.Status.SENT, Message.Status.DELIVERED]),
        ),
    )
    prev_stats = previous.aggregate(
        failed=Count("id", filter=Q(status__in=[Message.Status.FAILED, Message.Status.DEAD_LETTER])),
        sent=Count(
            "id",
            filter=Q(status__in=[Message.Status.SENT, Message.Status.DELIVERED]),
        ),
    )
    r_total = (recent_stats["failed"] or 0) + (recent_stats["sent"] or 0)
    p_total = (prev_stats["failed"] or 0) + (prev_stats["sent"] or 0)
    if r_total >= 10:
        r_rate = (recent_stats["failed"] or 0) / r_total
        p_rate = (prev_stats["failed"] or 0) / p_total if p_total else 0
        if r_rate >= 0.35 and r_rate >= (p_rate + 0.2):
            findings.append(
                {
                    "type": "tenant_failure_spike",
                    "failure_rate": round(r_rate, 2),
                    "baseline_rate": round(p_rate, 2),
                    "explanation": (
                        f"Tenant failure rate rose to {int(r_rate * 100)}% in the last hour "
                        f"(was {int(p_rate * 100)}%). Review routing, rate limits, and device health."
                    ),
                }
            )

    if notify_on_find:
        for finding in findings:
            notify(
                tenant=tenant,
                event="anomaly.detected",
                severity="high",
                title=f"AI anomaly: {finding['type']}",
                body=finding["explanation"],
                meta=finding,
            )
    return findings


def run_anomaly_scan() -> int:
    total = 0
    for tenant in Tenant.objects.all():
        total += len(detect_tenant_anomalies(tenant, notify_on_find=True))
    return total
