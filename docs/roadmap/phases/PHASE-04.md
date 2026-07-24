# PHASE-04 — Routing & Reliability

**ID:** PH-04  
**Depends on:** PH-03  
**Goal:** Production-grade routing, rate limits, HA.

---

## Scope

- Load balancer strategies
- Smart routing rules engine + CRUD API/UI
- Per device/SIM/project rate limits
- HA failover when device offline
- Improved retry/DLQ policies
- Operator prefix tables

## Exit Criteria

Multi-device project distributes load; limits enforced; failover works in test.

**Status:** DONE (Phase 4 implemented)

## Agent Prompt

[`../../agents/prompts/phase-04-routing.md`](../../agents/prompts/phase-04-routing.md)
