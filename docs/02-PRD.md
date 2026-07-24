# Product Requirements Document (PRD) — DeviceFlow

**Status:** DRAFT  
**Version:** 0.1  
**Related:** [Vision](./01-VISION-AND-PRODUCT-STRATEGY.md) · [Roadmap](./roadmap/01-ROADMAP.md)

---

## 1. Purpose

Define functional and non-functional requirements for DeviceFlow so engineering, design, and AI agents can implement without ambiguity.

---

## 2. Goals

### Primary goals

- G1: Register multiple Android devices and send SMS via REST API.
- G2: Assign devices to projects; route by project or explicit device.
- G3: Full visibility: message lifecycle, device health, queues, stats.
- G4: Production-ready reliability: queue, retry, offline mode, heartbeat.
- G5: Secure multi-user access with API keys and RBAC.

### Secondary goals

- G6: Smart routing, load balancing, rate limiting, SIM rotation.
- G7: Webhooks, templates, bulk send, scheduling, conversations.
- G8: Plugin architecture and path to Device Automation Platform.

### Non-goals (MVP)

- NG1: Becoming a telecom carrier or buying virtual numbers from operators.
- NG2: iOS agent (Android-first).
- NG3: Built-in billing/payment for end customers (Phase later).
- NG4: Guaranteed delivery independent of carrier/SIM health.

---

## 3. Personas

| Persona | Needs |
|---------|--------|
| **Admin** | Tenants, users, global settings, audit |
| **Operator** | Devices online, queues, retries, alerts |
| **Developer** | API keys, playground, webhooks, docs |
| **Viewer** | Read-only stats and message history |
| **End system** | Machine client calling `/api/send` |

---

## 4. User Stories (selected)

### Devices

- US-D01: As an Operator, I register a phone by installing the agent and pairing with a token so it appears Online in the dashboard.
- US-D02: As an Operator, I see battery, signal, SIM, last seen, pending, sent/failed today per device.
- US-D03: As an Operator, I send remote commands (restart agent, clear queue, refresh SIM).

### Messaging

- US-M01: As a Developer, I POST send with `project` or `device` and receive a message ID.
- US-M02: As a Developer, I poll or webhook for status: Pending → Sending → Sent → Delivered/Failed.
- US-M03: As an Operator, I cancel or retry a message from the dashboard.
- US-M04: As a Developer, I schedule a message for a future time.

### Projects

- US-P01: As an Admin, I create a project with API key, rate limits, allowed devices, webhooks.
- US-P02: As an Admin, I assign phones to projects (shared or exclusive).

### Analytics

- US-A01: As a Viewer, I see today/yesterday/week/month SMS counts and charts.
- US-A02: As an Operator, I see per-device success rate and average send latency.

### Reliability

- US-R01: As the system, if a device goes offline, I re-route pending messages when HA policy allows and notify ops.
- US-R02: As the agent, if no network, I keep a local queue and sync when online.

---

## 5. Functional Requirements

### 5.1 Android Agent (`FEAT-AGENT`)

| ID | Requirement | Priority |
|----|-------------|----------|
| REQ-AG-01 | Send SMS to arbitrary number with custom text | P0 |
| REQ-AG-02 | Receive inbound SMS and forward to server | P0 |
| REQ-AG-03 | Capture delivery reports where OS/carrier allows | P0 |
| REQ-AG-04 | Dual-SIM selection (SIM1/SIM2) | P0 |
| REQ-AG-05 | Persistent connection / reconnect with backoff | P0 |
| REQ-AG-06 | Local Room queue + retry | P0 |
| REQ-AG-07 | Offline mode (queue locally) | P0 |
| REQ-AG-08 | Heartbeat with health payload | P0 |
| REQ-AG-09 | Execute remote commands from server | P1 |
| REQ-AG-10 | Foreground service with clear notification | P0 |
| REQ-AG-11 | Permission monitor & alert on revoke | P1 |
| REQ-AG-12 | In-app OTA APK update (enterprise channel) | P2 |
| REQ-AG-13 | Auto-reply by keyword (rules from server) | P2 |
| REQ-AG-14 | USSD execute (where permitted) | P3 |

### 5.2 Backend API (`FEAT-API`)

| ID | Requirement | Priority |
|----|-------------|----------|
| REQ-API-01 | `POST /send` with device or project routing | P0 |
| REQ-API-02 | Message status query by ID | P0 |
| REQ-API-03 | Cancel / retry message | P1 |
| REQ-API-04 | Device CRUD + pairing | P0 |
| REQ-API-05 | Project CRUD + API keys | P0 |
| REQ-API-06 | Queue inspection endpoints | P1 |
| REQ-API-07 | Statistics endpoints | P1 |
| REQ-API-08 | Webhook registration & delivery | P1 |
| REQ-API-09 | Bulk send (CSV/JSON) | P2 |
| REQ-API-10 | Templates with variables | P2 |
| REQ-API-11 | Contacts, groups, black/whitelist | P2 |
| REQ-API-12 | API playground metadata | P2 |

