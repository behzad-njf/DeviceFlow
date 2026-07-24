# Load Test Report — DeviceFlow (Phase 7)

**Date:** 2026-07-23  
**Tool:** `scripts/load_test.py`  
**Target:** local/staging API `POST /api/v1/messages/send/`

---

## 1. Method

```bash
python scripts/load_test.py \
  --base http://127.0.0.1:8000 \
  --token "$JWT" \
  --project camp \
  --n 100 \
  --concurrency 10
```

Prerequisites: ≥1 online paired device attached to the project; rate limits raised for the test tenant.

---

## 2. Baseline (local SQLite / eager Celery)

| Metric | Result |
|--------|--------|
| Requests | 100 |
| Concurrency | 10 |
| Approx RPS | 15–40 (CPU-bound routing + SQLite) |
| Success status | mostly `202` |
| p50 latency | typically &lt; 200ms on warm run |

> Numbers vary by machine. Re-run on staging Postgres + Redis and paste results here before production cutover.

---

## 3. Staging acceptance gates

- Error rate &lt; 1% at 50 RPS for 5 minutes  
- p95 enqueue latency &lt; 500ms  
- Queue depth recovers within 2 minutes after burst  
- No 5xx on `/metrics` or `/api/v1/health/`

---

## 4. Related

- [Performance](./07-PERFORMANCE.md)
- [Monitoring](./02-MONITORING.md)
