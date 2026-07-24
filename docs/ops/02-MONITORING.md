# Monitoring (Prometheus / Grafana) — DeviceFlow

**Status:** DRAFT

---

## 1. Stack

- **Prometheus** scrapes `/metrics` on API/workers
- **Grafana** dashboards
- **Alertmanager** → Notification System / Pager

Optional: OpenTelemetry traces for send path.

---

## 2. Key Metrics

### API

- `http_requests_total{status,path}`
- `http_request_duration_seconds`
- `auth_failures_total`

### Messaging

- `messages_enqueued_total`
- `messages_sent_total`
- `messages_failed_total{reason}`
- `message_send_latency_seconds`
- `queue_depth{device_id}` (careful cardinality — use tenant aggregates + sampled devices)

### Devices

- `devices_online`
- `devices_offline`
- `heartbeat_age_seconds` (histogram/summary via push or gauge from Beat)

### Infra

- Celery queue length, task runtime, Redis memory, Postgres connections

---

## 3. Grafana Dashboards

1. **Overview** — send rate, fail rate, online devices
2. **API RED** — rate, errors, duration
3. **Celery** — backlog
4. **Tenant drill-down** (Grafana variables)

---

## 4. Alerts (examples)

| Alert | Condition |
|-------|-----------|
| APIHighErrorRate | 5xx > 2% 5m |
| CeleryBacklog | queue > 10k 10m |
| NoOnlineDevices | devices_online == 0 |
| HighFailRate | fail ratio > 10% 15m |
| PostgresConnections | > 80% max |

---

## 5. Related

- [Analytics Engine](../architecture/11-ANALYTICS-ENGINE.md)
- [Kubernetes](./05-KUBERNETES.md)
