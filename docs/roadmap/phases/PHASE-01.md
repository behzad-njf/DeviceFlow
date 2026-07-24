# PHASE-01 — Foundation

**ID:** PH-01  
**Goal:** Bootable monorepo with auth, tenant model, Docker, empty dashboard shell, agent stub.

---

## Scope

- Create `backend/`, `dashboard/`, `android-agent/`, `deploy/`
- Django project + apps skeleton (`accounts`, `tenants`, `common`)
- JWT login/refresh
- Tenant + membership + roles
- React app shell (routing, theme, i18n FA/EN, Vazirmatn)
- Android empty Compose app with pairing screen UI only
- Docker Compose: postgres, redis, api
- CI lint/test stubs

## Out of Scope

- SMS send, devices heartbeat, websockets

## Deliverables

- [x] Compose up works
- [x] Login returns JWT
- [x] Dashboard shows empty Overview
- [x] Docs linked from README

## Exit Criteria

Developer can register/login and see tenant-scoped empty UI.

**Status:** Implemented (Phase 1 code landed).

## Agent Prompt

Use: [`../../agents/prompts/phase-01-foundation.md`](../../agents/prompts/phase-01-foundation.md)
