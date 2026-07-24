import uuid

from django.db import models


class Contact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="contacts"
    )
    phone_number = models.CharField(max_length=32, db_index=True)
    name = models.CharField(max_length=255, blank=True, default="")
    tags = models.JSONField(default=list, blank=True)
    is_blacklisted = models.BooleanField(default=False)
    is_whitelisted = models.BooleanField(default=False)
    notes = models.TextField(blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)
    source_device = models.ForeignKey(
        "devices.Device",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="imported_contacts",
        help_text="Last device this contact was imported from (phonebook sync).",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "phone_number")
        ordering = ["name", "phone_number"]
        indexes = [
            models.Index(fields=["tenant", "source_device"]),
        ]

    def __str__(self) -> str:
        return self.name or self.phone_number


class ContactGroup(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="contact_groups"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    members = models.ManyToManyField(Contact, related_name="groups", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "name")
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class Conversation(models.Model):
    """Thread keyed by normalized phone number within a tenant (optional project)."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="conversations"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    contact = models.ForeignKey(
        Contact,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversations",
    )
    phone_number = models.CharField(max_length=32, db_index=True)
    last_message_at = models.DateTimeField(null=True, blank=True)
    last_preview = models.CharField(max_length=255, blank=True, default="")
    unread_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("tenant", "phone_number", "project")
        ordering = ["-last_message_at", "-updated_at"]
        indexes = [
            models.Index(fields=["tenant", "-last_message_at"]),
        ]

    def __str__(self) -> str:
        return self.phone_number


class AutoReplyRule(models.Model):
    class MatchType(models.TextChoices):
        EXACT = "exact", "Exact"
        CONTAINS = "contains", "Contains"
        STARTS_WITH = "starts_with", "Starts with"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="auto_reply_rules"
    )
    project = models.ForeignKey(
        "projects.Project",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="auto_reply_rules",
    )
    name = models.CharField(max_length=255)
    keyword = models.CharField(max_length=128)
    match_type = models.CharField(
        max_length=16, choices=MatchType.choices, default=MatchType.CONTAINS
    )
    reply_body = models.TextField()
    priority = models.IntegerField(default=100)
    enabled = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-priority", "name"]
