# Dashboard Wireframes — DeviceFlow

**Status:** DRAFT  
**Fidelity:** ASCII structural wireframes (not visual mockups)

---

## 1. Screen Inventory

1. Login  
2. Overview / Live Monitor  
3. Devices list  
4. Device detail  
5. Messages  
6. Message detail  
7. Queue inspector  
8. Projects list / detail  
9. API keys  
10. Webhooks  
11. Analytics  
12. Inbox (Phase 2)  
13. Users  
14. Audit  
15. Playground  
16. Settings / Notifications  

---

## 2. Live Monitor

```
┌─ DeviceFlow ──── Tenant ▾ ── WS● ── FA/EN ── Theme ── User ▾ ─┐
│ Overview                                                      │
│ Devices online 12/14   Sent today 1543   Fail 1.2%   Queue 38 │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐                        │
│ │ Office-1 │ │ Office-2 │ │ Shop-A   │  ...                   │
│ │ ● Online │ │ ● Busy   │ │ ○ Offline│                        │
│ │ 91% ████ │ │ Q:24     │ │ 2m ago   │                        │
│ └──────────┘ └──────────┘ └──────────┘                        │
└───────────────────────────────────────────────────────────────┘
```

---

## 3. Devices List

```
Devices                    [Pair device]
Filters: Status▾ Search____
Table: Name | Status | Battery | Signal | SIMs | Pending | Sent | Last seen | ⋮
```

---

## 4. Device Detail

```
Office-1  ● Online   Health 97  [Commands ▾]
Tabs: Overview | Queue | Events | SIMs | Settings
Overview: gauges + stats
Events: timeline
```

---

## 5. Messages

```
Messages     Filters: Project Device Status Date Search
Table: Time | To | Preview | Project | Device | SIM | Status | Retries | Latency
Row click → detail drawer
```

---

## 6. Project Detail

```
Project: OTP Service
Tabs: General | Devices | API Keys | Webhooks | Rate limits | Routing
```

---

## 7. Analytics

```
Range: Today | 7d | 30d
Charts: SMS/hour  SMS/day  Success vs Fail  Per device
```

---

## 8. Playground

```
POST /messages/send
JSON editor          [Send]
Response panel
```

---

## 9. Related

- [React Dashboard Architecture](../architecture/04-REACT-DASHBOARD-ARCHITECTURE.md)
- [Component Library](./05-COMPONENT-LIBRARY.md)
