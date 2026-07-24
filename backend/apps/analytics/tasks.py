"""Analytics rollup tasks."""
from datetime import timedelta

from celery import shared_task
from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncHour
from django.utils import timezone

from apps.analytics.models import HourlyStat
from apps.messaging.models import InboundMessage, Message
from apps.tenants.models import Tenant


@shared_task(name="analytics.rollup_hourly")
def rollup_hourly(hours_back: int = 2) -> int:
    """Aggregate message stats into HourlyStat rows for the last N hours."""
    now = timezone.now().replace(minute=0, second=0, microsecond=0)
    created = 0
    for offset in range(1, hours_back + 1):
        hour_start = now - timedelta(hours=offset)
        hour_end = hour_start + timedelta(hours=1)
        for tenant in Tenant.objects.all():
            created += _rollup_tenant_hour(tenant, hour_start, hour_end)
    return created


def _rollup_tenant_hour(tenant, hour_start, hour_end) -> int:
    rows = (
        Message.objects.filter(
            tenant=tenant, created_at__gte=hour_start, created_at__lt=hour_end
        )
        .values("project_id", "device_id", "mode")
        .annotate(
            sent=Count(
                "id",
                filter=Q(
                    status__in=[Message.Status.SENT, Message.Status.DELIVERED],
                    sent_at__gte=hour_start,
                    sent_at__lt=hour_end,
                ),
            ),
            failed=Count(
                "id",
                filter=Q(
                    status__in=[Message.Status.FAILED, Message.Status.DEAD_LETTER],
                    failed_at__gte=hour_start,
                    failed_at__lt=hour_end,
                ),
            ),
            delivered=Count(
                "id",
                filter=Q(
                    status=Message.Status.DELIVERED,
                    delivered_at__gte=hour_start,
                    delivered_at__lt=hour_end,
                ),
            ),
            latency_sum=Sum("latency_ms"),
            latency_count=Count("latency_ms"),
        )
    )
    by_operator = Message.objects.filter(
        tenant=tenant,
        sent_at__gte=hour_start,
        sent_at__lt=hour_end,
        status__in=[Message.Status.SENT, Message.Status.DELIVERED],
    )
    operator_counts: dict[str, int] = {}
    for msg in by_operator.only("meta"):
        meta = msg.meta or {}
        op = (meta.get("routing") or {}).get("operator") or ""
        if op:
            operator_counts[op] = operator_counts.get(op, 0) + 1

    inbound = InboundMessage.objects.filter(
        tenant=tenant, received_at__gte=hour_start, received_at__lt=hour_end
    ).count()

    created = 0
    row_list = list(rows)
    if not row_list and inbound:
        _, was_created = HourlyStat.objects.update_or_create(
            tenant=tenant,
            project=None,
            device=None,
            hour=hour_start,
            operator="",
            mode="",
            defaults={
                "sent": 0,
                "failed": 0,
                "delivered": 0,
                "inbound": inbound,
                "latency_sum_ms": 0,
                "latency_count": 0,
            },
        )
        return 1 if was_created else 0

    for row in row_list:
        _, was_created = HourlyStat.objects.update_or_create(
            tenant=tenant,
            project_id=row["project_id"],
            device_id=row["device_id"],
            hour=hour_start,
            operator="",
            mode=row["mode"] or "",
            defaults={
                "sent": row["sent"],
                "failed": row["failed"],
                "delivered": row["delivered"],
                "inbound": 0,
                "latency_sum_ms": int(row["latency_sum"] or 0),
                "latency_count": int(row["latency_count"] or 0),
            },
        )
        if was_created:
            created += 1

    for op, cnt in operator_counts.items():
        HourlyStat.objects.update_or_create(
            tenant=tenant,
            project=None,
            device=None,
            hour=hour_start,
            operator=op,
            mode="",
            defaults={
                "sent": cnt,
                "failed": 0,
                "delivered": 0,
                "inbound": 0,
                "latency_sum_ms": 0,
                "latency_count": 0,
            },
        )
    return created
