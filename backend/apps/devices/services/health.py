"""Device health score computation (Phase 8)."""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.devices.models import Device
from apps.messaging.models import Message


def _battery_factor(health: dict) -> float:
    battery = health.get("battery")
    if battery is None:
        return 0.7
    return max(0.0, min(1.0, float(battery) / 100.0))


# Qualitative labels used by the Android agent / mock_agent (CharField on heartbeat).
_SIGNAL_LABELS = {
    "excellent": 1.0,
    "great": 1.0,
    "strong": 1.0,
    "good": 0.75,
    "fair": 0.5,
    "moderate": 0.5,
    "average": 0.5,
    "ok": 0.5,
    "poor": 0.25,
    "weak": 0.25,
    "bad": 0.25,
    "none": 0.0,
    "unknown": 0.5,
    "no_signal": 0.0,
    "nosignal": 0.0,
}


def _signal_factor(health: dict) -> float:
    signal = health.get("signal")
    if signal is None or signal == "":
        return 0.7
    if isinstance(signal, str):
        label = signal.strip().lower().replace(" ", "_").replace("-", "_")
        if label in _SIGNAL_LABELS:
            return _SIGNAL_LABELS[label]
    try:
        # Accept 0–4 bars or 0–100 percent
        value = float(signal)
    except (TypeError, ValueError):
        return 0.7
    if value <= 4:
        return max(0.0, min(1.0, value / 4.0))
    return max(0.0, min(1.0, value / 100.0))


def _success_rate_24h(device: Device) -> float:
    since = timezone.now() - timedelta(hours=24)
    qs = Message.objects.filter(device=device, updated_at__gte=since).exclude(
        status__in=[
            Message.Status.QUEUED,
            Message.Status.SCHEDULED,
            Message.Status.ASSIGNED,
            Message.Status.SENDING,
            Message.Status.RETRYING,
            Message.Status.CANCELLED,
        ]
    )
    total = qs.count()
    if total == 0:
        return 0.9
    ok = qs.filter(
        status__in=[Message.Status.SENT, Message.Status.DELIVERED]
    ).count()
    return ok / total


def _queue_factor(device: Device) -> float:
    depth = Message.objects.filter(
        device=device,
        status__in=[
            Message.Status.QUEUED,
            Message.Status.ASSIGNED,
            Message.Status.SCHEDULED,
            Message.Status.RETRYING,
            Message.Status.SENDING,
        ],
    ).count()
    # 0 pending → 1.0; 50+ → ~0
    return max(0.0, min(1.0, 1.0 - (depth / 50.0)))


def _uptime_factor(device: Device) -> float:
    if device.status == Device.Status.ONLINE:
        return 1.0
    if device.status == Device.Status.BUSY:
        return 0.85
    if device.status == Device.Status.OFFLINE:
        return 0.2
    return 0.5


def compute_health_score(device: Device) -> int:
    """
    Weighted formula (clamped 0–100):
      0.25*battery + 0.25*signal + 0.20*success_24h + 0.15*queue + 0.15*uptime
    """
    health = device.health or {}
    score = (
        0.25 * _battery_factor(health)
        + 0.25 * _signal_factor(health)
        + 0.20 * _success_rate_24h(device)
        + 0.15 * _queue_factor(device)
        + 0.15 * _uptime_factor(device)
    )
    return int(max(0, min(100, round(score * 100))))


def refresh_health_score(device: Device, *, save: bool = True) -> int:
    score = compute_health_score(device)
    device.health_score = score
    if save:
        device.save(update_fields=["health_score", "updated_at"])
    return score
