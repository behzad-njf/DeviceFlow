# Plugin SDK — DeviceFlow

**Status:** DRAFT  
**Phase:** 8+ (design now, implement later)

---

## 1. Vision

Allow extensions without forking core:

- CRM/ERP connectors
- Extra notification channels
- Extra message channels (WhatsApp Business legal APIs, etc.)
- Custom routers

---

## 2. Plugin Types

| Type | Hook points |
|------|-------------|
| `InboundHandler` | After inbound SMS stored |
| `OutboundLifecycle` | on_queued, on_sent, on_delivered, on_failed |
| `AuthEnricher` | Rare |
| `ChannelAdapter` | Alternative send backends |
| `DashboardWidget` | Frontend plugin (later, Module Federation) |

---

## 3. Backend Contract (Python)

```python
class Plugin(Protocol):
    id: str
    version: str

    def on_load(self, app_context): ...
    def on_event(self, event: DomainEvent): ...
```

Discovery: entry points / `plugins/` folder with `plugin.json` manifest.

Manifest:

```json
{
  "id": "slack-notifier",
  "name": "Slack Notifier",
  "version": "1.0.0",
  "hooks": ["notification.channel"],
  "config_schema": { "type": "object", "properties": { "webhook_url": { "type": "string" } } }
}
```

---

## 4. Safety

- Plugins run in-process v1 (trusted/admin-installed only)
- Future: sidecar workers with signed payloads
- Timeouts around plugin calls
- Errors isolated — core path continues

---

## 5. Versioning

Semver; core advertises `plugin_api_version`. Incompatible plugins refuse to load.

---

## 6. Related

- [Future Features](../roadmap/02-FUTURE-FEATURES-AI.md)
- [Software Architecture](./01-SOFTWARE-ARCHITECTURE.md)
