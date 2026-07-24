import uuid

from django.db import models


class PluginInstallation(models.Model):
    """Per-tenant enablement + config for a discovered plugin."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="plugin_installations"
    )
    plugin_id = models.CharField(max_length=128, db_index=True)
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "plugin_id")
        ordering = ["plugin_id"]

    def __str__(self) -> str:
        return f"{self.plugin_id}@{self.tenant_id}"
