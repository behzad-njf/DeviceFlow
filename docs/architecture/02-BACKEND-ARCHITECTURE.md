# Backend Architecture (Django) — DeviceFlow

**Status:** DRAFT  
**Stack:** Django 5.x · DRF · Celery · Redis · PostgreSQL · Channels · django-filter

---

## 1. Goals

- Clean domain boundaries (devices, messages, projects, tenants, analytics)
- Thin views, fat services
- Idempotent Celery tasks
- Realtime fan-out without coupling to HTTP request cycle

---

## 2. Django Apps

```
backend/
  config/                 # settings, urls, asgi, celery
  apps/
    accounts/             # User, JWT, sessions
    tenants/              # Organization / multi-tenant
    projects/             # Project, APIKey, webhooks config
    devices/              # Device, SIM, pairing, health
    messaging/            # Message, inbound, templates, bulk
    routing/              # Rules, LB strategies
    queues/               # Queue views, policies (or part of messaging)
    analytics/            # Aggregates, rollups
    notifications/        # Alert channels
    audit/                # AuditLog
    webhooks/             # Outbound webhook delivery
    plugins/              # Plugin registry (Phase later)
    common/               # Shared utils, permissions, pagination
```

---

## 3. Layering

```
HTTP/WS
  → Permissions / Auth
    → Serializers / Validators
      → Services (domain logic)
        → Repositories / ORM
          → Celery tasks / Events
```

**Rule:** Views do not call Celery for business decisions; services enqueue.

---

## 4. Core Services

| Service | Responsibility |
|---------|----------------|
| `DeviceService` | Pairing, heartbeat ingest, status transitions |
| `MessageService` | Create, cancel, retry, status updates |
| `RoutingService` | Select device/SIM given project + constraints |
| `LoadBalancer` | Strategy over candidate set |
| `RateLimitService` | Token buckets per device/SIM/project |
| `WebhookService` | Sign, deliver, retry outbound hooks |
| `AnalyticsService` | Increment counters / query rollups |
| `NotificationService` | Ops alerts |
| `CommandService` | Remote commands to agents |

---

## 5. Celery Task Map

| Task | Trigger | Notes |
|------|---------|-------|
| `dispatch_message_to_device` | Message queued | Push via channel layer |
| `deliver_webhook` | Lifecycle event | Exponential backoff |
| `rollup_stats_hourly` | Beat | Analytics |
| `mark_stale_devices_offline` | Beat | Heartbeat timeout |
| `process_scheduled_messages` | Beat | Scheduler |
| `retry_failed_messages` | Beat / event | Policy-driven |
| `export_messages_job` | User request | Async file |

Concurrency: separate queues `default`, `dispatch`, `webhooks`, `analytics`.

---

## 6. Channels / Realtime

Channel groups:

- `tenant.{id}.dashboard`
- `project.{id}.messages`
- `device.{id}.agent` — commands to a specific agent
- `user.{id}.notifications`

Consumers:

- `DashboardConsumer` — auth JWT, subscribe to tenant/project rooms
- `AgentConsumer` — device token auth, heartbeat + command ack

Protocol details: [WebSocket Protocol](../api/02-WEBSOCKET-PROTOCOL.md).

---

## 7. Settings Structure

```
config/settings/
  base.py
  local.py
  staging.py
  production.py
```

Env via `django-environ` or pydantic-settings: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ALLOWED_HOSTS`, JWT TTLs, rate limits defaults.

---

## 8. Auth Surfaces

| Client | Auth |
|--------|------|
| Dashboard users | JWT (access + refresh) |
| External API | `X-API-Key` (project-scoped) |
| Agent | Device certificate/token (pairing secret → long-lived device credential) |

See [Security](../security/01-SECURITY.md).

---

## 9. Error Model

DRF consistent envelope:

```json
{
  "error": {
    "code": "RATE_LIMITED",
    "message": "Device rate limit exceeded",
    "details": { "retry_after": 12 }
  }
}
```

---

## 10. Admin

Django Admin enabled for superuser emergency ops; primary UX is React dashboard. Admin should not be the only ops path in production.

---

## 11. Related

- [REST API](../api/01-REST-API.md)
- [Database Design](./05-DATABASE-DESIGN.md)
- [Queue & Retry](./07-QUEUE-AND-RETRY.md)
- [Folder Structure](../structure/01-FOLDER-STRUCTURE.md)
