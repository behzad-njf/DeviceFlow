from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework import serializers

from apps.messaging.models import InboundMessage, Message, MessageAttempt


class MessageSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True, default=None)
    project_name = serializers.CharField(source="project.name", read_only=True, default=None)
    sim_slot_index = serializers.IntegerField(
        source="sim_slot.slot_index", read_only=True, default=None
    )

    class Meta:
        model = Message
        fields = (
            "id",
            "to_number",
            "body",
            "status",
            "mode",
            "priority",
            "project",
            "project_name",
            "device",
            "device_name",
            "sim_slot",
            "sim_slot_index",
            "retry_count",
            "max_retries",
            "latency_ms",
            "error_code",
            "error_message",
            "client_ref",
            "sent_at",
            "delivered_at",
            "failed_at",
            "next_retry_at",
            "created_at",
            "updated_at",
        )


class SendMessageSerializer(serializers.Serializer):
    to = serializers.CharField(max_length=32)
    text = serializers.CharField(required=False, allow_blank=True)
    template_id = serializers.UUIDField(required=False)
    vars = serializers.DictField(child=serializers.CharField(), required=False)
    project = serializers.CharField(required=False, allow_blank=True)
    device = serializers.CharField(required=False, allow_blank=True)
    mode = serializers.ChoiceField(
        choices=Message.Mode.choices, required=False, default=Message.Mode.GENERAL
    )
    sim_slot = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=2
    )
    client_ref = serializers.CharField(required=False, allow_blank=True, max_length=128)
    meta = serializers.DictField(required=False)
    scheduled_at = serializers.DateTimeField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("text") and not attrs.get("template_id"):
            raise serializers.ValidationError("Provide text or template_id")
        return attrs


class MessageStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=[
            Message.Status.SENDING,
            Message.Status.SENT,
            Message.Status.DELIVERED,
            Message.Status.FAILED,
        ]
    )
    error_code = serializers.CharField(required=False, allow_blank=True)
    error_message = serializers.CharField(required=False, allow_blank=True)
    latency_ms = serializers.IntegerField(required=False, allow_null=True)
    sim_slot = serializers.IntegerField(required=False, allow_null=True)


class InboundCreateSerializer(serializers.Serializer):
    from_number = serializers.CharField(max_length=32)
    body = serializers.CharField()
    received_at = serializers.CharField(required=False, allow_blank=True)
    sim_slot = serializers.IntegerField(required=False, allow_null=True)
    meta = serializers.DictField(required=False)

    def to_internal_value(self, data):
        data = data.copy() if hasattr(data, "copy") else dict(data)
        if "from" in data and "from_number" not in data:
            data["from_number"] = data["from"]
        return super().to_internal_value(data)

    def validate(self, attrs):
        raw = attrs.get("received_at")
        if raw:
            parsed = parse_datetime(raw)
            if parsed is None:
                raise serializers.ValidationError({"received_at": "Invalid datetime"})
            attrs["received_at"] = parsed
        else:
            attrs["received_at"] = timezone.now()
        return attrs


class InboundMessageSerializer(serializers.ModelSerializer):
    device_name = serializers.CharField(source="device.name", read_only=True)

    class Meta:
        model = InboundMessage
        fields = (
            "id",
            "from_number",
            "body",
            "device",
            "device_name",
            "project",
            "sim_slot",
            "received_at",
            "read_at",
            "created_at",
        )


class MessageAttemptSerializer(serializers.ModelSerializer):
    class Meta:
        model = MessageAttempt
        fields = ("id", "device", "started_at", "finished_at", "result", "detail")
