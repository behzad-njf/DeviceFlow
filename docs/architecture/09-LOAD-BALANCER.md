# Load Balancer — DeviceFlow

**Status:** DRAFT

---

## 1. Role

Given a **candidate set** of devices from Routing, select exactly one device (and optionally SIM).

---

## 2. Strategies

| Strategy | Algorithm |
|----------|-----------|
| `round_robin` | Rotate last-used index per project/pool |
| `least_queue` | Min (pending + sending) |
| `random` | Uniform random |
| `priority` | Highest `ProjectDevice.priority`, tie-break least_queue |
| `weighted` | Weight by health_score × (1 / queue_penalty) |

Default: `least_queue` for general; `priority` for OTP pools.

---

## 3. Fairness Across Projects

When a device is shared:

- Track per-project recent send rate
- Optional weighted fair queuing so one project cannot starve others

---

## 4. Sticky Options

`sticky_to_number`: same destination prefers last successful device (conversation continuity) — Phase 2.

---

## 5. SIM Selection Inside Device

After device pick:

1. If rule forces operator/slot → use it  
2. Else prefer SIM with matching operator for destination  
3. Else least daily_sent among active SIMs  
4. Respect per-SIM rate limits

---

## 6. Observability

Metric labels: `strategy`, `project`, `device`, `result=selected|empty_set`.

Empty candidate set → message `failed` with `NO_DEVICE_AVAILABLE` or stay queued per policy.

---

## 7. Related

- [Smart Routing](./08-SMART-ROUTING.md)
- [Queue & Retry](./07-QUEUE-AND-RETRY.md)
