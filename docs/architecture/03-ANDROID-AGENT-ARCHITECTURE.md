# Android Agent Architecture — DeviceFlow

**Status:** DRAFT  
**Stack:** Kotlin · Jetpack Compose · WorkManager · Foreground Service · Room · OkHttp / Scarlet or Ktor WS

---

## 1. Purpose

The Agent turns a phone into a managed node that:

- Sends/receives SMS and delivery reports
- Maintains connectivity to the control plane
- Queues work offline
- Reports health
- Executes remote commands

---

## 2. Module Structure

```
android-agent/
  app/
    ui/                 # Compose screens (status, pairing, logs)
    service/            # Foreground AgentService
    sms/                # Send, receive, delivery broadcast
    sync/               # WebSocket + REST client
    queue/              # Room entities + workers
    health/             # Battery, signal, network collectors
    commands/           # Command handlers
    update/             # APK OTA (later)
    di/                 # Hilt
    data/               # Repositories
```

---

## 3. Runtime Model

```
┌─────────────────────────────────────────┐
│           Foreground Service            │
│  ┌─────────┐  ┌──────────┐  ┌────────┐  │
│  │ WS Loop │  │ Heartbeat│  │ Queue  │  │
│  └────┬────┘  └────┬─────┘  └───┬────┘  │
│       │            │            │       │
│       └────────────┴────────────┘       │
│                    │                    │
│              SmsGateway                 │
└─────────────────────────────────────────┘
         WorkManager: retries, sync when network returns
```

**Why Foreground Service:** OEM aggressive battery killers; user-visible ongoing notification required for SMS gateway reliability.

---

## 4. Core Components

### 4.1 Pairing

1. User opens app → enters server URL + pairing code (from dashboard).
2. `POST /agent/pair` → receives `device_id` + `device_token`.
3. Stored in EncryptedSharedPreferences.

### 4.2 Heartbeat

Every `heartbeat_interval` (default 15s configurable):

```json
{
  "device_id": "...",
  "battery": 91,
  "charging": true,
  "signal": "excellent",
  "sims": [{ "slot": 1, "operator": "Irancell", "number": "..." }],
  "queue_size": 12,
  "network": "wifi",
  "agent_version": "1.0.0",
  "permissions": { "sms": true, "phone": true }
}
```

### 4.3 Outbound send

1. Receive `SEND_SMS` command with `message_id`, `to`, `text`, `sim_slot`.
2. Insert Room `LocalJob` (idempotent on `message_id`).
3. Call `SmsManager` / SubscriptionManager for dual SIM.
4. Ack `SENDING` → on success `SENT` → listen delivery `DELIVERED`/`FAILED`.

### 4.4 Inbound

`BroadcastReceiver` for `SMS_RECEIVED` → normalize → push to server → mark synced.

### 4.5 Offline

If WS/REST down: keep accepting? (only local) — actually agent only sends when online; server holds queue. Local queue is for **in-flight retries** and **inbound buffering**.

Policy:

- Server is primary queue.
- Agent local queue: commands received but not finished + inbound not yet uploaded.

---

## 5. Dual SIM

Use `SubscriptionManager` + `SmsManager.getSmsManagerForSubscriptionId`.

Server may specify `sim_slot` or `subscription_id`; agent validates against available SIMs.

---

## 6. Permissions

Required:

- `SEND_SMS`, `RECEIVE_SMS`, `READ_SMS` (as needed)
- `READ_PHONE_STATE` (SIM info)
- `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_SPECIAL_USE` / appropriate type per target SDK
- `POST_NOTIFICATIONS` (API 33+)
- Optional: `ACCESS_FINE_LOCATION` only if map feature enabled (opt-in)

Permission revoke → local banner + report in heartbeat → server alert.

---

## 7. UI (Compose) — Minimal Agent UX

Screens:

1. **Pairing**
2. **Status** — Online/Offline, queue, last sync, SIM cards
3. **Logs** — recent events (local)
4. **Settings** — server URL, heartbeat, dark mode

Agent UI is **ops-oriented**, not consumer marketing.

---

## 8. Security on Device

- Encrypted storage for tokens
- Certificate pinning optional (configurable)
- No logging of full message bodies in release logcat
- Remote wipe command: clear token + local DB (Phase later)

---

## 9. Update Strategy

- Phase 1: Manual APK
- Phase 2: Dashboard-triggered download + PackageInstaller session
- Avoid Play policy issues by documenting enterprise distribution

---

## 10. Testing

- Unit: queue state machine, parsers
- Instrumented: SMS on emulator limited — use fakes + selected real devices
- OEM matrix: Samsung, Xiaomi, Huawei battery settings checklist in docs

---

## 11. Related

- [Device Communication Protocol](../api/03-DEVICE-COMMUNICATION-PROTOCOL.md)
- [Queue & Retry](./07-QUEUE-AND-RETRY.md)
- [Folder Structure](../structure/01-FOLDER-STRUCTURE.md)
