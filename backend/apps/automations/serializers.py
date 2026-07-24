from rest_framework import serializers

from apps.automations.models import AutomationRule


class AutomationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutomationRule
        fields = (
            "id",
            "project",
            "name",
            "priority",
            "enabled",
            "match",
            "action",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")
