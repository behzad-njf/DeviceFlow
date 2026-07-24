from django.core.cache import cache


def _incr(key: str, timeout: int) -> int:
    """Atomic-ish counter using cache add/incr."""
    if cache.add(key, 1, timeout=timeout):
        return 1
    try:
        return int(cache.incr(key))
    except ValueError:
        cache.set(key, 1, timeout=timeout)
        return 1


def check_and_consume(
    *,
    device_id: str,
    project_id: str | None,
    sim_id: str | None,
    limits: dict,
) -> tuple[bool, str | None]:
    """
    Returns (allowed, reason_if_blocked).
    limits keys: per_minute, per_hour, per_day, project_per_minute
    """
    checks = [
        (f"rl:dev:{device_id}:m", limits.get("per_minute", 50), 60, "DEVICE_RATE_LIMIT_MINUTE"),
        (f"rl:dev:{device_id}:h", limits.get("per_hour", 500), 3600, "DEVICE_RATE_LIMIT_HOUR"),
        (f"rl:dev:{device_id}:d", limits.get("per_day", 5000), 86400, "DEVICE_RATE_LIMIT_DAY"),
    ]
    if project_id:
        checks.append(
            (
                f"rl:proj:{project_id}:m",
                limits.get("project_per_minute", 200),
                60,
                "PROJECT_RATE_LIMIT_MINUTE",
            )
        )
    if sim_id:
        checks.append(
            (
                f"rl:sim:{sim_id}:m",
                limits.get("per_minute", 50),
                60,
                "SIM_RATE_LIMIT_MINUTE",
            )
        )

    # Peek then consume — approximate for Phase 4 (single-process / Redis incr).
    for key, limit, timeout, code in checks:
        current = cache.get(key) or 0
        if int(current) >= int(limit):
            return False, code

    for key, limit, timeout, _code in checks:
        _incr(key, timeout)
    return True, None


def has_headroom(*, device_id: str, limits: dict) -> bool:
    checks = [
        (f"rl:dev:{device_id}:m", limits.get("per_minute", 50)),
        (f"rl:dev:{device_id}:h", limits.get("per_hour", 500)),
        (f"rl:dev:{device_id}:d", limits.get("per_day", 5000)),
    ]
    for key, limit in checks:
        if int(cache.get(key) or 0) >= int(limit):
            return False
    return True
