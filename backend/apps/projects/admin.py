from django.contrib import admin

from .models import ApiKey, Project, ProjectDevice, ProjectRouteBinding


class ProjectDeviceInline(admin.TabularInline):
    model = ProjectDevice
    extra = 0


class ProjectRouteBindingInline(admin.TabularInline):
    model = ProjectRouteBinding
    extra = 0
    autocomplete_fields = ("device",)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "tenant", "mode_default", "is_active")
    search_fields = ("name", "slug")
    list_filter = ("is_active", "mode_default")
    inlines = [ProjectDeviceInline, ProjectRouteBindingInline]


@admin.register(ProjectRouteBinding)
class ProjectRouteBindingAdmin(admin.ModelAdmin):
    list_display = (
        "route_key",
        "label",
        "project",
        "device",
        "preferred_sim_slot",
        "is_active",
    )
    search_fields = ("route_key", "label", "project__name", "project__slug")
    list_filter = ("is_active",)
    autocomplete_fields = ("project", "device")


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ("name", "key_prefix", "project", "revoked_at", "last_used_at")
    search_fields = ("name", "key_prefix")
    list_filter = ("revoked_at",)
