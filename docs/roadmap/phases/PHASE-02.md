# PHASE-02 — Core Messaging MVP

**ID:** PH-02  
**Depends on:** PH-01  
**Goal:** End-to-end SMS send/receive with real or mock agent.

---

## Scope

- Device model + pairing API
- Agent: pair, WS/REST heartbeat, send SMS, inbound forward, status reports
- `POST /messages/send`, message states basic
- Project model (minimal) + attach devices
- Dashboard: devices list, messages list, pair flow
- Dual SIM basic selection
- Local agent queue + server queue basic retry

## Out of Scope

- Smart routing rules UI, webhooks, bulk, analytics charts

## Exit Criteria

Paired phone sends SMS from API; status visible; inbound appears in DB/UI.

**Status:** Implemented. Backend + dashboard + Android agent source ready.  
Verified via automated API tests + `scripts/mock_agent.py`. Physical device E2E pending your Android Studio build.

## Agent Prompt

[`../../agents/prompts/phase-02-messaging-mvp.md`](../../agents/prompts/phase-02-messaging-mvp.md)
