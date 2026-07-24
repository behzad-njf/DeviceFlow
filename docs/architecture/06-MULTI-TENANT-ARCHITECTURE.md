# Multi-Tenant Architecture — DeviceFlow

**Status:** DRAFT

---

## 1. Model

**Tenant = Organization** (company / team).  
**Project = Workspace** inside a tenant (OTP Service, School, Marketing…).  
**Users** belong to tenants via membership + role.  
**Devices** belong to a tenant; optionally attached to one or more projects.

```
Tenant
 ├── Users (memberships)
 ├── Devices
 ├── Projects
 │    ├── API Keys
 │    ├── Webhooks
 │    ├── Messages
 │    └── Routing overrides
 └── Tenant-wide routing / notification settings
```

---

## 2. Isolation Guarantees

| Resource | Isolation |
|----------|-----------|
| Messages | tenant_id + project_id |
| Devices | tenant_id (never visible cross-tenant) |
| API Keys | project-scoped; imply tenant |
| Analytics | scoped queries only |
| Audit | tenant-scoped |
| Files/exports | tenant-prefixed object keys |

**Hard rule:** No query without tenant scope derived from auth (JWT membership or API key → project → tenant).

---

## 3. Auth Context

### Dashboard JWT claims

```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "role": "operator",
  "locale": "fa"
}
```

Tenant switcher (if multi-membership): re-issue token with selected `tenant_id`.

### API Key

Resolve: key → project → tenant → scopes. Attach to request context.

### Agent token

Resolve: device → tenant. Agent never sees other tenants.

---

## 4. Shared Devices Across Projects

Allowed via `ProjectDevice` M2M:

- **Shared pool:** multiple projects can route to same device (LB across project queues with fairness — Phase 2 policy).
- **Exclusive:** device locked to one project.

Conflict policy documented in Routing.

---

## 5. SaaS vs Single-Tenant Deploy

| Mode | Behavior |
|------|----------|
| Multi-tenant SaaS | Many tenants one cluster |
| Single-tenant on-prem | One tenant row; hide switcher |

Same codebase; `SINGLE_TENANT_MODE` setting optional.

---

## 6. Data Export / Delete (GDPR-like)

Tenant admin can request:

- Export all messages/devices metadata
- Soft-delete tenant → hard-delete after grace period

---

## 7. Related

- [RBAC](../security/02-RBAC-PERMISSION-MATRIX.md)
- [Database Design](./05-DATABASE-DESIGN.md)
