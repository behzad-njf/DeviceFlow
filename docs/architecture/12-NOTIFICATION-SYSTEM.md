# Notification System — DeviceFlow

**Status:** DRAFT

---

## 1. Purpose

Alert humans when the fleet needs attention — not for every SMS (that’s webhooks).

---

## 2. Channels

| Channel | Phase | Notes |
|---------|-------|-------|
| In-app | P1 | Notification center + WS toast |
| Email | P2 | SMTP / provider |
| Telegram Bot | P2 | Chat ID per tenant |
| Discord Webhook | P2 | |
| Mobile Push | P3 | For dashboard PWA later |

---

## 3. Alert Types

| Event | Default severity |
|-------|------------------|
| Device offline (missed heartbeats) | high |
| Device back online | info |
| Battery low | medium |
| Permission revoked | critical |
| Queue depth exceeded | medium |
| High failure rate | high |
| Dead letter created | medium |
| Agent version outdated | low |
| Rate limit saturated | medium |

---

## 4. Configuration

Per tenant:

```json
{
  "notifications": {
    "telegram": { "enabled": true, "chat_id": "..." },
    "email": { "enabled": true, "to": ["ops@acme.com"] },
    "rules": [
      { "event": "device.offline", "channels": ["telegram", "inapp"], "cooldown_sec": 300 }
    ]
  }
}
```

**Cooldown** prevents alert storms.

---

## 5. Pipeline

```
Domain event → NotificationService.match(rules)
  → dedupe/cooldown
  → Celery send per channel
  → store NotificationLog
```

---

## 6. Related

- [Logging & Audit](../ops/01-LOGGING-AUDIT.md)
- [Webhooks](../api/01-REST-API.md) (machine vs human distinction)
