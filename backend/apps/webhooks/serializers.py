from rest_framework import serializers

from apps.common.crypto import generate_webhook_secret
from apps.webhooks.models import WebhookDelivery, WebhookEndpoint
from apps.webhooks.services.delivery import ALL_EVENTS, is_safe_webhook_url


class WebhookEndpointSerializer(serializers.ModelSerializer):
    project_id = serializers.UUIDField(source="project.id", read_only=True)
    secret = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = WebhookEndpoint
        fields = (
            "id",
            "project_id",
            "url",
            "secret",
            "events",
            "is_active",
            "failure_count",
            "description",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "failure_count", "created_at", "updated_at")

    def validate_url(self, value):
        if not is_safe_webhook_url(value):
            raise serializers.ValidationError("Webhook URL is not allowed")
        return value

    def validate_events(self, value):
        if not value:
            return list(ALL_EVENTS)
        invalid = [e for e in value if e != "*" and e not in ALL_EVENTS]
        if invalid:
            raise serializers.ValidationError(f"Unknown events: {invalid}")
        return value


class WebhookEndpointCreateSerializer(WebhookEndpointSerializer):
    def create(self, validated_data):
        project = self.context["project"]
        secret = validated_data.pop("secret", None) or generate_webhook_secret()
        endpoint = WebhookEndpoint.objects.create(
            project=project, secret=secret, **validated_data
        )
        self.context["plaintext_secret"] = secret
        return endpoint


class WebhookDeliverySerializer(serializers.ModelSerializer):
    endpoint_url = serializers.CharField(source="endpoint.url", read_only=True)

    class Meta:
        model = WebhookDelivery
        fields = (
            "id",
            "endpoint",
            "endpoint_url",
            "event_type",
            "payload",
            "status",
            "attempts",
            "response_code",
            "response_body",
            "next_retry_at",
            "created_at",
            "updated_at",
        )
