# Vision & Product Strategy — DeviceFlow

**Status:** APPROVED (Platform framing — Phase 10)  
**Product name (working):** DeviceFlow  
**Tagline:** *Your phones. Your gateway. Full control.*

---

## 1. Vision Statement

Build an **Enterprise Device Automation Platform** that starts with SMS gateway capabilities and evolves into a programmable Android agent fleet — controllable via API, observable via dashboard, and extensible via plugins.

We are **not** building “another SMS API.” We are building the **control plane** for physical devices that companies already own (or can buy cheaply), turning them into first-class infrastructure for OTP, support, marketing, and automation.

**Platform contract (Phase 10):** devices advertise capabilities (`sms.send`, `ussd.run`, …) and accept generic actions via `POST /devices/{id}/actions`. SMS remains the first channel; USSD/call hooks are capability- and feature-gated.

---

## 2. Problem

Commercial SMS APIs (Twilio-like providers in each region) are:

- Expensive at scale
- Geographically constrained or filtered
- Opaque (little control over routing, SIM health, delivery physics)
- Hard to customize for local operators and dual-SIM realities

Open-source phone-as-gateway apps exist, but typically lack:

- Multi-device fleet management
- Project-based routing and multi-tenancy
- Enterprise observability (queues, health, audit)
- Production-grade API + webhooks + RBAC

**Gap:** A clear, visual, infinitely customizable **platform** that treats phones as managed nodes in an SMS (and later multi-channel) mesh.

---

## 3. Solution

### Three pillars

1. **Android Agent** — installable on any compatible phone; registers as a device; sends/receives SMS; reports health; executes remote commands.
2. **Backend Control Plane** — Django-based API that queues, routes, balances, schedules, and records every message.
3. **Operations Dashboard** — React console where everything is visible: devices, SIMs, queues, stats, logs, projects, API keys.

### Positioning

| Competitor type | They sell | We sell |
|-----------------|-----------|---------|
| Cloud SMS APIs | Minutes / messages on their network | Control of **your** SIMs and devices |
| DIY scripts | One phone + one webhook | Fleet, projects, HA, analytics |
| MDM / RMM | Device policy | Communication & automation workloads |

---

## 4. Ideal Customer Profile (ICP)

### Primary

- Mid-size product teams needing OTP / transactional SMS with cost control
- Agencies running multi-client messaging with separate projects/API keys
- Companies with on-prem / private-cloud requirements (data residency)
- Support & CRM teams needing inbound SMS + conversation view

### Secondary

- Schools / logistics / field ops with regional phones
- Developers building local marketplaces who need Iranian (or other) operator reach without expensive aggregators

### Non-goals (initially)

- Becoming a licensed telecom operator
- Guaranteeing carrier-grade SLA without customer-owned SIMs
- Competing on “cheapest bulk SMS” alone without platform value

---

## 5. Product Principles

1. **Clarity over cleverness** — every message, device, and failure must be inspectable.
2. **Phone as infrastructure** — treat devices like servers (health, heartbeat, deploy, restart).
3. **Project isolation** — API keys, devices, quotas, webhooks scoped per project/tenant.
4. **Infinite customization via rules** — routing, rate limits, modes (OTP vs marketing), plugins.
5. **Extensibility** — architecture must allow Call, USSD, contacts, WhatsApp (legal), RCS later without rewrite.
6. **RTL-first UX** — Persian typography (Vazirmatn) and bilingual dashboard from day one.

---

## 6. Strategic Moat

| Moat | How |
|------|-----|
| Fleet UX | Live monitor, health score, queue inspector — hard to copy shallowly |
| Smart routing | Operator + health + mode aware — saves SIMs from bans |
| Plugin SDK | Ecosystem of CRM/ERP connectors |
| Device Automation framing | Up-sell beyond SMS into agent platform |
| Observability | Audit + timeline + metrics as default, not bolt-on |

---

## 7. Business Model (options)

1. **Self-hosted open core** — free core; paid HA, plugins, SSO, advanced analytics  
2. **SaaS control plane** — host backend/dashboard; customer brings phones  
3. **Hybrid** — on-prem license for enterprises  

Monetization levers: seats, devices, message volume, plugins, support SLA.

*(Final model TBD before Phase 6 commercial packaging.)*

---

## 8. Success Metrics (North Star)

| Metric | Target (Year 1 aspirational) |
|--------|------------------------------|
| Messages processed / month (platform) | Growing, measured |
| Device uptime (fleet average) | ≥ 99% (excluding intentional offline) |
| Time-to-first-SMS for new customer | < 30 minutes |
| Dashboard task completion (ops) | Send, inspect, retry without docs |
| SIM ban incidents / 10k msgs | Decreasing via rate limiter |

---

## 9. Evolution Path

```
Phase A: SMS Gateway Platform
    ↓
Phase B: Conversation + Inbox + Templates + Bulk
    ↓
Phase C: Smart Routing + HA + OTP/Marketing modes
    ↓
Phase D: Plugin SDK + Multi-tenant SaaS
    ↓
Phase E: Device Automation Platform (Call, USSD, sensors, channels)
    ↓
Phase F: AI (anomaly detection, auto-routing, reply assist)
```

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Carrier spam / SIM blocks | Rate limits, SIM rotation, marketing delays, health score |
| Android SMS permission / OS restrictions | Foreground service, clear UX, permission monitor, OEM guides |
| Google Play policy for SMS apps | Prefer sideload / enterprise distribution; document policy |
| Competing open-source | Differentiate on dashboard, routing, multi-tenant, plugins |
| Legal / consent for marketing SMS | Project-level compliance flags, quiet hours, opt-out hooks |
| Scale bottleneck | Celery + Redis + horizontal API; device parallelization |

---

## 11. Naming

**DeviceFlow** (working). Alternatives: GateSIM, PhoneMesh, AgentSMS, SimFleet.  
Final brand before public launch.

---

## 12. One-Sentence Pitch

**DeviceFlow turns Android phones into a managed, API-first SMS and device automation fleet — with enterprise routing, queues, and a dashboard that makes every message and every device visible.**
