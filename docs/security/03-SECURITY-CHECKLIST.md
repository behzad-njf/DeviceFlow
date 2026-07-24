# Security Checklist — DeviceFlow (Phase 7)

**Status:** COMPLETED for Phase 7 scope  
**Reviewed:** 2026-07-23

---

## Authentication & secrets

- [x] Passwords hashed (Django PBKDF2/argon via AUTH hashers)
- [x] JWT access short-lived + refresh rotation/blacklist
- [x] API keys stored as SHA-256 hashes; plaintext shown once
- [x] Device tokens hashed at rest
- [x] Webhook HMAC signatures (`X-DeviceFlow-Signature`)
- [x] No secrets committed in git (`.env` / K8s Secret examples only)

## Authorization

- [x] Tenant scoping on API queries
- [x] RBAC permissions on dashboard/API views (`RequirePermission`)
- [x] API key scopes mapped to permissions
- [x] Automated RBAC denial tests (viewer cannot send/invite)
- [x] Audit log for invite, membership, API key mutations

## Network / runtime

- [x] SSRF guard on webhook URLs (strict outside DEBUG)
- [x] Optional API key IP whitelist
- [x] `/metrics` intended for scrape network (document NetworkPolicy)
- [x] Health endpoint for probes
- [x] K8s manifests with readiness/liveness probes

## Data

- [x] Append-only audit log model
- [x] Backup/restore runbook published
- [x] Message bodies not logged at INFO by design

## Residual / next phases

- [ ] SSO / OIDC (SSO-ready hooks deferred)
- [ ] Field-level encryption for webhook secrets (Fernet/KMS)
- [ ] WAF / edge rate limits in front of Ingress

**Sign-off (Phase 7):** Implementation complete per checklist above; staging K8s + monitoring artifacts checked in under `deploy/`.
