from django.db import models
import uuid


class HourlyStat(models.Model):
    """Rolled-up analytics for charts (tenant-scoped)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="hourly_stats"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="hourly_stats",
        null=True,
        blank=True,
    )
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.CASCADE,
        related_name="hourly_stats",
        null=True,
        blank=True,
    )
    hour = models.DateTimeField(db_index=True)
    operator = models.CharField(max_length=64, blank=True, default="")
    mode = models.CharField(max_length=32, blank=True, default="")
    sent = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    delivered = models.PositiveIntegerField(default=0)
    inbound = models.PositiveIntegerField(default=0)
    latency_sum_ms = models.BigIntegerField(default=0)
    latency_count = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            models.Index(fields=["tenant", "hour"]),
            models.Index(fields=["tenant", "operator", "hour"]),
            models.Index(fields=["tenant", "mode", "hour"]),
        ]
        unique_together = ("tenant", "project", "device", "hour", "operator", "mode")

    @property
    def avg_latency_ms(self) -> float | None:
        if self.latency_count == 0:
            return None
        return self.latency_sum_ms / self.latency_count
