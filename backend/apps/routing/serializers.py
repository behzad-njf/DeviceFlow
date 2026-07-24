from rest_framework import serializers

from apps.routing.models import OperatorPrefix, RoutingRule, TenantRoutingConfig


class RoutingRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoutingRule
        fields = (
            "id",
            "project",
            "name",
            "priority",
            "match",
            "action",
            "enabled",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class RoutingRuleCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoutingRule
        fields = ("project", "name", "priority", "match", "action", "enabled")

    def create(self, validated_data):
        tenant = self.context["tenant"]
        return RoutingRule.objects.create(tenant=tenant, **validated_data)


class TenantRoutingConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantRoutingConfig
        fields = (
            "lb_strategy",
            "ha_enabled",
            "min_health_score",
            "min_battery_percent",
            "rate_limit_per_minute",
            "rate_limit_per_hour",
            "rate_limit_per_day",
            "project_rate_limit_per_minute",
            "otp_queue_weight",
            "marketing_queue_weight",
            "marketing_jitter_max_seconds",
            "sim_daily_quota_default",
            "adaptive_throttle_enabled",
            "adaptive_failure_threshold",
            "updated_at",
        )
        read_only_fields = ("updated_at",)


class OperatorPrefixSerializer(serializers.ModelSerializer):
    class Meta:
        model = OperatorPrefix
        fields = ("id", "prefix", "operator", "country", "is_active")
