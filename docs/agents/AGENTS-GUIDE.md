# Agents Guide — DeviceFlow

**Status:** DRAFT  
**For:** Human developers and AI coding agents (Cursor, etc.)

---

## 1. Mission

Build DeviceFlow exactly as specified in `/docs`. Prefer blueprint compliance over improvisation.

---

## 2. Golden Rules

1. **Read before write** — open PRD + relevant architecture doc for the phase.
2. **Docs-first changes** — if behavior changes, update docs in the same PR.
3. **Phase discipline** — do not implement Phase 9 features during Phase 2.
4. **Security defaults** — hash secrets, tenant-scope every query, no DEBUG in prod configs.
5. **Explain changes** — when assisting users, say *what* and *why* (project preference).
6. **No secrets in git** — use `.env.example` only.
7. **Small PRs** — one phase slice per PR when possible.

---

## 3. How to Start a Phase

1. Open `docs/roadmap/phases/PHASE-XX.md`
2. Open matching prompt in `docs/agents/prompts/`
3. Open checklist in `docs/steps/`
4. Implement against contracts in `docs/api/` and `docs/architecture/`
5. Mark exit criteria

---

## 4. Layer Ownership

| Agent focus | Paths | Canonical docs |
|-------------|-------|----------------|
| Backend | `backend/` | Backend Arch, REST, DB, Security |
| Android | `android-agent/` | Android Arch, Device Protocol |
| Dashboard | `dashboard/` | React Arch, Design System |
| Ops | `deploy/` | Docker, K8s, Monitoring |

---

## 5. Definition of Done (any task)

- [ ] Matches PRD requirement IDs when applicable
- [ ] Tests added for critical logic
- [ ] i18n keys for new UI strings
- [ ] No cross-tenant data leak
- [ ] Lint/typecheck clean

---

## 6. Prompt Library

See [prompts/](./prompts/) for copy-paste phase prompts.

Also mirrored under `/prompts` at repo root for quick access.

---

## 7. When Specs Conflict

Priority: **Security > PRD P0 > Architecture decision records > older drafts**.  
Raise a short ADR note under `docs/architecture/` if resolving a conflict.
