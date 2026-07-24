from rest_framework import serializers

from apps.plugins.models import PluginInstallation
from apps.plugins.registry import get_registry


class PluginCatalogSerializer(serializers.Serializer):
    id = serializers.CharField()
    name = serializers.CharField()
    version = serializers.CharField()
    hooks = serializers.ListField(child=serializers.CharField())
    config_schema = serializers.DictField()
    plugin_api = serializers.CharField()
    installed = serializers.BooleanField()
    enabled = serializers.BooleanField(allow_null=True)
    config = serializers.DictField(required=False)


class PluginInstallationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PluginInstallation
        fields = (
            "id",
            "plugin_id",
            "enabled",
            "config",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "plugin_id", "created_at", "updated_at")


class PluginInstallCreateSerializer(serializers.Serializer):
    plugin_id = serializers.CharField()
    config = serializers.DictField(required=False)
    enabled = serializers.BooleanField(required=False, default=True)

    def validate_plugin_id(self, value):
        if get_registry().get(value) is None:
            raise serializers.ValidationError("Unknown plugin")
        return value
