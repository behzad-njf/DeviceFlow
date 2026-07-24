# Security — DeviceFlow

**Status:** DRAFT

---

## 1. Principles

- Least privilege (RBAC + scopes)
- Defense in depth (TLS, hashed secrets, rate limits)
- Assume phones can be stolen → remote revoke
- Never log secrets or full API keys

---

## 2. JWT (Dashboard Users)

| Token | TTL (default) | Storage |
|-------|---------------|---------|
| Access | 15m | Memory |
| Refresh | 7–30d | HttpOnly secure cookie or secure storage |

Claims: `sub`, `tenant_id`, `role`, `jti`.  
Rotate refresh; support logout denylist in Redis.

Algorithm: RS256 (prod) or HS256 (dev).

---

## 3. API Keys

- Generate `df_live_...` high entropy
- Store **SHA-256 hash** only; show plaintext once
- Prefix stored for UI identification
- Optional **IP whitelist** (CIDR list)
- Scopes example: `messages:send`, `messages:read`, `webhooks:manage`
- Rate limit per key + per project

---

## 4. Device Tokens

- Long random bearer; hashed at rest
- Revoke = disconnect agent immediately via WS close + reject REST

---

## 5. Encryption

| Data | Method |
|------|--------|
| In transit | TLS 1.2+ |
| DB secrets | Field encryption (Fernet/KMS) for webhook secrets |
| Agent prefs | EncryptedSharedPreferences |
| Backups | Encrypted exports optional |

Message bodies: access-controlled; consider encryption-at-rest via disk/Postgres TDE in enterprise deploys.

---

## 6. Rate Limiting

Layers:

1. Edge / Ingress
2. API gateway middleware (per IP / per key)
3. Project limits
4. Device/SIM limits (anti-ban)

Response `429` + `Retry-After`.

Default device: `50/min`, `500/hour`, `5000/day` (configurable).

---

## 7. IP Whitelist

On API key: if list non-empty, reject non-matching clients with `403 IP_NOT_ALLOWED`.

---

## 8. Webhook Security

- HMAC SHA-256 signature header
- Replay protection: timestamp header skew window
- SSRF guard: block private IPs unless allowlisted (enterprise)

---

## 9. Hardening Checklist

- [ ] `DEBUG=False` in prod
- [ ] Secret rotation runbook
- [ ] CORS allowlist
- [ ] CSRF for cookie sessions if used
- [ ] SQL injection: ORM only
- [ ] Dependency scanning in CI
- [ ] Android: no secrets in APK; server URL configurable

---

## 10. Related

- [RBAC](./02-RBAC-PERMISSION-MATRIX.md)
- [Audit](../ops/01-LOGGING-AUDIT.md)
