from rest_framework import serializers

from apps.audit.models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    actor_email = serializers.CharField(
        source="actor_user.email", read_only=True, default=None
    )

    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor_type",
            "actor_label",
            "actor_email",
            "action",
            "object_type",
            "object_id",
            "before",
            "after",
            "ip",
            "user_agent",
            "created_at",
        )
