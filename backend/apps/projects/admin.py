from django.contrib import admin

from .models import ApiKey, Project, ProjectDevice


class ProjectDeviceInline(admin.TabularInline):
    model = ProjectDevice
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tenant", "mode_default", "is_active")
    search_fields = ("name", "slug")
    list_filter = ("is_active", "mode_default")
    inlines = [ProjectDeviceInline]


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "key_prefix", "project", "revoked_at", "last_used_at")
    search_fields = ("name", "key_prefix")
    list_filter = ("revoked_at",)
