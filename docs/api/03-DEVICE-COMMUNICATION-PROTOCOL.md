# Device Communication Protocol — DeviceFlow

**Status:** DRAFT  
**Companion to:** [WebSocket Protocol](./02-WEBSOCKET-PROTOCOL.md) · Agent REST in [REST API](./01-REST-API.md)

---

## 1. Design Goals

- Work behind NAT / mobile networks
- Survive brief disconnects
- Idempotent commands
- Minimal battery impact with tunable intervals

---

## 2. Session Lifecycle

```
Pair → Store token → Connect WS → Auth OK
  → Heartbeat loop
  → Receive commands → Ack → Execute → Status reports
  → On disconnect → exponential reconnect + REST poll fallback
```

---

## 3. Pairing

1. Dashboard generates one-time `pairing_code` (6–8 chars, TTL 15m).
2. Agent submits code + device fingerprint (model, Android version, SIMs).
3. Server creates Device, returns `device_token` (shown once to agent storage).
4. Code invalidated.

---

## 4. Heartbeat Contract

Interval default **15s** (min 5s, max 120s) from server config.

Missed **3** intervals → Device `offline` (server Beat also verifies `last_seen_at`).

Payload fields: battery, charging, signal_dbm or enum, sims[], queue_size, network_type, permissions, storage_free, agent_version, optional temp.

---

## 5. Command: SEND_SMS

```json
{
  "type": "command.send_sms",
  "payload": {
    "command_id": "uuid",
    "message_id": "uuid",
    "to": "+98912...",
    "text": "...",
    "sim_slot": 1,
    "timeout_sec": 60
  }
}
```

Agent responses (REST or WS):

1. `command.ack` accepted
2. `message.status` = `sending`
3. `message.status` = `sent` | `failed`
4. Later `delivered` | `failed` if DLR available

---

## 6. Control Commands

| action | effect |
|--------|--------|
| `restart_agent` | Restart foreground service process |
| `sync` | Flush local inbound + request pending |
| `clear_queue` | Clear **local** unfinished only (server queue untouched) — confirm dangerous |
| `refresh_sim` | Re-read subscription info |
| `enable_logs` | Verbose logging window |
| `update_config` | Apply config.update |

Prefer server-side cancel for message queue clear.

---

## 7. Security

- Device token rotatable from dashboard (forces re-pair or soft rotate)
- Optional mTLS later
- Clock skew: accept status ts within ±10m

---

## 8. Version Negotiation

On connect, agent sends `protocol_version` & `agent_version`.  
Server may refuse with `upgrade_required`.

---

## 9. Related

- [Android Agent Architecture](../architecture/03-ANDROID-AGENT-ARCHITECTURE.md)
- [Queue & Retry](../architecture/07-QUEUE-AND-RETRY.md)