### 5.3 Dashboard (`FEAT-UI`)

| ID | Requirement | Priority |
|----|-------------|----------|
| REQ-UI-01 | Live device list (online/offline/busy) | P0 |
| REQ-UI-02 | Message list with filters & search | P0 |
| REQ-UI-03 | Project management UI | P0 |
| REQ-UI-04 | Charts: SMS/hour, day, month | P1 |
| REQ-UI-05 | Queue inspector | P1 |
| REQ-UI-06 | Event timeline per device | P1 |
| REQ-UI-07 | User & role management | P1 |
| REQ-UI-08 | Webhook builder UI | P2 |
| REQ-UI-09 | Conversation / inbox views | P2 |
| REQ-UI-10 | Map of device locations | P3 |
| REQ-UI-11 | Light/Dark + RTL (Vazirmatn) | P0 |

### 5.4 Platform Intelligence (`FEAT-INTEL`)

| ID | Requirement | Priority |
|----|-------------|----------|
| REQ-IN-01 | Round-robin / least-queue / random / priority LB | P1 |
| REQ-IN-02 | Smart routing rules (operator, mode, health) | P1 |
| REQ-IN-03 | Per-SIM/device rate limiter | P0 |
| REQ-IN-04 | Auto SIM rotation on quota | P2 |
| REQ-IN-05 | HA failover when device offline | P1 |
| REQ-IN-06 | OTP vs Marketing queue modes | P2 |
| REQ-IN-07 | Health score per device | P2 |
| REQ-IN-08 | Quiet hours / allowed send windows | P2 |

### 5.5 Enterprise (`FEAT-ENT`)

| ID | Requirement | Priority |
|----|-------------|----------|
| REQ-EN-01 | Multi-tenant isolation | P1 |
| REQ-EN-02 | RBAC: Admin, Developer, Operator, Viewer | P0 |
| REQ-EN-03 | Audit log of mutations | P1 |
| REQ-EN-04 | IP whitelist for API keys | P1 |
| REQ-EN-05 | Export CSV/Excel/JSON | P2 |
| REQ-EN-06 | Plugin system | P3 |
| REQ-EN-07 | Notifications (Telegram/Discord/Email) | P2 |

---

## 6. Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NFR-01 | Latency | API accept send < 200ms p95 (enqueue) |
| NFR-02 | Throughput | Design for 100+ msgs/sec per deployment (horizontally scalable) |
| NFR-03 | Availability | Control plane 99.9% target (device SLA separate) |
| NFR-04 | Durability | No message loss once accepted (Postgres + Redis ack design) |
| NFR-05 | Security | TLS everywhere; secrets encrypted at rest; least privilege |
| NFR-06 | Privacy | Message bodies access-controlled; retention policy configurable |
| NFR-07 | Observability | Metrics, structured logs, traces for critical paths |
| NFR-08 | i18n | FA + EN UI strings; RTL layout |
| NFR-09 | Compatibility | Android 8+ (API 26+); modern browsers last 2 versions |
| NFR-10 | Ops | Docker Compose for dev; K8s for prod |

---

## 7. Message Lifecycle States

```
Queued → Assigned → Sending → Sent → Delivered
                 ↘ Failed → Retrying → (back to Queued) → DeadLetter
Cancelled (terminal)
```

Exact transitions: see [Queue & Retry](./architecture/07-QUEUE-AND-RETRY.md).

---

## 8. MVP Scope (Phase 1–3)

**In MVP**

- Device register + heartbeat + send/receive SMS
- Dual SIM basic selection
- Projects + API keys
- `POST /send`, status, basic dashboard
- Rate limit (simple), retry with backoff
- JWT dashboard auth + RBAC basic roles
- Light/Dark RTL dashboard with core screens

**Out of MVP (later phases)**

- Plugin SDK, map, remote screen beyond health, AI, full webhook builder, MMS, Call API

---

## 9. Acceptance Criteria (MVP)

1. Install agent → pair → Online within 60s on dashboard.
2. `POST /api/v1/messages/send` returns `id`; SMS arrives on handset within configured timeout when device online.
3. Delivery/failure reflected in dashboard and status API.
4. Device offline: message stays queued or fails per policy; alert optional.
5. Operator can filter messages by project/device/status.
6. Unauthorized API key rejected with 401.

---

## 10. Open Questions

| # | Question | Owner |
|---|----------|-------|
| Q1 | Final product name & branding | Product |
| Q2 | Self-host only vs SaaS first | Product |
| Q3 | Default message retention (days) | Security |
| Q4 | Play Store vs enterprise APK distribution | Mobile |
| Q5 | gRPC vs WebSocket for agent transport (v1) | Architecture |

**Working decision for Q5:** WebSocket + REST fallback for v1; gRPC optional later.

---

## 11. Traceability

- Requirements → Phases: [Roadmap](./roadmap/01-ROADMAP.md)
- Requirements → API: [REST API](./api/01-REST-API.md)
- Requirements → DB: [Database Design](./architecture/05-DATABASE-DESIGN.md)
