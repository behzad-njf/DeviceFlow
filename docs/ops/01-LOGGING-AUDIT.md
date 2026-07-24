# Logging & Audit System — DeviceFlow

**Status:** DRAFT

---

## 1. Three Pillars

| Pillar | Purpose |
|--------|---------|
| **Application logs** | Debug/trace for engineers |
| **Audit logs** | Who changed what (compliance) |
| **Domain events / timeline** | Device & message lifecycle for ops UI |

---

## 2. Application Logging

- Structured JSON logs: `timestamp`, `level`, `service`, `request_id`, `tenant_id?`, `message`, `extra`
- Correlate with `X-Request-ID`
- Levels: DEBUG (dev), INFO+, WARN, ERROR
- **Never** log API keys, passwords, device tokens, or full SMS bodies at INFO in prod (body hash optional)

Stack: structlog / python-json-logger → stdout → Loki/ELK

---

## 3. Audit Log

Record mutations:

- User invite/role change
- Project create/delete
- API key create/revoke
- Device delete/disable/command
- Routing rule changes
- Settings changes
- Message cancel (optional)

Fields: actor, action, object_type, object_id, before/after, ip, ua, ts.

Immutable (append-only); Admin UI read-only.

---

## 4. Device Event Timeline

Types: `sms.sent`, `sms.failed`, `sim.changed`, `agent.restarted`, `permission.revoked`, `online`, `offline`, `battery.low`, `config.updated`.

Shown on device detail page like a GitHub activity feed.

---

## 5. Retention

| Store | Default |
|-------|---------|
| App logs | 14–30 days |
| Audit | 1 year |
| Device events | 90 days |
| Message rows | tenant setting |

---

## 6. Related

- [Monitoring](./02-MONITORING.md)
- [Security](../security/01-SECURITY.md)
