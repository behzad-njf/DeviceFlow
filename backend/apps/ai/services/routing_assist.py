"""Routing suggestion assistant from historical operator/device outcomes."""
from __future__ import annotations

from datetime import timedelta

from django.db.models import Count, Q
from django.utils import timezone

from apps.common.features import feature_enabled
from apps.devices.models import Device
from apps.messaging.models import Message
from apps.routing.services.operators import resolve_operator


def suggest_routing_rules(*, tenant, hours: int = 24) -> list[dict]:
    """
    Propose RoutingRule-shaped suggestions (not persisted).
    Heuristic: for each destination operator with enough volume, prefer the
    device with the best sent/(sent+failed) ratio that has a matching SIM.
    """
    if not feature_enabled(tenant, key="ai.routing_suggestions", default=True):
        return []

    since = timezone.now() - timedelta(hours=hours)
    messages = Message.objects.filter(
        tenant=tenant,
        created_at__gte=since,
        device__isnull=False,
    ).select_related("device", "sim_slot")

    # operator -> device_id -> {sent, failed}
    stats: dict[str, dict[str, dict[str, int]]] = {}
    for msg in messages.iterator():
        op = (msg.meta or {}).get("routing", {}).get("operator") or resolve_operator(
            msg.to_number
        ) or "unknown"
        device_id = str(msg.device_id)
        bucket = stats.setdefault(op, {}).setdefault(
            device_id, {"sent": 0, "failed": 0, "name": msg.device.name}
        )
        if msg.status in {Message.Status.SENT, Message.Status.DELIVERED}:
            bucket["sent"] += 1
        elif msg.status in {Message.Status.FAILED, Message.Status.DEAD_LETTER}:
            bucket["failed"] += 1

    suggestions: list[dict] = []
    for operator, by_device in stats.items():
        if operator in {"", "unknown"}:
            continue
        ranked = []
        for device_id, row in by_device.items():
            total = row["sent"] + row["failed"]
            if total < 3:
                continue
            success = row["sent"] / total
            ranked.append((success, total, device_id, row["name"]))
        if not ranked:
            continue
        ranked.sort(key=lambda x: (-x[0], -x[1]))
        best = ranked[0]
        if best[0] < 0.6:
            continue
        # Prefix hint from operator table is soft; use operator match dimension
        suggestions.append(
            {
                "name": f"AI prefer {best[3]} for {operator}",
                "priority": 150,
                "match": {"operator": [operator]},
                "action": {
                    "type": "prefer_devices",
                    "device_ids": [best[2]],
                    "sim_operator": operator,
                },
                "confidence": round(best[0], 2),
                "sample_size": best[1],
                "rationale": (
                    f"{best[3]} delivered {int(best[0] * 100)}% success for {operator} "
                    f"over {best[1]} messages in the last {hours}h."
                ),
            }
        )
    return suggestions
