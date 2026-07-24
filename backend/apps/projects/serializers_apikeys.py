from rest_framework import serializers

from apps.projects.models import ApiKey
from apps.projects.services.apikeys import DEFAULT_SCOPES, create_api_key


class ApiKeySerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(source="project.id", read_only=True)
    project_slug = serializers.CharField(source="project.slug", read_only=True)
    is_active = serializers.BooleanField(read_only=True)

    class Meta:
        model = ApiKey
        fields = (
            "id",
            "project_id",
            "project_slug",
            "name",
            "key_prefix",
            "scopes",
            "ip_whitelist",
            "last_used_at",
            "usage_count",
            "messages_sent",
            "revoked_at",
            "is_active",
            "created_at",
        )


class ApiKeyCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=255)
    scopes = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        allow_empty=True,
    )
    ip_whitelist = serializers.ListField(
        child=serializers.CharField(max_length=64),
        required=False,
        allow_empty=True,
    )

    def create(self, validated_data):
        project = self.context["project"]
        api_key, plaintext = create_api_key(
            project=project,
            name=validated_data["name"],
            scopes=validated_data.get("scopes") or list(DEFAULT_SCOPES),
            ip_whitelist=validated_data.get("ip_whitelist") or [],
        )
        self.context["plaintext"] = plaintext
        return api_key
