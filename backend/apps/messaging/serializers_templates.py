from rest_framework import serializers

from apps.messaging.models import MessageTemplate
from apps.messaging.services.templates import extract_variables, render_template


class MessageTemplateSerializer(serializers.ModelSerializer):
    variables = serializers.SerializerMethodField()

    class Meta:
        model = MessageTemplate
        fields = (
            "id",
            "project",
            "name",
            "body",
            "channel",
            "is_active",
            "variables",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at", "variables")

    def get_variables(self, obj):
        return extract_variables(obj.body)


class MessageTemplateCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageTemplate
        fields = ("project", "name", "body", "channel", "is_active")

    def create(self, validated_data):
        tenant = self.context["tenant"]
        return MessageTemplate.objects.create(tenant=tenant, **validated_data)


class TemplateRenderSerializer(serializers.Serializer):
    vars = serializers.DictField(child=serializers.CharField(), required=False)

    def render(self, template: MessageTemplate) -> str:
        return render_template(template.body, self.validated_data.get("vars") or {})
