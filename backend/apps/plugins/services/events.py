"""Emit domain events to installed plugins."""
from apps.plugins.models import PluginInstallation
from apps.plugins.registry import DomainEvent, get_registry


def emit_plugin_event(
    *,
    tenant,
    event_type: str,
    payload: dict,
    project_id: str | None = None,
) -> None:
    installs = PluginInstallation.objects.filter(tenant=tenant, enabled=True)
    installed_ids = {row.plugin_id for row in installs}
    if not installed_ids:
        return
    # Attach per-plugin config into a copy when plugins ask via payload helper
    config_by_id = {row.plugin_id: row.config for row in installs}
    event = DomainEvent(
        type=event_type,
        tenant_id=str(tenant.id),
        payload={**payload, "_plugin_configs": config_by_id},
        project_id=project_id,
    )
    get_registry().dispatch(event, installed_ids=installed_ids)
