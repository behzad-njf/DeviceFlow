from datetime import timedelta

from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.devices.models import Device
from apps.messaging.models import InboundMessage, Message
from apps.realtime.events import queue_summary_for_device
from apps.routing.services.operators import resolve_operator


class AnalyticsOverviewView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "analytics.read"

    def get(self, request):
        tenant = request.tenant
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=6)

        messages = Message.objects.filter(tenant=tenant)
        devices = Device.objects.filter(tenant=tenant).exclude(status=Device.Status.DISABLED)

        sent_today = messages.filter(
            status__in=[Message.Status.SENT, Message.Status.DELIVERED],
            sent_at__gte=today_start,
        ).count()
        failed_today = messages.filter(
            status__in=[Message.Status.FAILED, Message.Status.DEAD_LETTER],
            failed_at__gte=today_start,
        ).count()
        sent_7d = messages.filter(
            status__in=[Message.Status.SENT, Message.Status.DELIVERED],
            sent_at__gte=week_start,
        ).count()
        inbound_today = InboundMessage.objects.filter(
            tenant=tenant, received_at__gte=today_start
        ).count()

        queue_pending = messages.filter(
            status__in=[
                Message.Status.QUEUED,
                Message.Status.ASSIGNED,
                Message.Status.SCHEDULED,
                Message.Status.RETRYING,
                Message.Status.SENDING,
            ]
        ).count()

        online = devices.filter(status=Device.Status.ONLINE).count()
        offline = devices.filter(status=Device.Status.OFFLINE).count()
        busy = devices.filter(status=Device.Status.BUSY).count()
        pending_pair = devices.filter(status=Device.Status.PENDING).count()

        by_day = (
            messages.filter(
                status__in=[Message.Status.SENT, Message.Status.DELIVERED],
                sent_at__gte=week_start,
            )
            .annotate(day=TruncDate("sent_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )

        latency = messages.filter(
            latency_ms__isnull=False,
            sent_at__gte=today_start,
        ).aggregate(avg=Avg("latency_ms"))

        by_mode = (
            messages.filter(
                status__in=[Message.Status.SENT, Message.Status.DELIVERED],
                sent_at__gte=today_start,
            )
            .values("mode")
            .annotate(count=Count("id"))
        )

        return Response(
            {
                "devices": {
                    "online": online,
                    "offline": offline,
                    "busy": busy,
                    "pending": pending_pair,
                    "total": devices.count(),
                },
                "messages": {
                    "sent_today": sent_today,
                    "failed_today": failed_today,
                    "sent_7d": sent_7d,
                    "queue_depth": queue_pending,
                    "inbound_today": inbound_today,
                    "avg_latency_ms_today": latency["avg"],
                },
                "by_mode_today": {row["mode"]: row["count"] for row in by_mode},
                "series_7d": [
                    {
                        "day": row["day"].isoformat() if row["day"] else None,
                        "sent": row["count"],
                    }
                    for row in by_day
                ],
            }
        )


class AnalyticsTimeseriesView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "analytics.read"

    def get(self, request):
        tenant = request.tenant
        metric = request.query_params.get("metric", "sent")
        interval = request.query_params.get("interval", "hour")
        hours = min(int(request.query_params.get("hours", 24)), 168)
        since = timezone.now() - timedelta(hours=hours)

        trunc = TruncHour if interval == "hour" else TruncDate
        field = "sent_at"
        status_filter = Q(status__in=[Message.Status.SENT, Message.Status.DELIVERED])
        if metric == "failed":
            field = "failed_at"
            status_filter = Q(
                status__in=[Message.Status.FAILED, Message.Status.DEAD_LETTER]
            )

        qs = (
            Message.objects.filter(tenant=tenant, **{f"{field}__gte": since})
            .filter(status_filter)
            .annotate(bucket=trunc(field))
            .values("bucket")
            .annotate(count=Count("id"))
            .order_by("bucket")
        )
        return Response(
            {
                "metric": metric,
                "interval": interval,
                "points": [
                    {
                        "t": row["bucket"].isoformat() if row["bucket"] else None,
                        "v": row["count"],
                    }
                    for row in qs
                ],
            }
        )


class AnalyticsOperatorsView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "analytics.read"

    def get(self, request):
        tenant = request.tenant
        hours = min(int(request.query_params.get("hours", 24)), 168)
        since = timezone.now() - timedelta(hours=hours)
        messages = Message.objects.filter(
            tenant=tenant,
            sent_at__gte=since,
            status__in=[Message.Status.SENT, Message.Status.DELIVERED],
        ).only("to_number", "meta", "latency_ms")

        stats: dict[str, dict] = {}
        for msg in messages:
            op = (msg.meta or {}).get("routing", {}).get("operator") or resolve_operator(
                msg.to_number
            ) or "unknown"
            bucket = stats.setdefault(
                op, {"operator": op, "sent": 0, "latency_sum": 0, "latency_n": 0}
            )
            bucket["sent"] += 1
            if msg.latency_ms is not None:
                bucket["latency_sum"] += msg.latency_ms
                bucket["latency_n"] += 1

        results = []
        for op, row in sorted(stats.items(), key=lambda x: -x[1]["sent"]):
            avg = (
                row["latency_sum"] / row["latency_n"] if row["latency_n"] else None
            )
            results.append(
                {
                    "operator": op,
                    "sent": row["sent"],
                    "avg_latency_ms": avg,
                }
            )
        return Response({"results": results})


class AnalyticsDevicesView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "analytics.read"

    def get(self, request):
        tenant = request.tenant
        hours = min(int(request.query_params.get("hours", 24)), 168)
        since = timezone.now() - timedelta(hours=hours)
        devices = Device.objects.filter(tenant=tenant).exclude(
            status=Device.Status.DISABLED
        )
        results = []
        for device in devices:
            sent = Message.objects.filter(
                device=device,
                sent_at__gte=since,
                status__in=[Message.Status.SENT, Message.Status.DELIVERED],
            ).count()
            failed = Message.objects.filter(
                device=device,
                failed_at__gte=since,
                status__in=[Message.Status.FAILED, Message.Status.DEAD_LETTER],
            ).count()
            latency = Message.objects.filter(
                device=device, latency_ms__isnull=False, sent_at__gte=since
            ).aggregate(avg=Avg("latency_ms"))
            results.append(
                {
                    "device_id": str(device.id),
                    "name": device.name,
                    "status": device.status,
                    "health_score": device.health_score,
                    "sent": sent,
                    "failed": failed,
                    "avg_latency_ms": latency["avg"],
                    "lat": (device.meta or {}).get("lat"),
                    "lng": (device.meta or {}).get("lng"),
                    "city": (device.meta or {}).get("city"),
                }
            )
        results.sort(key=lambda r: (-r["sent"], r["name"]))
        return Response({"results": results})


class AnalyticsLatencyView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "analytics.read"

    def get(self, request):
        tenant = request.tenant
        hours = min(int(request.query_params.get("hours", 24)), 168)
        since = timezone.now() - timedelta(hours=hours)
        by_mode = (
            Message.objects.filter(
                tenant=tenant,
                latency_ms__isnull=False,
                sent_at__gte=since,
            )
            .values("mode")
            .annotate(avg=Avg("latency_ms"), count=Count("id"))
            .order_by("mode")
        )
        return Response(
            {
                "by_mode": [
                    {
                        "mode": row["mode"],
                        "avg_latency_ms": row["avg"],
                        "count": row["count"],
                    }
                    for row in by_mode
                ]
            }
        )


class DeviceMapView(APIView):
    """Optional geo map — returns devices that have lat/lng in meta."""

    permission_classes = [RequirePermission]
    required_permission = "devices.read"

    def get(self, request):
        devices = Device.objects.filter(tenant=request.tenant).exclude(
            status=Device.Status.DISABLED
        )
        points = []
        for device in devices:
            meta = device.meta or {}
            lat, lng = meta.get("lat"), meta.get("lng")
            if lat is None or lng is None:
                continue
            points.append(
                {
                    "device_id": str(device.id),
                    "name": device.name,
                    "status": device.status,
                    "health_score": device.health_score,
                    "lat": float(lat),
                    "lng": float(lng),
                    "city": meta.get("city") or "",
                    "accuracy_m": meta.get("accuracy_m"),
                    "last_seen_at": (
                        device.last_seen_at.isoformat() if device.last_seen_at else None
                    ),
                    "location_received_at": meta.get("location_received_at") or "",
                }
            )
        return Response({"results": points})


class QueuesSummaryView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "queues.read"

    def get(self, request):
        devices = Device.objects.filter(tenant=request.tenant).exclude(
            status__in=[Device.Status.DISABLED, Device.Status.PENDING]
        )
        results = []
        totals = {"pending": 0, "sending": 0, "failed": 0, "dead_letter": 0}
        for device in devices:
            summary = queue_summary_for_device(device)
            summary["name"] = device.name
            summary["status"] = device.status
            summary["health_score"] = device.health_score
            results.append(summary)
            for key in totals:
                totals[key] += summary[key]
        return Response({"totals": totals, "results": results})
