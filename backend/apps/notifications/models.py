import uuid

from django.db import models


class NotificationChannel(models.Model):
    class ChannelType(models.TextChoices):
        EMAIL = "email", "Email"
        TELEGRAM = "telegram", "Telegram"
        DISCORD = "discord", "Discord"
        INAPP = "inapp", "In-app"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="notification_channels"
    )
    channel_type = models.CharField(max_length=32, choices=ChannelType.choices)
    name = models.CharField(max_length=128, blank=True, default="")
    enabled = models.BooleanField(default=True)
    config = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["channel_type", "name"]

    def __str__(self) -> str:
        return f"{self.channel_type}:{self.name or self.id}"


class NotificationRule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="notification_rules"
    )
    name = models.CharField(max_length=255)
    event = models.CharField(max_length=64, db_index=True)
    channels = models.JSONField(default=list, blank=True)  # ["telegram","email","inapp"]
    cooldown_sec = models.PositiveIntegerField(default=300)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["event", "name"]

    def __str__(self) -> str:
        return self.name


class NotificationLog(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="notification_logs"
    )
    event = models.CharField(max_length=64)
    channel = models.CharField(max_length=32)
    severity = models.CharField(max_length=16, default="info")
    title = models.CharField(max_length=255)
    body = models.TextField(blank=True, default="")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    error = models.TextField(blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["tenant", "-created_at"])]
