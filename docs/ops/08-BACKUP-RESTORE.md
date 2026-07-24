# Backup & Restore Runbook — DeviceFlow

**Phase:** 7  
**Owner:** Platform / SRE

---

## 1. What to back up

| Asset | Location | Notes |
|-------|----------|-------|
| PostgreSQL | primary DB | tenants, messages, devices, audit |
| Redis | optional | ephemeral caches/queues — rebuildable |
| Media/exports | `backend/media/` | export artifacts |
| Secrets | K8s secrets / vault | never commit |

---

## 2. Postgres logical backup (staging/prod)

```bash
# Backup
pg_dump "$DATABASE_URL" -Fc -f deviceflow-$(date +%Y%m%d).dump

# Restore into empty DB
pg_restore --clean --if-exists -d "$DATABASE_URL" deviceflow-YYYYMMDD.dump
python manage.py migrate
```

Schedule daily dumps + weekly full; retain ≥ 30 days for audit/compliance workloads.

---

## 3. Point-in-time (managed Postgres)

Prefer provider PITR (Neon/RDS/Cloud SQL). Document RPO/RTO:

| Environment | RPO | RTO |
|-------------|-----|-----|
| Staging | 24h | 4h |
| Production | ≤ 15m | ≤ 1h |

---

## 4. Restore drill checklist

1. Provision empty Postgres + Redis  
2. Restore dump  
3. Run migrations  
4. Start API + worker  
5. Verify: login, list devices, send test SMS, `/metrics` scrapes  
6. Record drill date in ops calendar  

---

## 5. Related

- [Kubernetes](./05-KUBERNETES.md)
- [Security checklist](../security/03-SECURITY-CHECKLIST.md)
