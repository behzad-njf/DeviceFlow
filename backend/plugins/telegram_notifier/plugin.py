"""Sample Telegram notifier plugin (uses Bot API when configured)."""
from __future__ import annotations

import json
import logging
import urllib.parse
import urllib.request

logger = logging.getLogger("deviceflow.plugins.telegram_notifier")
EVENTS: list[dict] = []


class TelegramNotifierPlugin:
    id = "telegram-notifier"
    version = "1.0.0"

    def on_load(self, app_context: dict) -> None:
        logger.info("Telegram notifier plugin loaded")

    def on_event(self, event) -> None:
        EVENTS.append({"type": event.type, "tenant_id": event.tenant_id})
        configs = (event.payload or {}).get("_plugin_configs") or {}
        config = configs.get(self.id) or {}
        token = config.get("bot_token")
        chat_id = config.get("chat_id")
        if not token or not chat_id:
            return
        if event.type not in {"device.offline", "alert", "message.failed"}:
            return
        text = f"DeviceFlow {event.type}: {(event.payload or {}).get('title') or ''}"
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            data = urllib.parse.urlencode(
                {"chat_id": chat_id, "text": text}
            ).encode("utf-8")
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
        except Exception:  # noqa: BLE001
            logger.exception("Telegram plugin notify failed")


plugin = TelegramNotifierPlugin()
