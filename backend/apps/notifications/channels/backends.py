"""Notification channel backends."""
from __future__ import annotations

import json
import logging
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage

from django.conf import settings

logger = logging.getLogger(__name__)


def send_email(*, config: dict, title: str, body: str) -> None:
    to_list = config.get("to") or []
    if isinstance(to_list, str):
        to_list = [to_list]
    if not to_list:
        raise ValueError("email.to is required")
    host = config.get("smtp_host") or getattr(settings, "EMAIL_HOST", "") or ""
    if not host:
        # Dev fallback: log only
        logger.info("EMAIL notify (no SMTP): to=%s title=%s body=%s", to_list, title, body)
        return
    port = int(config.get("smtp_port") or getattr(settings, "EMAIL_PORT", 587))
    user = config.get("smtp_user") or getattr(settings, "EMAIL_HOST_USER", "")
    password = config.get("smtp_password") or getattr(settings, "EMAIL_HOST_PASSWORD", "")
    from_addr = config.get("from") or user or "noreply@deviceflow.local"
    msg = EmailMessage()
    msg["Subject"] = title
    msg["From"] = from_addr
    msg["To"] = ", ".join(to_list)
    msg.set_content(body)
    with smtplib.SMTP(host, port, timeout=10) as smtp:
        if config.get("use_tls", True):
            smtp.starttls()
        if user:
            smtp.login(user, password)
        smtp.send_message(msg)


def send_telegram(*, config: dict, title: str, body: str) -> None:
    token = config.get("bot_token") or getattr(settings, "TELEGRAM_BOT_TOKEN", "")
    chat_id = config.get("chat_id")
    if not token or not chat_id:
        raise ValueError("telegram bot_token and chat_id required")
    text = f"{title}\n{body}".strip()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST")
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()


def send_discord(*, config: dict, title: str, body: str) -> None:
    webhook_url = config.get("webhook_url")
    if not webhook_url:
        raise ValueError("discord webhook_url required")
    payload = {"content": f"**{title}**\n{body}".strip()}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        resp.read()
