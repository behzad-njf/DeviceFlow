"""Notification matching, cooldown, and dispatch."""
from __future__ import annotations

import logging

from django.core.cache import cache
from django.utils import timezone

from apps.notifications.models import NotificationChannel, NotificationLog, NotificationRule
from apps.realtime.broadcast import broadcast_alert

logger = logging.getLogger(__name__)

DEFAULT_RULES = [
    {"event": "device.offline", "channels": ["inapp", "telegram", "discord", "email"], "cooldown_sec": 300},
    {"event": "device.online", "channels": ["inapp"], "cooldown_sec": 60},
    {"event": "permission.revoked", "channels": ["inapp", "telegram", "email"], "cooldown_sec": 60},
    {"event": "message.dead_letter", "channels": ["inapp", "email"], "cooldown_sec": 120},
    {"event": "agent.outdated", "channels": ["inapp"], "cooldown_sec": 3600},
    {"event": "anomaly.detected", "channels": ["inapp", "telegram", "email"], "cooldown_sec": 600},
]


def notify(
    *,
    tenant,
    event: str,
    severity: str = "info",
    title: str,
    body: str = "",
    meta: dict | None = None,
) -> list[NotificationLog]:
    """Match rules → cooldown → enqueue channel sends. Always fans in-app when selected."""
    from apps.notifications.tasks import deliver_notification

    rules = list(
        NotificationRule.objects.filter(tenant=tenant, enabled=True, event=event)
    )
    if not rules:
        # Fall back to defaults for known events so in-app still works via this path
        for default in DEFAULT_RULES:
            if default["event"] == event:
                rules = [
                    NotificationRule(
                        tenant=tenant,
                        name=f"default:{event}",
                        event=event,
                        channels=default["channels"],
                        cooldown_sec=default["cooldown_sec"],
                        enabled=True,
                    )
                ]
                break

    logs: list[NotificationLog] = []
    channels_wanted: set[str] = set()
    cooldown = 300
    for rule in rules:
        channels_wanted.update(rule.channels or [])
        cooldown = min(cooldown, int(rule.cooldown_sec or 300))

    if not channels_wanted:
        channels_wanted = {"inapp"}

    cooldown_key = f"notify:cd:{tenant.id}:{event}"
    if title:
        # Keep memcached-safe keys (no spaces)
        safe_title = "".join(ch if ch.isalnum() or ch in "-_." else "_" for ch in title)[:48]
        cooldown_key = f"{cooldown_key}:{safe_title}"
    if cache.get(cooldown_key):
        log = NotificationLog.objects.create(
            tenant=tenant,
            event=event,
            channel="*",
            severity=severity,
            title=title,
            body=body,
            status=NotificationLog.Status.SKIPPED,
            error="cooldown",
            meta=meta or {},
        )
        return [log]
    cache.set(cooldown_key, 1, timeout=cooldown)

    # Resolve configured channel backends
    channel_rows = {
        row.channel_type: row
        for row in NotificationChannel.objects.filter(tenant=tenant, enabled=True)
    }

    for channel in channels_wanted:
        if channel == "inapp":
            broadcast_alert(
                tenant.id, severity=severity, title=title, body=body, meta=meta
            )
            log = NotificationLog.objects.create(
                tenant=tenant,
                event=event,
                channel="inapp",
                severity=severity,
                title=title,
                body=body,
                status=NotificationLog.Status.SENT,
                meta=meta or {},
            )
            logs.append(log)
            continue

        row = channel_rows.get(channel)
        if row is None:
            continue
        log = NotificationLog.objects.create(
            tenant=tenant,
            event=event,
            channel=channel,
            severity=severity,
            title=title,
            body=body,
            status=NotificationLog.Status.PENDING,
            meta={**(meta or {}), "channel_id": str(row.id)},
        )
        logs.append(log)
        deliver_notification.delay(str(log.id))

    # Also notify plugins listening for alerts
    try:
        from apps.plugins.services.events import emit_plugin_event

        emit_plugin_event(
            tenant=tenant,
            event_type="alert",
            payload={"title": title, "body": body, "severity": severity, "event": event},
        )
    except Exception:  # noqa: BLE001
        logger.exception("plugin alert emit failed")

    return logs


def deliver_log(log: NotificationLog) -> NotificationLog:
    from apps.notifications.channels import backends

    channel = NotificationChannel.objects.filter(
        tenant=log.tenant, channel_type=log.channel, enabled=True
    ).first()
    if channel is None:
        log.status = NotificationLog.Status.FAILED
        log.error = "channel not configured"
        log.save(update_fields=["status", "error"])
        return log
    try:
        if log.channel == NotificationChannel.ChannelType.EMAIL:
            backends.send_email(config=channel.config, title=log.title, body=log.body)
        elif log.channel == NotificationChannel.ChannelType.TELEGRAM:
            backends.send_telegram(config=channel.config, title=log.title, body=log.body)
        elif log.channel == NotificationChannel.ChannelType.DISCORD:
            backends.send_discord(config=channel.config, title=log.title, body=log.body)
        else:
            raise ValueError(f"Unsupported channel {log.channel}")
        log.status = NotificationLog.Status.SENT
        log.error = ""
    except Exception as exc:  # noqa: BLE001
        log.status = NotificationLog.Status.FAILED
        log.error = str(exc)[:500]
        logger.exception("notification deliver failed")
    log.save(update_fields=["status", "error"])
    return log
