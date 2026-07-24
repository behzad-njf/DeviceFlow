# RBAC & Permission Matrix — DeviceFlow

**Status:** DRAFT

---

## 1. Roles

| Role | Intent |
|------|--------|
| **Admin** | Full tenant control |
| **Developer** | API keys, webhooks, playground, send |
| **Operator** | Devices, queues, retries, live ops |
| **Viewer** | Read-only analytics & messages |

Optional later: `Auditor` (audit-only), `Owner` (billing).

---

## 2. Permission Keys

```
tenant.read / tenant.write
users.read / users.invite / users.manage
projects.read / projects.write
apikeys.read / apikeys.write
devices.read / devices.write / devices.command
messages.read / messages.send / messages.cancel / messages.retry
inbound.read / inbound.manage
queues.read
routing.read / routing.write
webhooks.read / webhooks.write
analytics.read
audit.read
exports.create
settings.write
notifications.write
plugins.manage
```

---

## 3. Matrix

| Permission | Admin | Developer | Operator | Viewer |
|------------|:-----:|:---------:|:--------:|:------:|
| tenant.write | ✓ | | | |
| users.manage | ✓ | | | |
| projects.write | ✓ | ✓ | | |
| apikeys.write | ✓ | ✓ | | |
| devices.write | ✓ | | ✓ | |
| devices.command | ✓ | | ✓ | |
| messages.send | ✓ | ✓ | ✓ | |
| messages.cancel/retry | ✓ | ✓ | ✓ | |
| messages.read | ✓ | ✓ | ✓ | ✓ |
| queues.read | ✓ | ✓ | ✓ | ✓ |
| routing.write | ✓ | ✓ | | |
| webhooks.write | ✓ | ✓ | | |
| analytics.read | ✓ | ✓ | ✓ | ✓ |
| audit.read | ✓ | | | |
| exports.create | ✓ | ✓ | ✓ | |
| settings.write | ✓ | | | |
| plugins.manage | ✓ | | | |

---

## 4. API Key Scopes

Independent of user roles; machine auth. Default key: `messages:send`, `messages:read`.  
Cannot manage users.

---

## 5. Enforcement

- DRF permission classes map role → permission set
- UI hides unauthorized nav but **server enforces**
- Multi-tenant: role is per membership

---

## 6. Related

- [Multi-Tenant](../architecture/06-MULTI-TENANT-ARCHITECTURE.md)
- [Security](./01-SECURITY.md)
