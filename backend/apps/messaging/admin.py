from django.contrib import admin

from .models import (
    BulkCampaign,
    BulkCampaignItem,
    ExportJob,
    IdempotencyRecord,
    InboundMessage,
    Message,
    MessageAttempt,
    MessageTemplate,
)


class MessageAttemptInline(admin.TabularInline):
    model = MessageAttempt
    extra = 0
    readonly_fields = ("started_at", "finished_at", "result", "detail", "device")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("to_number", "status", "device", "project", "created_at")
    list_filter = ("status", "mode")
    search_fields = ("to_number", "body", "client_ref")
    inlines = [MessageAttemptInline]


@admin.register(InboundMessage)
class InboundMessageAdmin(admin.ModelAdmin):
    list_display = ("from_number", "device", "received_at")
    search_fields = ("from_number", "body")


@admin.register(MessageTemplate)
class MessageTemplateAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "project", "channel", "is_active")
    search_fields = ("name", "body")


@admin.register(IdempotencyRecord)
class IdempotencyRecordAdmin(admin.ModelAdmin):
    list_display = ("key", "tenant", "response_status", "created_at")
    search_fields = ("key",)


class BulkCampaignItemInline(admin.TabularInline):
    model = BulkCampaignItem
    extra = 0
    readonly_fields = ("to_number", "status", "error", "message")


@admin.register(BulkCampaign)
class BulkCampaignAdmin(admin.ModelAdmin):
    list_display = ("name", "status", "total", "sent", "failed", "tenant")
    list_filter = ("status",)
    inlines = [BulkCampaignItemInline]


@admin.register(ExportJob)
class ExportJobAdmin(admin.ModelAdmin):
    list_display = ("export_type", "format", "status", "row_count", "tenant", "created_at")
    list_filter = ("status", "format")
