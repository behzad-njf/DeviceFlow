import random

from django.core.cache import cache

from apps.devices.models import Device
from apps.messaging.models import Message
from apps.projects.models import ProjectDevice
from apps.routing.models import TenantRoutingConfig


def _queue_depth(device: Device, mode: str | None = None) -> int:
    qs = Message.objects.filter(
        device=device,
        status__in=[
            Message.Status.QUEUED,
            Message.Status.ASSIGNED,
            Message.Status.SCHEDULED,
            Message.Status.RETRYING,
            Message.Status.SENDING,
        ],
    )
    if mode:
        qs = qs.filter(mode=mode)
    return qs.count()


def _priority_map(project) -> dict:
    if project is None:
        return {}
    return {
        str(row.device_id): row.priority
        for row in ProjectDevice.objects.filter(project=project)
    }


def select_device(
    *,
    candidates: list[Device],
    strategy: str,
    tenant_id,
    project=None,
    mode: str | None = None,
    mode_weight: float = 1.0,
) -> Device | None:
    if not candidates:
        return None
    strategy = strategy or TenantRoutingConfig.LBStrategy.LEAST_QUEUE
    priorities = _priority_map(project)
    weight = max(float(mode_weight or 1.0), 0.1)

    if strategy == TenantRoutingConfig.LBStrategy.RANDOM:
        return random.choice(candidates)

    if strategy == TenantRoutingConfig.LBStrategy.ROUND_ROBIN:
        key = f"rr:{tenant_id}:{getattr(project, 'id', 'none')}:{mode or 'any'}"
        idx = int(cache.get(key) or 0) % len(candidates)
        cache.set(key, idx + 1, timeout=86400)
        ordered = sorted(candidates, key=lambda d: d.name)
        return ordered[idx % len(ordered)]

    if strategy == TenantRoutingConfig.LBStrategy.PRIORITY:
        return sorted(
            candidates,
            key=lambda d: (
                -priorities.get(str(d.id), 100),
                _queue_depth(d, mode=mode),
                d.name,
            ),
        )[0]

    if strategy == TenantRoutingConfig.LBStrategy.WEIGHTED:
        scored = []
        for device in candidates:
            depth = max(_queue_depth(device, mode=mode), 1)
            score = (max(device.health_score, 1) * weight) / depth
            scored.append((score, device))
        scored.sort(key=lambda item: (-item[0], item[1].name))
        return scored[0][1]

    # least_queue — mode-specific depth so marketing backlog does not inflate OTP wait
    return sorted(candidates, key=lambda d: (_queue_depth(d, mode=mode), d.name))[0]
