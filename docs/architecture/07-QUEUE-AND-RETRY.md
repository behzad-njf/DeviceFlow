# Queue & Retry Architecture — DeviceFlow

**Status:** DRAFT

---

## 1. Goals

- No silent message loss after API acceptance
- Predictable states visible in dashboard
- Carrier/device failures handled with backoff
- Dead-letter for human intervention

---

## 2. Message States

| State | Meaning |
|-------|---------|
| `queued` | Accepted; not yet assigned |
| `scheduled` | Waiting for `scheduled_at` |
| `assigned` | Device/SIM chosen |
| `sending` | Agent acknowledged start |
| `sent` | SMS submitted to radio |
| `delivered` | Delivery report success (if available) |
| `failed` | Terminal or waiting retry decision |
| `retrying` | Backoff in progress |
| `cancelled` | User/API cancelled |
| `dead_letter` | Exhausted retries |

Note: Some carriers never send DLR → `sent` may be success for OTP mode (`treat_sent_as_success`).

---

## 3. Dual Queue Model

1. **Server queue (source of truth)** — Postgres `Message` + Redis dispatch lists per device.
2. **Agent local queue** — unfinished commands + unsynced inbound.

---

## 4. Dispatch Flow

```
queued → Routing → assigned → push SEND_SMS to device channel
  → agent ack sending → sending
  → agent result sent/failed
```

If device offline at assign time:

- **HA on:** re-route to next candidate
- **HA off:** stay `queued`/`assigned` until online or timeout → fail

---

## 5. Retry Policy (default)

Triggers: no service, radio error, agent timeout, temporary network.

Backoff: `30s → 1m → 5m → 10m → 30m` (configurable per project).

Max attempts: default 5.

Between retries: state `retrying`; `next_retry_at` set; Beat or ETA Celery task requeues.

---

## 6. Idempotency

- Client may send `client_ref` / `Idempotency-Key`
- Agent commands keyed by `message_id` — duplicate SEND ignored if already sent

---

## 7. Cancellation

Allowed while `queued|scheduled|assigned|retrying`.  
If `sending`, best-effort cancel command; may still send (race). Document this.

---

## 8. Dead Letter Queue (DLQ)

After max retries → `dead_letter` + event + optional notification.  
Manual Retry from dashboard resets count or uses `force`.

---

## 9. Visibility (Queue Inspector)

Per device / project aggregates:

- pending (`queued+assigned+scheduled`)
- sending
- retrying
- failed (recent)
- dead_letter

API: see REST doc.

---

## 10. Related

- [Load Balancer](./09-LOAD-BALANCER.md)
- [Smart Routing](./08-SMART-ROUTING.md)
- [Device Protocol](../api/03-DEVICE-COMMUNICATION-PROTOCOL.md)
