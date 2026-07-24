# Documentation Index — DeviceFlow

Master map of all blueprint documents. Use this as the single entry point for humans and AI agents.

---

## How to Use These Docs

1. Read **Vision** → understand *why* we build this.
2. Read **PRD** → understand *what* we build.
3. Read **Software Architecture** → understand *how* pieces fit.
4. Dive into layer-specific docs (Backend, Android, Dashboard).
5. Follow **Roadmap / Phases / Steps** for execution order.
6. AI agents: follow [agents/AGENTS-GUIDE.md](./agents/AGENTS-GUIDE.md) and use prompts under `agents/prompts/`.

---

## 1. Product & Strategy

| # | Document | Description |
|---|----------|-------------|
| 01 | [Vision & Product Strategy](./01-VISION-AND-PRODUCT-STRATEGY.md) | Mission, positioning, ICP, moat, Device Automation Platform vision |
| 02 | [Product Requirements (PRD)](./02-PRD.md) | Goals, personas, functional/non-functional requirements, MVP scope |

---

## 2. Architecture

| # | Document | Description |
|---|----------|-------------|
| A00 | [ADR Index](./architecture/00-ADR-INDEX.md) | Architecture decision records |
| A01 | [Software Architecture](./architecture/01-SOFTWARE-ARCHITECTURE.md) | System context, C4-style overview, tech stack, data flow |
| A02 | [Backend Architecture (Django)](./architecture/02-BACKEND-ARCHITECTURE.md) | Apps, Celery, Redis, Channels, service layer |
| A03 | [Android Agent Architecture](./architecture/03-ANDROID-AGENT-ARCHITECTURE.md) | Kotlin/Compose, services, Room, permissions, offline |
| A04 | [React Dashboard Architecture](./architecture/04-REACT-DASHBOARD-ARCHITECTURE.md) | SPA structure, state, realtime, routing |
| A05 | [Database Design](./architecture/05-DATABASE-DESIGN.md) | ERD, tables, indexes, multi-tenant keys |
| A06 | [Multi-Tenant Architecture](./architecture/06-MULTI-TENANT-ARCHITECTURE.md) | Isolation model, tenants, projects |
| A07 | [Queue & Retry Architecture](./architecture/07-QUEUE-AND-RETRY.md) | Queues, states, backoff, DLQ |
| A08 | [Smart Routing Engine](./architecture/08-SMART-ROUTING.md) | Rules, operator mapping, health-aware routing |
| A09 | [Load Balancer](./architecture/09-LOAD-BALANCER.md) | Round-robin, least-queue, priority |
| A10 | [Scheduler](./architecture/10-SCHEDULER.md) | Delayed/scheduled sends, quiet hours |
| A11 | [Analytics Engine](./architecture/11-ANALYTICS-ENGINE.md) | Metrics, aggregations, dashboards |
| A12 | [Notification System](./architecture/12-NOTIFICATION-SYSTEM.md) | Telegram, Discord, Email, Push |
| A13 | [Plugin SDK](./architecture/13-PLUGIN-SDK.md) | Extension model for CRM/ERP/channels |

---

## 3. API & Protocols

| # | Document | Description |
|---|----------|-------------|
| P01 | [REST API Documentation](./api/01-REST-API.md) | All endpoints, auth, errors, examples |
| P02 | [WebSocket Protocol](./api/02-WEBSOCKET-PROTOCOL.md) | Dashboard & agent realtime channels |
| P03 | [Device Communication Protocol](./api/03-DEVICE-COMMUNICATION-PROTOCOL.md) | Agent ↔ server messages, heartbeats, commands |

---

## 4. Security & Access

| # | Document | Description |
|---|----------|-------------|
| S01 | [Security](./security/01-SECURITY.md) | JWT, API keys, encryption, rate limit, IP whitelist |
| S02 | [RBAC & Permission Matrix](./security/02-RBAC-PERMISSION-MATRIX.md) | Roles, permissions, matrix |
| S03 | [Security Checklist](./security/03-SECURITY-CHECKLIST.md) | Phase 7 signed checklist |

