from django.contrib import admin

from .models import Device, DeviceEvent, SimSlot


class SimSlotInline(admin.TabularInline):
    model = SimSlot
    extra = 0


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "status", "agent_version", "last_seen_at")
    list_filter = ("status",)
    search_fields = ("name",)
    inlines = [SimSlotInline]


@admin.register(DeviceEvent)
class DeviceEventAdmin(admin.ModelAdmin):
    list_display = ("device", "type", "created_at")
    list_filter = ("type",)
