# Database Design — DeviceFlow

**Status:** DRAFT  
**Engine:** PostgreSQL 16+

---

## 1. ERD (Logical)

```
Tenant 1──* UserMembership *──1 User
Tenant 1──* Project
Project 1──* ApiKey
Project 1──* WebhookEndpoint
Project *──* Device          (M2M: ProjectDevice)
Tenant 1──* Device
Device 1──* SimSlot
Device 1──* DeviceEvent
Project 1──* Message
Device 1──* Message          (nullable until assigned)
Message 1──* MessageAttempt
Message 1──* MessageEvent
Project 1──* InboundMessage
Project 1──* Template
Project 1──* Contact
Tenant 1──* AuditLog
Tenant 1──* RoutingRule
```

---

## 2. Tables

### 2.1 `tenants_tenant`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID PK | |
| name | varchar | |
| slug | varchar unique | |
| plan | varchar | free/pro/enterprise |
| settings | jsonb | retention, defaults |
| created_at | timestamptz | |
| is_active | bool | |

### 2.2 `accounts_user`

Standard custom user: email, password hash, name, is_staff, locale, theme.

### 2.3 `tenants_membership`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| tenant_id | FK | |
| user_id | FK | |
| role | varchar | admin/developer/operator/viewer |
| unique(tenant_id, user_id) | | |

### 2.4 `projects_project`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| tenant_id | FK | |
| name | varchar | |
| slug | varchar | unique per tenant |
| mode_default | varchar | otp/marketing/general |
| rate_limit | jsonb | |
| allowed_numbers | jsonb | optional allowlist |
| settings | jsonb | |
| created_at | timestamptz | |

### 2.5 `projects_apikey`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| project_id | FK | |
| name | varchar | |
| key_prefix | varchar | display |
| key_hash | varchar | store hash only |
| ip_whitelist | inet[] / jsonb | |
| scopes | jsonb | |
| last_used_at | timestamptz | |
| revoked_at | timestamptz null | |

### 2.6 `devices_device`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| tenant_id | FK | |
| name | varchar | e.g. office-phone |
| status | varchar | online/offline/busy/disabled |
| agent_version | varchar | |
| last_seen_at | timestamptz | |
| health | jsonb | battery, signal, etc. |
| health_score | int | 0–100 |
| capabilities | jsonb | ["sms","ussd"] |
| pairing_code_hash | varchar null | ephemeral |
| device_token_hash | varchar | |
| meta | jsonb | labels, city |
| created_at | timestamptz | |

### 2.7 `devices_simslot`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| device_id | FK | |
| slot_index | int | 1 or 2 |
| subscription_id | varchar null | Android id |
| operator | varchar | |
| phone_number | varchar null | |
| iccid | varchar null | |
| daily_sent | int | reset job |
| rate_limit | jsonb | |
| is_active | bool | |

### 2.8 `projects_projectdevice`

M2M: project_id, device_id, priority, exclusive bool.

### 2.9 `messaging_message`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| tenant_id | FK | denormalized for RLS-style filters |
| project_id | FK | |
| device_id | FK null | |
| sim_slot_id | FK null | |
| to_number | varchar | E.164 preferred |
| body | text | |
| status | varchar | see queue doc |
| priority | int | |
| mode | varchar | otp/marketing/general |
| scheduled_at | timestamptz null | |
| sent_at | timestamptz null | |
| delivered_at | timestamptz null | |
| failed_at | timestamptz null | |
| error_code | varchar null | |
| error_message | text null | |
| retry_count | int | |
| latency_ms | int null | |
| client_ref | varchar null | idempotency key |
| meta | jsonb | |
| created_at | timestamptz | |
| updated_at | timestamptz | |

**Indexes:** `(project_id, created_at DESC)`, `(device_id, status)`, `(status, scheduled_at)`, `(tenant_id, created_at)`, unique `(project_id, client_ref)` where client_ref not null.

### 2.10 `messaging_messageattempt`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| message_id | FK | |
| device_id | FK | |
| started_at | timestamptz | |
| finished_at | timestamptz null | |
| result | varchar | |
| detail | text | |

### 2.11 `messaging_inboundmessage`

| Column | Type | Notes |
|--------|------|-------|
| id | UUID | |
| tenant_id | FK | |
| project_id | FK null | resolved by rule |
| device_id | FK | |
| from_number | varchar | |
| body | text | |
| received_at | timestamptz | |
| read_at | timestamptz null | |
| meta | jsonb | |

### 2.12 `messaging_template`

id, project_id, name, body (`{{vars}}`), channel=`sms`.

### 2.13 `routing_rule`

id, tenant_id, project_id null (global), priority, match jsonb, action jsonb, enabled.

### 2.14 `webhooks_endpoint`

id, project_id, url, secret, events[], is_active, failure_count.

### 2.15 `webhooks_delivery`

id, endpoint_id, event_type, payload, status, attempts, next_retry_at.

### 2.16 `audit_auditlog`

id, tenant_id, actor_user_id null, actor_type, action, object_type, object_id, before jsonb, after jsonb, ip, created_at.

### 2.17 `analytics_hourlystat`

id, tenant_id, project_id null, device_id null, hour timestamptz, sent, delivered, failed, inbound — unique constraint on dimensions + hour.

### 2.18 `devices_deviceevent`

id, device_id, type, payload jsonb, created_at — timeline.

### 2.19 Contacts (Phase 2+)

`contacts_contact`, `contacts_group`, M2M, tags; blacklist/whitelist tables or flags.

---

## 3. Multi-Tenant Access Pattern

Every query filters by `tenant_id` from auth context. Optional Postgres RLS later; app-level mandatory in v1.

---

## 4. Retention

Configurable per tenant: e.g. message bodies 90 days; aggregates kept longer. Celery cleanup job.

---

## 5. Migration Policy

- Django migrations only
- Expand/contract for zero-downtime on large tables
- Never rewrite history of `messaging_message` without backup

---

## 6. Related

- [Multi-Tenant](./06-MULTI-TENANT-ARCHITECTURE.md)
- [Analytics](./11-ANALYTICS-ENGINE.md)
