# Performance Optimization — DeviceFlow

**Status:** DRAFT

---

## 1. Targets

| Path | Target |
|------|--------|
| `POST /messages/send` enqueue | p95 < 200ms |
| Dashboard message list | p95 < 500ms |
| Heartbeat ingest | p95 < 100ms |
| WS fan-out | < 1s to UI |

---

## 2. Backend Tactics

- Index hot filters (see DB doc)
- Avoid N+1 (select_related/prefetch)
- Redis for rate limits & live counters
- Celery for webhooks/exports — never block request
- Connection pooling (PgBouncer)
- Paginate everything

---

## 3. Agent Tactics

- Batch status uploads when reconnecting
- Backoff heartbeats on battery saver mode (with server awareness)
- Single WS connection

---

## 4. Dashboard Tactics

- Virtualized tables
- Query staleTime tuned per resource
- Conditionally subscribe WS rooms

---

## 5. Load Testing

Tools: k6 / Locust

Scenarios: burst enqueue 1k rps (accept), sustained 100 rps with mock agents.

---

## 6. Related

- [Database Design](../architecture/05-DATABASE-DESIGN.md)
- [Monitoring](./02-MONITORING.md)
