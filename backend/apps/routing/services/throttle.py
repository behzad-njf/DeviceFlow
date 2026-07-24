"""Spam-risk / failure-rate adaptive rate limiting."""
from __future__ import annotations

from django.core.cache import cache


WINDOW_SECONDS = 900  # 15 minutes


def _keys(device_id: str) -> tuple[str, str]:
    return f"throttle:ok:{device_id}", f"throttle:fail:{device_id}"


def record_outcome(*, device_id: str, success: bool) -> None:
    ok_key, fail_key = _keys(device_id)
    key = ok_key if success else fail_key
    if cache.add(key, 1, timeout=WINDOW_SECONDS):
        return
    try:
        cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=WINDOW_SECONDS)


def failure_rate(*, device_id: str) -> float:
    ok_key, fail_key = _keys(device_id)
    ok = int(cache.get(ok_key) or 0)
    fail = int(cache.get(fail_key) or 0)
    total = ok + fail
    if total < 5:
        return 0.0
    return fail / total


def adaptive_factor(
    *,
    device_id: str,
    enabled: bool = True,
    threshold: float = 0.3,
) -> float:
    """
    Returns a multiplier applied to rate limits (0.25–1.0).
    High recent failure rate → lower effective throughput (spam-risk adaptation).
    """
    if not enabled:
        return 1.0
    rate = failure_rate(device_id=device_id)
    if rate < threshold:
        return 1.0
    # Linear scale from threshold→1.0 failure → factor 1.0→0.25
    excess = min(1.0, (rate - threshold) / max(1e-6, 1.0 - threshold))
    return max(0.25, 1.0 - (0.75 * excess))


def apply_adaptive_limits(
    *,
    device_id: str,
    limits: dict,
    enabled: bool = True,
    threshold: float = 0.3,
) -> dict:
    factor = adaptive_factor(
        device_id=device_id, enabled=enabled, threshold=threshold
    )
    if factor >= 0.999:
        return limits
    scaled = dict(limits)
    for key in ("per_minute", "per_hour", "per_day"):
        if key in scaled and scaled[key]:
            scaled[key] = max(1, int(int(scaled[key]) * factor))
    return scaled
