# DeviceFlow Plugin SDK (v1)

Third-party style plugins load from `backend/plugins/<id>/` (or `DEVICEFLOW_PLUGINS_DIRS`).

## Manifest (`plugin.json`)

```json
{
  "id": "slack-notifier",
  "name": "Slack Notifier",
  "version": "1.0.0",
  "plugin_api": "1.0",
  "entry": "plugin.py",
  "hooks": ["notification.channel", "inbound.handler"],
  "config_schema": {
    "type": "object",
    "properties": {
      "webhook_url": { "type": "string" }
    }
  }
}
```

## Python entry

Export `plugin` (or `PLUGIN`) with:

- `id`, `version`
- `on_load(app_context)`
- `on_event(event)` where `event.type`, `event.tenant_id`, `event.payload`

Tenant config is injected at `payload["_plugin_configs"][plugin_id]` when the plugin is installed via `POST /api/v1/plugins/install/`.

## Safety

- In-process, admin-installed only (`plugins.manage`)
- Exceptions are isolated — core SMS path continues
- Major `plugin_api` mismatch refuses load

## Samples

- `backend/plugins/slack_notifier/`
- `backend/plugins/telegram_notifier/`

## Install via API

```http
GET /api/v1/plugins/
POST /api/v1/plugins/install/
{"plugin_id":"slack-notifier","config":{"webhook_url":"https://hooks.slack.com/..."}}
PATCH /api/v1/plugins/slack-notifier/
{"enabled":true}
```
