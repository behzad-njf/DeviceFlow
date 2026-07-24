# PHASE-03 — Fleet Ops Console

**ID:** PH-03  
**Depends on:** PH-02  
**Goal:** Visibility — live monitor, queues, retries, basic stats.

---

## Scope

- Live Monitor page + WS dashboard channel
- Device detail + event timeline
- Queue inspector
- Cancel / retry message
- Basic analytics overview (today/7d counters)
- Remote commands (restart/sync/clear local/refresh SIM)
- Permission revoke alerts (in-app)

## Exit Criteria

Operator can run day-2 ops without SQL.

**Status:** Implemented — Live Monitor, Queues, device timeline/commands, analytics overview, WebSocket fan-out + in-app alerts.

## Agent Prompt

[`../../agents/prompts/phase-03-fleet-ops.md`](../../agents/prompts/phase-03-fleet-ops.md)
