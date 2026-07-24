# DeviceFlow Phase 10 Demo Script

Stakeholder walkthrough for **Device Automation Platform + AI**.

## Prep

1. Start API + dashboard; migrate DB.
2. Enable tenant flags (Django shell or DB):

```python
tenant.settings = {
  "features": {"ussd": True, "call_hooks": False},
  "ai": {"anomaly_enabled": True, "draft_assist": True, "routing_suggestions": True},
}
tenant.save()
```

3. Pair mock agent: `python scripts/mock_agent.py --code <PAIRING_CODE>`

## Demo A — Non-SMS action (USSD)

1. Open device detail → confirm capabilities include `ussd.run`.
2. Enter `*141#` → **Run USSD**.
3. Mock agent logs `USSD -> *141#` and acks with a balance response.
4. Timeline shows `command.acked`.

API equivalent:

```http
POST /api/v1/devices/{id}/actions/
{"capability":"ussd.run","params":{"code":"*141#"}}
```

## Demo B — AI anomaly alert

1. Overview → **Run AI anomaly scan** (or wait for Celery beat).
2. With elevated failure outcomes (lab: fail messages / throttle), scan posts `anomaly.detected` in-app alert.
3. Banner appears via WebSocket.

## Demo C — Routing suggestions + inbox draft

1. Routing → **AI routing suggestions** → Apply a preferred-device rule.
2. Inbox → open thread → **Suggest reply** → review → Send (never auto-sends).

## Notes

- Call hooks stay gated (`features.call_hooks`) until compliance review.
- Optional LLM drafts need `OPENAI_API_KEY`; otherwise heuristic drafts are used.
