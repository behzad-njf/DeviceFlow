"""Optional inbox draft assist — heuristic first, LLM optional."""
from __future__ import annotations

import json
import os
import urllib.request

from django.conf import settings

from apps.common.features import feature_enabled
from apps.contacts.models import Conversation
from apps.messaging.models import InboundMessage, Message


def _thread_snippets(conversation: Conversation, limit: int = 8) -> list[dict]:
    outbound = list(
        Message.objects.filter(
            tenant=conversation.tenant,
            to_number=conversation.phone_number,
        ).order_by("-created_at")[:limit]
    )
    inbound = list(
        InboundMessage.objects.filter(
            tenant=conversation.tenant,
            from_number=conversation.phone_number,
        ).order_by("-created_at")[:limit]
    )
    items = []
    for m in outbound:
        items.append({"dir": "out", "body": m.body, "at": m.created_at})
    for m in inbound:
        items.append({"dir": "in", "body": m.body, "at": m.received_at})
    items.sort(key=lambda x: x["at"] or x.get("at"))
    return items[-limit:]


def _heuristic_draft(last_inbound: str) -> str:
    text = (last_inbound or "").strip().lower()
    if not text:
        return "Thanks for your message — how can we help?"
    if "stop" in text or "unsubscribe" in text:
        return "You have been unsubscribed. Reply START to opt back in."
    if "help" in text or "support" in text:
        return "Thanks for reaching out. A teammate will follow up shortly."
    if "otp" in text or "code" in text:
        return "If you did not request a code, please ignore this message."
    if "?" in text:
        return "Thanks for your question — we will get back to you soon."
    return f"Thanks for your message. Regarding “{last_inbound[:80]}”, we will follow up shortly."


def _llm_draft(snippets: list[dict], last_inbound: str) -> str | None:
    api_key = getattr(settings, "OPENAI_API_KEY", "") or os.environ.get("OPENAI_API_KEY", "")
    if not api_key:
        return None
    model = getattr(settings, "OPENAI_MODEL", "gpt-4o-mini")
    prompt = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You draft short SMS replies for a human operator. "
                    "Never invent OTPs. Keep under 160 chars when possible. "
                    "Return only the reply text."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {"thread": snippets, "last_inbound": last_inbound}, default=str
                ),
            },
        ],
        "temperature": 0.3,
        "max_tokens": 120,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(prompt).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None


def suggest_inbox_draft(*, conversation: Conversation) -> dict:
    if not feature_enabled(conversation.tenant, key="ai.draft_assist", default=True):
        return {
            "draft": "",
            "source": "disabled",
            "note": "AI draft assist disabled in tenant settings",
        }
    snippets = _thread_snippets(conversation)
    last_inbound = ""
    for item in reversed(snippets):
        if item["dir"] == "in":
            last_inbound = item["body"]
            break
    if not last_inbound:
        last_inbound = conversation.last_preview or ""

    llm = _llm_draft(snippets, last_inbound)
    if llm:
        return {"draft": llm, "source": "llm", "note": "Review before sending"}
    return {
        "draft": _heuristic_draft(last_inbound),
        "source": "heuristic",
        "note": "Rule-based suggestion — review before sending",
    }
