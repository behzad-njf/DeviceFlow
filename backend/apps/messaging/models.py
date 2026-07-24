import uuid

from django.db import models


class Message(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SCHEDULED = "scheduled", "Scheduled"
        ASSIGNED = "assigned", "Assigned"
        SENDING = "sending", "Sending"
        SENT = "sent", "Sent"
        DELIVERED = "delivered", "Delivered"
        FAILED = "failed", "Failed"
        RETRYING = "retrying", "Retrying"
        CANCELLED = "cancelled", "Cancelled"
        DEAD_LETTER = "dead_letter", "Dead letter"

    class Mode(models.TextChoices):
        GENERAL = "general", "General"
        OTP = "otp", "OTP"
        MARKETING = "marketing", "Marketing"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="messages"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="messages",
        null=True,
        blank=True,
    )
    device = models.ForeignKey(
        "devices.Device",
        on_delete=models.SET_NULL,
        related_name="messages",
        null=True,
        blank=True,
    )
    sim_slot = models.ForeignKey(
        "devices.SimSlot",
        on_delete=models.SET_NULL,
        related_name="messages",
        null=True,
        blank=True,
    )
    to_number = models.CharField(max_length=32, db_index=True)
    body = models.TextField()
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.QUEUED, db_index=True
    )
    priority = models.IntegerField(default=100)
    mode = models.CharField(max_length=32, choices=Mode.choices, default=Mode.GENERAL)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    failed_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True, default="")
    error_message = models.TextField(blank=True, default="")
    retry_count = models.PositiveSmallIntegerField(default=0)
    max_retries = models.PositiveSmallIntegerField(default=5)
    latency_ms = models.PositiveIntegerField(null=True, blank=True)
    client_ref = models.CharField(max_length=128, blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["tenant", "-created_at"]),
            models.Index(fields=["device", "status"]),
            models.Index(fields=["status", "next_retry_at"]),
            models.Index(fields=["project", "-created_at"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "client_ref"],
                condition=~models.Q(client_ref=""),
                name="uniq_project_client_ref",
            )
        ]

    def __str__(self) -> str:
        return f"{self.to_number} [{self.status}]"


class MessageTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="templates"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        related_name="templates",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255)
    body = models.TextField(help_text="Use {{variable}} placeholders")
    channel = models.CharField(max_length=16, default="sms")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("tenant", "name", "project")

    def __str__(self) -> str:
        return self.name


class IdempotencyRecord(models.Model):
    """Hardened Idempotency-Key storage for mutating API calls."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="idempotency_records"
    )
    key = models.CharField(max_length=128)
    request_hash = models.CharField(max_length=64)
    response_status = models.PositiveSmallIntegerField()
    response_body = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("tenant", "key")
        indexes = [models.Index(fields=["tenant", "key"])]


class MessageAttempt(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        Message, on_delete=models.CASCADE, related_name="attempts"
    )
    device = models.ForeignKey(
        "devices.Device", on_delete=models.SET_NULL, null=True, blank=True
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    result = models.CharField(max_length=32, blank=True, default="")
    detail = models.TextField(blank=True, default="")

    class Meta:
        ordering = ["-started_at"]


class InboundMessage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="inbound_messages"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inbound_messages",
    )
    device = models.ForeignKey(
        "devices.Device", on_delete=models.CASCADE, related_name="inbound_messages"
    )
    from_number = models.CharField(max_length=32, db_index=True)
    body = models.TextField()
    sim_slot = models.ForeignKey(
        "devices.SimSlot",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    received_at = models.DateTimeField()
    read_at = models.DateTimeField(null=True, blank=True)
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-received_at"]
        indexes = [
            models.Index(fields=["tenant", "-received_at"]),
            models.Index(fields=["device", "-received_at"]),
        ]


class BulkCampaign(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="bulk_campaigns"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="bulk_campaigns",
    )
    name = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    body_template = models.TextField(blank=True, default="")
    mode = models.CharField(max_length=32, default=Message.Mode.GENERAL)
    total = models.PositiveIntegerField(default=0)
    sent = models.PositiveIntegerField(default=0)
    failed = models.PositiveIntegerField(default=0)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    meta = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created_at"]


class BulkCampaignItem(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        BulkCampaign, on_delete=models.CASCADE, related_name="items"
    )
    to_number = models.CharField(max_length=32)
    body = models.TextField()
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING
    )
    message = models.ForeignKey(
        Message, on_delete=models.SET_NULL, null=True, blank=True
    )
    error = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class ExportJob(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RUNNING = "running", "Running"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="export_jobs"
    )
    export_type = models.CharField(max_length=32, default="messages")
    format = models.CharField(max_length=16, default="json")
    filters = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    file_path = models.CharField(max_length=512, blank=True, default="")
    row_count = models.PositiveIntegerField(default=0)
    error = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
