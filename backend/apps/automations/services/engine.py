"""Automation rule evaluation."""
from __future__ import annotations

import json
import logging
import urllib.request

from apps.automations.models import AutomationRule

logger = logging.getLogger(__name__)


def _matches(rule: AutomationRule, *, event: str, body: str = "", meta: dict | None = None) -> bool:
    match = rule.match or {}
    expected_event = match.get("event") or "inbound.received"
    if expected_event != event and expected_event != "*":
        return False
    if match.get("body_contains"):
        if str(match["body_contains"]).lower() not in (body or "").lower():
            return False
    if match.get("body_exact") is not None:
        if (body or "").strip() != str(match["body_exact"]).strip():
            return False
    if match.get("body_starts_with"):
        if not (body or "").lower().startswith(str(match["body_starts_with"]).lower()):
            return False
    if match.get("from_prefix"):
        from_number = (meta or {}).get("from_number") or ""
        prefixes = match["from_prefix"]
        if isinstance(prefixes, str):
            prefixes = [prefixes]
        if not any(from_number.startswith(p) for p in prefixes):
            return False
    return True


def run_automations(
    *,
    tenant,
    event: str,
    body: str = "",
    project=None,
    meta: dict | None = None,
) -> list[str]:
    """Evaluate enabled rules; return list of action types executed."""
    qs = AutomationRule.objects.filter(tenant=tenant, enabled=True).order_by("-priority")
    if project is not None:
        qs = qs.filter(models_Q_project(project))
    else:
        qs = qs.filter(project__isnull=True)

    executed: list[str] = []
    for rule in qs:
        if not _matches(rule, event=event, body=body, meta=meta):
            continue
        action = rule.action or {}
        action_type = action.get("type") or "notify"
        try:
            if action_type == "webhook":
                _post_webhook(action.get("url"), {"event": event, "body": body, **(meta or {})})
            elif action_type == "notify":
                from apps.notifications.services.notify import notify

                notify(
                    tenant=tenant,
                    event="automation.triggered",
                    severity=action.get("severity") or "info",
                    title=action.get("title") or rule.name,
                    body=action.get("body") or body[:200],
                    meta={"rule_id": str(rule.id), **(meta or {})},
                )
            elif action_type == "enqueue_project_webhook" and project is not None:
                from apps.webhooks.services.delivery import enqueue_event

                enqueue_event(
                    project=project,
                    event_type=action.get("event_type") or "automation.triggered",
                    payload={
                        "rule": rule.name,
                        "event": event,
                        "body": body,
                        **(meta or {}),
                    },
                )
            elif action_type == "reply" and meta and meta.get("from_number"):
                from apps.messaging.models import Message
                from apps.messaging.services.messages import MessageService

                MessageService.enqueue(
                    tenant=tenant,
                    to_number=meta["from_number"],
                    body=action.get("body") or "",
                    project=project,
                    mode=Message.Mode.GENERAL,
                    meta={"automation_rule_id": str(rule.id)},
                )
            executed.append(action_type)
            if action.get("stop", True):
                break
        except Exception:  # noqa: BLE001
            logger.exception("Automation rule %s failed", rule.id)
    return executed


def models_Q_project(project):
    from django.db.models import Q

    return Q(project=project) | Q(project__isnull=True)


def _post_webhook(url: str | None, payload: dict) -> None:
    if not url:
        raise ValueError("webhook url required")
    from apps.webhooks.services.delivery import is_safe_webhook_url

    if not is_safe_webhook_url(url):
        raise ValueError("unsafe webhook url")
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "DeviceFlow-Automation/1"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()
