import uuid

from django.db import models


class OperatorPrefix(models.Model):
    """Map phone number prefixes to mobile operators (seedable)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    prefix = models.CharField(max_length=16, unique=True, db_index=True)
    operator = models.CharField(max_length=64)
    country = models.CharField(max_length=8, default="IR")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-prefix"]  # longer prefixes matched first when sorted by length in code

    def __str__(self) -> str:
        return f"{self.prefix} → {self.operator}"


class RoutingRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="routing_rules"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="routing_rules",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    priority = models.IntegerField(default=100)
    match = models.JSONField(default=dict, blank=True)
    action = models.JSONField(default=dict, blank=True)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "name"]
        indexes = [
            models.Index(fields=["tenant", "enabled", "-priority"]),
        ]

    def __str__(self) -> str:
        return self.name


class TenantRoutingConfig(models.Model):
    """Per-tenant routing / reliability defaults."""

    class LBStrategy(models.TextChoices):
        ROUND_ROBIN = "round_robin", "Round robin"
        LEAST_QUEUE = "least_queue", "Least queue"
        RANDOM = "random", "Random"
        PRIORITY = "priority", "Priority"
        WEIGHTED = "weighted", "Weighted"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.OneToOneField(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="routing_config"
    )
    lb_strategy = models.CharField(
        max_length=32, choices=LBStrategy.choices, default=LBStrategy.LEAST_QUEUE
    )
    ha_enabled = models.BooleanField(default=True)
    min_health_score = models.PositiveSmallIntegerField(default=20)
    min_battery_percent = models.PositiveSmallIntegerField(default=10)
    rate_limit_per_minute = models.PositiveIntegerField(default=50)
    rate_limit_per_hour = models.PositiveIntegerField(default=500)
    rate_limit_per_day = models.PositiveIntegerField(default=5000)
    project_rate_limit_per_minute = models.PositiveIntegerField(default=200)
    # Phase 8 — mode / intelligence
    otp_queue_weight = models.PositiveSmallIntegerField(default=10)
    marketing_queue_weight = models.PositiveSmallIntegerField(default=1)
    marketing_jitter_max_seconds = models.PositiveIntegerField(default=15)
    sim_daily_quota_default = models.PositiveIntegerField(
        default=1000, help_text="0 = unlimited"
    )
    adaptive_throttle_enabled = models.BooleanField(default=True)
    adaptive_failure_threshold = models.FloatField(default=0.3)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"RoutingConfig<{self.tenant_id}>"
