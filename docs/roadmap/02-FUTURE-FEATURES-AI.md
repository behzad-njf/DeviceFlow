# Future Features & AI Integration — DeviceFlow

**Status:** DRAFT

---

## 1. Post-MVP Product Features

- MMS / media messages
- Conversation assignment to human agents
- Number aliasing (virtual internal numbers)
- Geo map of devices
- Remote diagnostics beyond health (log pull)
- Auto APK rollout rings (canary devices)
- WhatsApp / RCS via **legal official APIs** only
- Call place / call log read (capability-gated, heavy permissions)
- USSD automation for balance check
- Contact sync from device
- Advanced webhook builder (no-code IFTTT)
- Search engine (OpenSearch) for multi-million messages
- Billing & usage metering

---

## 2. AI Integration Ideas

| Use case | Approach |
|----------|----------|
| Anomaly detection | Fail-rate / offline spikes → alert with explanation |
| Smart routing assist | Suggest rules from historical success by operator |
| Auto-reply drafts | LLM suggests reply; human approve (inbox) |
| Template generation | Natural language → template + variables |
| Log summarization | “Why did Phone-3 fail today?” narrative |
| Spam risk scoring | Predict SIM ban risk from send patterns |
| Ops copilot | Chat with tenant metrics (RAG over docs + stats) |

**Principles:** AI never silently sends SMS without policy; PII minimization; optional self-hosted models for on-prem.

---

## 3. Device Automation Platform North Star

Unified `Capability` + `Command` model:

```
device.capabilities = ["sms.send", "sms.receive", "ussd.run", "contacts.read", ...]
POST /devices/{id}/actions { "capability": "ussd.run", "params": { "code": "*141#" } }
```

Channels become plugins on the same agent runtime.

---

## 4. Related

- [Plugin SDK](../architecture/13-PLUGIN-SDK.md)
- [Vision](../01-VISION-AND-PRODUCT-STRATEGY.md)
- [Phase 10](./phases/PHASE-10.md)
