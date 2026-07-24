# Kubernetes Deployment — DeviceFlow

**Status:** DRAFT  
**Phase:** Production hardening (Phase 7+)

---

## 1. Workloads

| Deployment | Replicas | Notes |
|------------|----------|-------|
| api | HPA 2–N | Uvicorn (ASGI) behind Ingress |
| realtime | 2+ | sticky sessions or Redis channel layer |
| worker | HPA on queue depth | |
| beat | 1 | singleton |
| dashboard | 2 | static |

Managed: Postgres (Cloud SQL/Neon/etc.), Redis (Memorystore/Upstash/self).

---

## 2. Core Objects

- Namespace `deviceflow`
- ConfigMaps + Secrets (External Secrets Operator recommended)
- Ingress TLS (cert-manager)
- NetworkPolicies (optional)
- PDB for api/realtime
- ServiceMonitor for Prometheus

---

## 3. Scaling Rules

- API CPU > 70% → scale
- Celery `dispatch` queue depth → scale workers
- Do not scale beat

---

## 4. Migrations

Init container or Job `migrate` with lock (Redis/DB advisory) before rolling api.

---

## 5. Related

- [CI/CD](./03-CICD.md)
- [Monitoring](./02-MONITORING.md)
