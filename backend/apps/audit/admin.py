from django.contrib import admin

from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("action", "object_type", "object_id", "actor_label", "tenant", "created_at")
    list_filter = ("action", "actor_type")
    search_fields = ("action", "object_id", "actor_label")
    readonly_fields = [f.name for f in AuditLog._meta.fields]
