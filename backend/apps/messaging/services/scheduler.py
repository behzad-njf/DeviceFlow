"""Quiet hours and schedule helpers."""
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.utils import timezone


def _parse_hhmm(value: str) -> tuple[int, int]:
    parts = value.split(":")
    return int(parts[0]), int(parts[1])


def is_within_quiet_window(now_local: datetime, windows: list[dict]) -> bool:
    """Return True if current local time is inside an allowed window."""
    minutes = now_local.hour * 60 + now_local.minute
    for window in windows or []:
        start_h, start_m = _parse_hhmm(window.get("start", "00:00"))
        end_h, end_m = _parse_hhmm(window.get("end", "23:59"))
        start = start_h * 60 + start_m
        end = end_h * 60 + end_m
        if start <= end:
            if start <= minutes < end:
                return True
        else:
            if minutes >= start or minutes < end:
                return True
    return not windows


def next_allowed_datetime(*, project, from_dt=None, mode: str = "general"):
    """
    If quiet hours apply, return the next allowed UTC datetime.
    Returns None if sending is allowed now.
    Raises ValueError if action=reject.
    """
    if project is None:
        return None
    settings = project.settings or {}
    quiet = settings.get("quiet_hours") or {}
    if not quiet:
        return None
    if mode == "otp":
        return None

    tz_name = quiet.get("timezone") or "UTC"
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("UTC")

    now = from_dt or timezone.now()
    if timezone.is_naive(now):
        now = timezone.make_aware(now, ZoneInfo("UTC"))
    local = now.astimezone(tz)
    days = quiet.get("days")
    windows = quiet.get("windows_allowed") or [{"start": "08:00", "end": "20:00"}]
    action = quiet.get("action") or "defer"

    if is_within_quiet_window(local, windows) and (
        days is None or local.weekday() in days
    ):
        return None

    if action == "reject":
        raise ValueError("Send rejected by project quiet hours")

    for day_offset in range(0, 8):
        candidate_day = (local + timedelta(days=day_offset)).date()
        if days is not None and candidate_day.weekday() not in days:
            continue
        for window in windows:
            start_h, start_m = _parse_hhmm(window.get("start", "08:00"))
            candidate = datetime(
                candidate_day.year,
                candidate_day.month,
                candidate_day.day,
                start_h,
                start_m,
                tzinfo=tz,
            )
            if candidate > local:
                return candidate.astimezone(ZoneInfo("UTC"))
    return now + timedelta(hours=1)
