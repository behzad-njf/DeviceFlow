# WebSocket Protocol — DeviceFlow

**Status:** DRAFT  
**Transport:** WSS · JSON messages · Heartbeat ping/pong

---

## 1. Endpoints

| Path | Client |
|------|--------|
| `/ws/dashboard/` | React dashboard |
| `/ws/agent/` | Android agent |

---

## 2. Envelope

```json
{
  "v": 1,
  "type": "event.type",
  "request_id": "optional-uuid",
  "ts": "2026-07-23T23:00:00Z",
  "payload": {}
}
```

---

## 3. Dashboard Channel

### Connect

Query or first message: JWT access token.

Server → `connection.ack` `{ tenant_id, user_id }`

### Client → Server

| type | payload |
|------|---------|
| `subscribe` | `{ rooms: ["project.{id}", "devices"] }` |
| `unsubscribe` | `{ rooms: [...] }` |
| `ping` | `{}` |

### Server → Client

| type | payload |
|------|---------|
| `device.updated` | device summary |
| `device.health` | health jsonb |
| `message.updated` | message summary |
| `queue.updated` | `{ device_id, pending, sending, ... }` |
| `alert` | notification |
| `pong` | `{}` |

---

## 4. Agent Channel

### Connect

`Authorization: Device <token>` or first frame `auth`.

### Server → Agent

| type | payload |
|------|---------|
| `command.send_sms` | `{ command_id, message_id, to, text, sim_slot? }` |
| `command.cancel` | `{ command_id, message_id }` |
| `command.control` | `{ command_id, action, params }` |
| `config.update` | partial agent config |
| `pong` | |

### Agent → Server

| type | payload |
|------|---------|
| `heartbeat` | health |
| `message.status` | status update |
| `inbound` | inbound SMS |
| `command.ack` | `{ command_id, status: accepted|rejected, reason? }` |
| `log` | optional debug |
| `ping` | |

---

## 5. Reliability

- Server may redeliver `command.send_sms` until terminal status for `message_id`
- Agent must be idempotent
- If WS down > threshold, agent uses REST polling (`/agent/commands/pending`)

---

## 6. Room Naming

- `tenant.{uuid}`
- `project.{uuid}`
- `device.{uuid}`
- `user.{uuid}`

---

## 7. Related

- [Device Communication Protocol](./03-DEVICE-COMMUNICATION-PROTOCOL.md)
- [Backend Architecture](../architecture/02-BACKEND-ARCHITECTURE.md)
