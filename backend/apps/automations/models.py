import uuid

from django.db import models


class AutomationRule(models.Model):
    """If inbound/event matches → action (webhook, notify, reply)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="automation_rules"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="automation_rules",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    priority = models.IntegerField(default=100)
    enabled = models.BooleanField(default=True)
    match = models.JSONField(default=dict, blank=True)
    # match examples:
    # {"event": "inbound.received", "body_contains": "STOP"}
    # {"event": "inbound.received", "body_exact": "HELP"}
    action = models.JSONField(default=dict, blank=True)
    # action examples:
    # {"type": "webhook", "url": "https://..."}  or {"type": "notify", "title": "..."}
    # {"type": "enqueue_project_webhook", "event_type": "automation.triggered"}
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "name"]
        indexes = [models.Index(fields=["tenant", "enabled", "-priority"])]

    def __str__(self) -> str:
        return self.name
