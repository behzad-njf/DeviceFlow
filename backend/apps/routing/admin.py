from django.contrib import admin

from .models import OperatorPrefix, RoutingRule, TenantRoutingConfig


@admin.register(OperatorPrefix)
class OperatorPrefixAdmin(admin.ModelAdmin):
    list_display = ("prefix", "operator", "country", "is_active")
    list_filter = ("country", "operator", "is_active")
    search_fields = ("prefix", "operator")


@admin.register(RoutingRule)
class RoutingRuleAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "priority", "enabled", "project")
    list_filter = ("enabled",)
    search_fields = ("name",)


@admin.register(TenantRoutingConfig)
class TenantRoutingConfigAdmin(admin.ModelAdmin):
    list_display = ("tenant", "lb_strategy", "ha_enabled", "updated_at")
