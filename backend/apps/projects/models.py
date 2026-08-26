import uuid

from django.db import models


class Project(models.Model):
    class Mode(models.TextChoices):
        GENERAL = "general", "General"
        OTP = "otp", "OTP"
        MARKETING = "marketing", "Marketing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="projects"
    )
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=64)
    mode_default = models.CharField(
        max_length=32, choices=Mode.choices, default=Mode.GENERAL
    )
    settings = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "slug")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.slug})"


class ProjectDevice(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="project_devices"
    )
    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE, related_name="project_links"
    )
    priority = models.IntegerField(default=100)
    exclusive = models.BooleanField(default=False)
    preferred_sim_slot = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Preferred SIM slot (1 or 2) for this project on this device.",
    )
    sim_fallback_enabled = models.BooleanField(
        default=True,
        help_text="Allow another SIM if the preferred slot is unavailable.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "device")
        ordering = ["-priority", "created_at"]


class ApiKey(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="api_keys"
    )
    name = models.CharField(max_length=255)
    key_prefix = models.CharField(max_length=32, db_index=True)
    key_hash = models.CharField(max_length=64, unique=True)
    ip_whitelist = models.JSONField(default=list, blank=True)
    scopes = models.JSONField(default=list, blank=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    usage_count = models.PositiveIntegerField(default=0)
    messages_sent = models.PositiveIntegerField(default=0)
    revoked_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.key_prefix}…)"

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.project.is_active

    @property
    def tenant(self):
        return self.project.tenant
