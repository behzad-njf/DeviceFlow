# Roadmap — DeviceFlow (Phase 1 → Phase 10)

**Status:** DRAFT  
**Prerequisite:** Documentation complete (this repo phase)

---

## Overview

| Phase | Name | Outcome |
|-------|------|---------|
| **0** | Docs & Blueprint | Done in `/docs` |
| **1** | Foundation | Monorepo, Docker, auth, tenants skeleton |
| **2** | Core Messaging MVP | Send/receive path device↔API↔dashboard |
| **3** | Fleet Ops Console | Live monitor, queues, retries, basic analytics |
| **4** | Routing & Reliability | LB, smart rules, rate limits, HA failover |
| **5** | Projects & Developer Experience | API keys, webhooks, playground, templates |
| **6** | Conversations & Bulk | Inbox, conversations, bulk, scheduler, contacts |
| **7** | Enterprise Hardening | Multi-tenant polish, audit, SSO-ready, K8s, monitoring |
| **8** | Modes & Intelligence | OTP/Marketing modes, health score, SIM rotation |
| **9** | Extensibility | Plugin SDK, automations, notification channels |
| **10** | Device Automation Platform | Capability model, USSD/Call hooks, AI assist |

Detailed specs: [phases/](./phases/).

---

## Dependency Graph

```
PH1 Foundation
  → PH2 Core Messaging
    → PH3 Fleet Ops
      → PH4 Routing
      → PH5 DX
        → PH6 Conversations/Bulk
      → PH7 Enterprise
        → PH8 Intelligence
          → PH9 Plugins
            → PH10 Automation + AI
```

---

## Definition of Done (per phase)

- Docs for phase marked implemented
- Tests for new critical paths
- Dashboard/Agent/API updated as needed
- CHANGELOG entry

---

## Related

- [PRD](../02-PRD.md)
- [Future Features & AI](./02-FUTURE-FEATURES-AI.md)
- [Steps](../steps/)
