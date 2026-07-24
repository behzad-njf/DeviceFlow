"""Sample third-party-style Slack notifier plugin."""
from __future__ import annotations

import json
import logging
import urllib.request

logger = logging.getLogger("deviceflow.plugins.slack_notifier")

# In-memory event log for tests / debugging
EVENTS: list[dict] = []


class SlackNotifierPlugin:
    id = "slack-notifier"
    version = "1.0.0"

    def on_load(self, app_context: dict) -> None:
        logger.info("Slack notifier loaded (api=%s)", app_context.get("plugin_api_version"))

    def on_event(self, event) -> None:
        EVENTS.append({"type": event.type, "tenant_id": event.tenant_id})
        configs = (event.payload or {}).get("_plugin_configs") or {}
        config = configs.get(self.id) or {}
        webhook_url = config.get("webhook_url")
        if not webhook_url:
            return
        if event.type not in {
            "device.offline",
            "inbound.received",
            "message.failed",
            "alert",
        }:
            return
        text = self._format(event)
        try:
            body = json.dumps({"text": text}).encode("utf-8")
            req = urllib.request.Request(
                webhook_url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception:  # noqa: BLE001
            logger.exception("Slack notify failed")

    def _format(self, event) -> str:
        title = (event.payload or {}).get("title") or event.type
        body = (event.payload or {}).get("body") or ""
        return f"[DeviceFlow] {title}: {body}".strip()


plugin = SlackNotifierPlugin()
