# Scheduler — DeviceFlow

**Status:** DRAFT

---

## 1. Purpose

Support delayed and calendar-based SMS sending, quiet hours, and bulk campaign pacing.

---

## 2. Features

| Feature | Description | Phase |
|---------|-------------|-------|
| Delayed send | `scheduled_at` on message | P1 |
| Quiet hours | Block/defer outside allowed windows | P2 |
| Campaign pacing | Max N/min with jitter for marketing | P2 |
| Recurring | Cron-like (rare; usually external) | P3 |

---

## 3. Delayed Send Flow

1. API creates message with `status=scheduled`, `scheduled_at=T`.
2. Celery Beat every minute (or Redis ETA task at create time) finds due messages.
3. Transition to `queued` → normal routing.

Prefer **ETA task per message** for precision; Beat as safety net for missed ETAs.

---

## 4. Quiet Hours

Project setting:

```json
{
  "quiet_hours": {
    "timezone": "Asia/Tehran",
    "windows_allowed": [{ "start": "08:00", "end": "20:00" }],
    "days": [0,1,2,3,4,5,6],
    "action": "defer"
  }
}
```

`defer` → push `scheduled_at` to next window; `reject` → API 422 on create.

OTP mode can bypass quiet hours (`bypass_quiet_hours: true`).

---

## 5. Marketing Jitter

Before dispatch: sleep random `0–delay_max_ms` at agent or server to reduce spam fingerprints.

---

## 6. Related

- [Queue & Retry](./07-QUEUE-AND-RETRY.md)
- [REST API](../api/01-REST-API.md)