---

## 5. Operations

| # | Document | Description |
|---|----------|-------------|
| O01 | [Logging & Audit System](./ops/01-LOGGING-AUDIT.md) | App logs, audit trail, event timeline |
| O02 | [Monitoring](./ops/02-MONITORING.md) | Prometheus, Grafana, alerts |
| O03 | [CI/CD Pipeline](./ops/03-CICD.md) | Build, test, release for all layers |
| O04 | [Docker & Docker Compose](./ops/04-DOCKER.md) | Local & staging compose stack |
| O05 | [Kubernetes Deployment](./ops/05-KUBERNETES.md) | Prod manifests, scaling, secrets |
| O06 | [Testing Strategy](./ops/06-TESTING-STRATEGY.md) | Unit, integration, E2E |
| O07 | [Performance Optimization](./ops/07-PERFORMANCE.md) | Throughput, latency, DB, queues |
| O08 | [Backup & Restore](./ops/08-BACKUP-RESTORE.md) | Postgres dump/restore drill |
| O09 | [Load Test Report](./ops/09-LOAD-TEST-REPORT.md) | Phase 7 load harness results |
| O10 | [Phase 10 Demo Script](./ops/10-PHASE10-DEMO.md) | Stakeholder platform + AI demo |
| Plugins | [Plugin SDK guide](./plugins/01-PLUGIN-SDK.md) | Third-party plugin authoring |

---

## 6. Design System

| # | Document | Description |
|---|----------|-------------|
| D01 | [UI/UX Design System](./design/01-UI-UX-DESIGN-SYSTEM.md) | Principles, layout, RTL, density |
| D02 | [Design Tokens](./design/02-DESIGN-TOKENS.md) | Spacing, radius, elevation, motion |
| D03 | [Typography (Vazirmatn)](./design/03-TYPOGRAPHY.md) | Font scale, Persian/English |
| D04 | [Color Palette](./design/04-COLOR-PALETTE.md) | Brand, semantic, status colors |
| D05 | [Component Library](./design/05-COMPONENT-LIBRARY.md) | Buttons, tables, charts, device cards |
| D06 | [Light/Dark Theme](./design/06-THEMES.md) | Theme tokens mapping |
| D07 | [Responsive Rules](./design/07-RESPONSIVE-RULES.md) | Breakpoints, mobile dashboard |
| D08 | [Dashboard Wireframes](./design/08-DASHBOARD-WIREFRAMES.md) | Screen inventory & ASCII wireframes |

---

## 7. Structure & Roadmap

| # | Document | Description |
|---|----------|-------------|
| ST01 | [Folder Structure](./structure/01-FOLDER-STRUCTURE.md) | Android, Backend, Frontend trees |
| R01 | [Roadmap](./roadmap/01-ROADMAP.md) | Phase 1–10 overview |
| R02 | [Future Features & AI](./roadmap/02-FUTURE-FEATURES-AI.md) | Post-MVP and AI integrations |
| Phases | [roadmap/phases/](./roadmap/phases/) | Detailed PHASE-01 … PHASE-10 |

---

## 8. Agents, Prompts & Steps

| # | Document | Description |
|---|----------|-------------|
| AG | [Agents Guide](./agents/AGENTS-GUIDE.md) | How AI coding agents must work in this repo |
| Prompts | [agents/prompts/](./agents/prompts/) | Reusable prompts per phase/layer |
| Steps | [steps/](./steps/) | Ordered implementation checklists |

---

## Document Conventions

- **Language:** Technical docs in English; product voice may include Persian notes where UX-critical.
- **Status tags:** `DRAFT` | `APPROVED` | `IMPLMENTED` | `DEPRECATED`
- **IDs:** Features use `FEAT-xxx`, requirements `REQ-xxx`, phases `PH-xx`.
- **No code in docs phases unless illustrating contracts** (schemas, JSON examples OK).

---

## Status Legend (this release)

Phases **0–10** implemented in code (MVP roadmap complete); remaining docs may still say DRAFT until a formal review pass.
