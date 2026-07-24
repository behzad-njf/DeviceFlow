"""OTP / Marketing / General mode policies."""
from __future__ import annotations

import random
from datetime import timedelta

from django.utils import timezone

from apps.messaging.models import Message
from apps.routing.models import TenantRoutingConfig


# Lower priority number = pulled first by agent pending queue
MODE_PRIORITY = {
    Message.Mode.OTP: 10,
    Message.Mode.GENERAL: 100,
    Message.Mode.MARKETING: 500,
}


def priority_for_mode(mode: str) -> int:
    return MODE_PRIORITY.get(mode, MODE_PRIORITY[Message.Mode.GENERAL])


def queue_weight_for_mode(mode: str, config: TenantRoutingConfig) -> float:
    if mode == Message.Mode.OTP:
        return float(config.otp_queue_weight or 10)
    if mode == Message.Mode.MARKETING:
        return float(config.marketing_queue_weight or 1)
    return 5.0


def marketing_jitter_deadline(config: TenantRoutingConfig):
    """Return a future UTC datetime for marketing pacing, or None if no delay."""
    max_seconds = int(getattr(config, "marketing_jitter_max_seconds", 0) or 0)
    if max_seconds <= 0:
        return None
    delay = random.randint(1, max_seconds)
    return timezone.now() + timedelta(seconds=delay)


def prefer_strategy_for_mode(mode: str, strategy: str) -> str:
    """OTP prefers low-latency strategies unless already priority/weighted."""
    if mode != Message.Mode.OTP:
        return strategy
    if strategy in {
        TenantRoutingConfig.LBStrategy.LEAST_QUEUE,
        TenantRoutingConfig.LBStrategy.ROUND_ROBIN,
        TenantRoutingConfig.LBStrategy.RANDOM,
    }:
        return TenantRoutingConfig.LBStrategy.PRIORITY
    return strategy
