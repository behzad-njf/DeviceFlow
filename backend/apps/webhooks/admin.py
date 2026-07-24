from django.contrib import admin

from .models import WebhookDelivery, WebhookEndpoint


@admin.register(WebhookEndpoint)
class WebhookEndpointAdmin(admin.ModelAdmin):
    list_display = ("url", "project", "is_active", "failure_count")
    list_filter = ("is_active",)


@admin.register(WebhookDelivery)
class WebhookDeliveryAdmin(admin.ModelAdmin):
    list_display = ("event_type", "status", "attempts", "endpoint", "created_at")
    list_filter = ("status", "event_type")
