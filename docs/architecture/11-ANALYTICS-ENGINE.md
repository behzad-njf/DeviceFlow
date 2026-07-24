# Analytics Engine — DeviceFlow

**Status:** DRAFT

---

## 1. Goals

- Near-real-time counters for dashboard
- Historical charts without scanning raw messages every time
- Per tenant / project / device / operator breakdowns

---

## 2. Metrics

### Counters (increment on events)

- `sms_sent_total`
- `sms_delivered_total`
- `sms_failed_total`
- `sms_inbound_total`
- `sms_queued_gauge`
- `device_online_gauge`
- Latency histograms: enqueue→sent, sent→delivered

### Dimensions

`tenant_id`, `project_id`, `device_id`, `operator`, `mode`, `status`

---

## 3. Storage Strategy

| Layer | Use |
|-------|-----|
| Redis counters | Live “today” widgets |
| `analytics_hourlystat` | Charts hour/day |
| Raw `messaging_message` | Drill-down, exports |
| Prometheus | Infra + app metrics scrape |

Rollup job: every hour aggregate previous hour from messages or from Redis flush.

Daily/monthly charts = sum of hourly rows.

---

## 4. Health Score (device)

Weighted formula (tunable):

```
score = 0.25*battery_factor
      + 0.25*signal_factor
      + 0.20*success_rate_24h
      + 0.15*queue_factor
      + 0.15*uptime_factor
```

Clamped 0–100; stored on device; shown as stars in UI.

---

## 5. API

- `GET /analytics/overview?range=today|7d|30d`
- `GET /analytics/timeseries?metric=sent&interval=hour`
- `GET /analytics/devices`
- `GET /analytics/operators`

---

## 6. Privacy

Aggregates OK for all roles with read access; message body never in analytics payloads.

---

## 7. Related

- [Monitoring](../ops/02-MONITORING.md)
- [PRD analytics stories](../02-PRD.md)
