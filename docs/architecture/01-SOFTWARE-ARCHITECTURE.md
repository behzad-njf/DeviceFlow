# Software Architecture — DeviceFlow

**Status:** APPROVED (Device Automation Platform — Phase 10)  
**Stack:** Django · Celery · Redis · PostgreSQL · Channels · Kotlin · React/Vite

DeviceFlow is a **device automation platform**: SMS is the primary channel, but the agent runtime is capability-driven (`capabilities` + `/actions`) so USSD, call hooks, and future channel plugins share one control plane.

---

## 1. System Context

```
┌─────────────┐     REST/WS      ┌──────────────────────────┐
│  External   │─────────────────▶│     DeviceFlow Backend   │
│  Apps/CRM   │◀──── Webhooks ───│  (Django + Celery)       │
└─────────────┘                  └────────────┬─────────────┘
                                              │
                     ┌────────────────────────┼────────────────────────┐
                     │                        │                        │
                     ▼                        ▼                        ▼
              ┌────────────┐          ┌────────────┐           ┌────────────┐
              │ Dashboard  │          │ PostgreSQL │           │ Redis      │
              │ React SPA  │          │            │           │ Queue/WS   │
              └────────────┘          └────────────┘           └─────┬──────┘
                                                                     │
                                              ┌──────────────────────┘
                                              ▼
                                    ┌──────────────────┐
                                    │ Android Agents   │
                                    │ (N devices)      │
                                    └──────────────────┘
```

---

## 2. C4 — Containers

| Container | Responsibility | Tech |
|-----------|----------------|------|
| **api** | REST API, auth, business logic | Django + DRF |
| **worker** | Async jobs: send dispatch, webhooks, aggregations | Celery |
| **beat** | Periodic: cleanup, stats rollup, stale device check | Celery Beat |
| **realtime** | WebSocket fan-out | Django Channels + Redis |
| **db** | Source of truth | PostgreSQL 16+ |
| **cache/broker** | Cache, broker, pub/sub | Redis 7+ |
| **dashboard** | Ops UI | React + Vite + TS |
| **agent** | On-device executor | Kotlin + Compose |

---

## 3. High-Level Data Flows

### 3.1 Outbound SMS

```
Client → POST /send → API validates → Message row (Queued)
       → Routing Engine selects device/SIM
       → Enqueue device job (Redis)
       → Agent receives command (WS) OR polls
       → Agent sends SMS → reports Sent/Failed
       → API updates Message + emits WS event + optional Webhook
```

### 3.2 Inbound SMS

```
Agent SMS Receiver → POST /agent/inbound (or WS event)
  → MessageInbound row → Project routing → Webhook / Automation
  → Dashboard Inbox update
```

### 3.3 Heartbeat

```
Agent every N seconds → health payload → Device.last_seen, metrics
  → If missed M intervals → Offline → HA policies / alerts
```

---

## 4. Architectural Principles

1. **Control plane vs data plane** — Backend decides; Agent executes.
2. **At-least-once delivery to agent** — Idempotent command IDs.
3. **Postgres is truth** — Redis is accelerator, not sole durability.
4. **Tenant/project scoping** on every query.
5. **Event-first observability** — every state change emits an event.
6. **Plugin hooks** at message lifecycle boundaries (later).

---

## 5. Technology Decisions

| Concern | Choice | Rationale |
|---------|--------|-----------|
| Backend | Django + DRF | Fast CRUD, auth, admin, mature ecosystem |
| Async | Celery + Redis | Proven for queues/retries |
| Realtime | Channels | Native Django WS |
| DB | PostgreSQL | JSONB, reliability, analytics |
| Agent transport (v1) | WebSocket + REST fallback | Simpler than gRPC for phone NATs |
| Dashboard | React + Vite | Fast DX, ecosystem |
| Agent UI | Jetpack Compose | Modern Android |
| Agent work | WorkManager + Foreground Service | Reliability under OEM kills |

---

## 6. Deployment Topologies

### Dev

Docker Compose: `api`, `worker`, `beat`, `redis`, `postgres`, `dashboard` (or Vite host), optional mock agent.

### Production

Kubernetes: separate Deployments for api/worker/beat/realtime; managed Postgres/Redis; Ingress TLS; HPA on api/worker.

See [Docker](../ops/04-DOCKER.md) and [Kubernetes](../ops/05-KUBERNETES.md).

---

## 7. Cross-Cutting Modules

| Module | Doc |
|--------|-----|
| Queue & Retry | [07-QUEUE-AND-RETRY](./07-QUEUE-AND-RETRY.md) |
| Smart Routing | [08-SMART-ROUTING](./08-SMART-ROUTING.md) |
| Load Balancer | [09-LOAD-BALANCER](./09-LOAD-BALANCER.md) |
| Scheduler | [10-SCHEDULER](./10-SCHEDULER.md) |
| Analytics | [11-ANALYTICS-ENGINE](./11-ANALYTICS-ENGINE.md) |
| Notifications | [12-NOTIFICATION-SYSTEM](./12-NOTIFICATION-SYSTEM.md) |
| Plugins | [13-PLUGIN-SDK](./13-PLUGIN-SDK.md) |
| Multi-tenant | [06-MULTI-TENANT-ARCHITECTURE](./06-MULTI-TENANT-ARCHITECTURE.md) |
| Security | [../security/01-SECURITY.md](../security/01-SECURITY.md) |

---

## 8. Evolution to Device Automation Platform

Message channel abstraction:

```
ChannelAdapter
  ├── SmsAdapter (v1)
  ├── MmsAdapter (later)
  ├── UssdAdapter (later)
  ├── CallAdapter (later)
  └── PluginChannelAdapter
```

Devices expose **capabilities**; routing selects devices by capability + health.

---

## 9. Related Docs

- [Backend Architecture](./02-BACKEND-ARCHITECTURE.md)
- [Android Agent](./03-ANDROID-AGENT-ARCHITECTURE.md)
- [React Dashboard](./04-REACT-DASHBOARD-ARCHITECTURE.md)
- [Database Design](./05-DATABASE-DESIGN.md)
