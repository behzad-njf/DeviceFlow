# Smart Routing Engine — DeviceFlow

**Status:** DRAFT

---

## 1. Purpose

Choose the best **device + SIM** for a message given project constraints, rules, health, rate limits, and mode (OTP vs marketing).

---

## 2. Pipeline

```
Message
  → Filter candidate devices (project attachment, online, capability sms)
  → Apply RoutingRules (match → include/exclude/force)
  → Filter by RateLimit headroom
  → Filter by HealthScore threshold
  → LoadBalancer strategy selects one
  → Optional SIM selection (dual SIM rules)
  → Assign
```

---

## 3. Routing Rule Schema

```json
{
  "name": "Irancell to Phone A",
  "priority": 100,
  "match": {
    "to_prefix": ["+9893", "+9890"],
    "mode": ["otp"],
    "project_id": "..."
  },
  "action": {
    "type": "prefer_devices",
    "device_ids": ["..."],
    "sim_operator": "Irancell"
  }
}
```

Actions: `prefer_devices`, `force_device`, `exclude_devices`, `set_mode`, `set_priority`.

First hard `force_*` wins by priority desc; else soft prefers feed LB weights.

---

## 4. Built-in Match Dimensions

- Destination prefix / operator guess
- Message mode (`otp`, `marketing`, `general`)
- Time of day / quiet hours (defer to scheduler)
- Project
- Country code
- Custom meta tags from API

---

## 5. Health-Aware Routing

Exclude or deprioritize if:

- Battery < threshold (e.g. 15%) and not charging
- Signal poor
- Health score < N
- Permission SMS false
- Queue depth > max

---

## 6. OTP vs Marketing

| Mode | Routing bias |
|------|----------------|
| OTP | Lowest latency devices, separate queue weight, stricter timeout |
| Marketing | Devices with headroom, random delay injection, lower priority |

---

## 7. Operator Mapping Example (Iran)

| Prefix patterns | Operator | Prefer |
|-----------------|----------|--------|
| 0912… | MCI | Device pool MCI |
| 0935… | Irancell | … |
| 0920… | Rightel | … |

Maintainable table in DB, not hard-coded only.

---

## 8. Failure Re-route

On assign failure or device death mid-queue: re-enter pipeline excluding failed device (HA).

---

## 9. Related

- [Load Balancer](./09-LOAD-BALANCER.md)
- [Rate limits in Security](../security/01-SECURITY.md)
