# REST API Documentation — DeviceFlow

**Status:** DRAFT  
**Base URL:** `/api/v1`  
**Formats:** JSON · UTF-8

---

## 1. Authentication

| Client | Header |
|--------|--------|
| User (dashboard) | `Authorization: Bearer <access_jwt>` |
| Project API | `X-API-Key: <key>` |
| Agent | `Authorization: Device <device_token>` |

TLS required in production.

---

## 2. Conventions

- UUIDs for IDs
- Timestamps ISO-8601 UTC
- Pagination: `?page=1&page_size=50` → `{ count, next, previous, results }`
- Errors: `{ "error": { "code", "message", "details?" } }`
- Idempotency: header `Idempotency-Key` on send

---

## 3. Auth Endpoints

### `POST /auth/login`

Body: `{ "email", "password", "tenant_slug?" }`  
→ `{ access, refresh, user, tenant, role }`

### `POST /auth/refresh`

Body: `{ "refresh" }` → new access

### `POST /auth/logout`

Invalidate refresh (if denylist enabled)

---

## 4. Tenants & Users

### `GET /tenants/me`

Current tenant profile

### `GET /users`

List memberships (Admin)

### `POST /users/invite`

`{ email, role }`

### `PATCH /users/{id}`

Change role / deactivate

---

## 5. Projects

### `GET /projects`

### `POST /projects`

`{ name, slug, settings? }`

### `GET /projects/{id}`

### `PATCH /projects/{id}`

### `DELETE /projects/{id}`

Soft-delete preferred

### `GET /projects/{id}/devices`

### `PUT /projects/{id}/devices`

Replace attachments `{ device_ids, priorities? }`

### `GET /projects/{id}/routes`

List optional customer→phone bindings (`route_key` → device).

### `POST /projects/{id}/routes`

`{ route_key, device_id, preferred_sim_slot?, sim_fallback_enabled?, label?, is_active? }`

### `PATCH /projects/{id}/routes/{route_id}` / `DELETE /projects/{id}/routes/{route_id}`

---

## 6. API Keys

### `GET /projects/{id}/api-keys`

### `POST /projects/{id}/api-keys`

`{ name, ip_whitelist?, scopes? }` → returns **plaintext key once**

### `POST /projects/{id}/api-keys/{kid}/revoke`

---

## 7. Devices

### `POST /devices/pairing-code`

Admin/Operator creates code `{ name? }` → `{ code, expires_at }`

### `GET /devices`

Query: `status`, `q`

### `GET /devices/{id}`

### `PATCH /devices/{id}`

Rename, disable, labels

### `DELETE /devices/{id}`

### `GET /devices/{id}/events`

Timeline

### `POST /devices/{id}/commands`

`{ "command": "restart_agent"|"sync"|"clear_queue"|"refresh_sim"|"enable_logs", "params"? }`

### `GET /devices/{id}/queue`

Inspector aggregates + optional list

---

## 8. Agent Endpoints

### `POST /agent/pair`

`{ pairing_code, device_info }` → `{ device_id, device_token, config }`

### `POST /agent/heartbeat`

Health payload (or via WS)

### `POST /agent/messages/{id}/status`

`{ status, error_code?, latency_ms?, sim_slot? }`

### `POST /agent/inbound`

`{ from, body, received_at, sim_slot?, meta? }`

### `GET /agent/commands/pending`

REST fallback if WS down

### `POST /agent/commands/{id}/ack`

---

## 9. Messages (Outbound)

### `POST /messages/send`

**API Key or JWT**

```json
{
  "to": "+98912...",
  "text": "Hello",
  "project": "otp-service",
  "device": null,
  "route_key": null,
  "mode": "otp",
  "sim_slot": null,
  "scheduled_at": null,
  "client_ref": "order-123",
  "meta": {}
}
```

Either `project` (slug/id) via key context, or explicit `device` name/id.

Optional `route_key`: looks up a `ProjectRouteBinding` on the resolved project and forces that device/SIM.
Omit it to keep normal project-pool routing. Unknown `route_key` → `422 ROUTE_NOT_CONFIGURED`.
Explicit `device` wins over `route_key`.

Response `202`:

```json
{
  "id": "uuid",
  "status": "queued",
  "created_at": "..."
}
```

### `POST /messages/send-bulk`

`{ messages: [ ... ] }` or multipart CSV — Phase 2

### `GET /messages`

Filters: `project`, `device`, `status`, `to`, `from_date`, `to_date`, `q`

### `GET /messages/{id}`

### `POST /messages/{id}/cancel`

### `POST /messages/{id}/retry`

### `GET /messages/{id}/attempts`

---

## 10. Inbound & Inbox

### `GET /inbound`

### `GET /inbound/{id}`

### `POST /inbound/{id}/read`

---

## 11. Templates

### CRUD `/templates`

Render preview: `POST /templates/{id}/render` `{ vars }`

---

## 12. Routing Rules

### CRUD `/routing-rules`

---

## 13. Webhooks

### CRUD `/projects/{id}/webhooks`

### `GET /webhooks/deliveries`

### `POST /webhooks/deliveries/{id}/redeliver`

**Event types:** `message.queued`, `message.sent`, `message.delivered`, `message.failed`, `inbound.received`, `device.offline`, `device.online`

Signed with `X-DeviceFlow-Signature: sha256=...`

---

## 14. Queues & Stats

### `GET /queues/summary`

### `GET /analytics/overview`

### `GET /analytics/timeseries`

### `GET /analytics/devices`

---

## 15. Contacts (Phase 2+)

CRUD contacts, groups, blacklist/whitelist

---

## 16. Exports

### `POST /exports`

`{ type: "messages", filters, format: "csv"|"xlsx"|"json" }` → job id

### `GET /exports/{id}`

Download when ready

---

## 17. Audit

### `GET /audit-logs`

Admin/Auditor

---

## 18. Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK |
| 201 | Created |
| 202 | Accepted (async) |
| 400 | Validation |
| 401 | Auth |
| 403 | Permission |
| 404 | Not found |
| 409 | Conflict (idempotency) |
| 422 | Business rule |
| 429 | Rate limited |
| 500 | Server error |

---

## 19. Related

- [WebSocket Protocol](./02-WEBSOCKET-PROTOCOL.md)
- [Device Protocol](./03-DEVICE-COMMUNICATION-PROTOCOL.md)
- [Security](../security/01-SECURITY.md)
