from rest_framework import serializers

from apps.notifications.models import NotificationChannel, NotificationLog, NotificationRule


class NotificationChannelSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationChannel
        fields = (
            "id",
            "channel_type",
            "name",
            "enabled",
            "config",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class NotificationRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationRule
        fields = (
            "id",
            "name",
            "event",
            "channels",
            "cooldown_sec",
            "enabled",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = (
            "id",
            "event",
            "channel",
            "severity",
            "title",
            "body",
            "status",
            "error",
            "meta",
            "created_at",
        )
