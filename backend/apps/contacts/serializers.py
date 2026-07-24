from rest_framework import serializers

from apps.contacts.models import AutoReplyRule, Contact, ContactGroup, Conversation
from apps.routing.services.operators import is_valid_phone_number, normalize_number


class ContactSerializer(serializers.ModelSerializer):
    source_device = serializers.UUIDField(
        source="source_device_id", allow_null=True, required=False, read_only=True
    )
    source_device_name = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = (
            "id",
            "phone_number",
            "name",
            "tags",
            "is_blacklisted",
            "is_whitelisted",
            "notes",
            "meta",
            "source_device",
            "source_device_name",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "id",
            "source_device",
            "source_device_name",
            "created_at",
            "updated_at",
        )

    def get_source_device_name(self, obj) -> str:
        device = getattr(obj, "source_device", None)
        return device.name if device else ""

    def validate_phone_number(self, value):
        if not is_valid_phone_number(value):
            raise serializers.ValidationError("Invalid phone number")
        return normalize_number(value)

    def create(self, validated_data):
        return Contact.objects.create(tenant=self.context["tenant"], **validated_data)


class ContactImportRowSerializer(serializers.Serializer):
    name = serializers.CharField(required=False, allow_blank=True, max_length=255, default="")
    phone = serializers.CharField(required=False, allow_blank=True, default="")
    phone_number = serializers.CharField(required=False, allow_blank=True, default="")
    number = serializers.CharField(required=False, allow_blank=True, default="")


class ContactImportPreviewSerializer(serializers.Serializer):
    device_id = serializers.UUIDField(required=False, allow_null=True)
    contacts = ContactImportRowSerializer(many=True)


class ContactImportConfirmSerializer(serializers.Serializer):
    device_id = serializers.UUIDField(required=False, allow_null=True)
    contacts = ContactImportRowSerializer(many=True)
    update_existing = serializers.BooleanField(required=False, default=True)


class ContactGroupSerializer(serializers.ModelSerializer):
    member_ids = serializers.ListField(
        child=serializers.UUIDField(), write_only=True, required=False
    )
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = ContactGroup
        fields = (
            "id",
            "name",
            "description",
            "member_ids",
            "member_count",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "member_count", "created_at", "updated_at")

    def get_member_count(self, obj):
        return obj.members.count()

    def create(self, validated_data):
        member_ids = validated_data.pop("member_ids", [])
        group = ContactGroup.objects.create(
            tenant=self.context["tenant"], **validated_data
        )
        if member_ids:
            members = Contact.objects.filter(
                tenant=self.context["tenant"], id__in=member_ids
            )
            group.members.set(members)
        return group

    def update(self, instance, validated_data):
        member_ids = validated_data.pop("member_ids", None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        if member_ids is not None:
            members = Contact.objects.filter(
                tenant=instance.tenant, id__in=member_ids
            )
            instance.members.set(members)
        return instance


class ConversationSerializer(serializers.ModelSerializer):
    contact_name = serializers.CharField(source="contact.name", read_only=True, default="")

    class Meta:
        model = Conversation
        fields = (
            "id",
            "project",
            "contact",
            "contact_name",
            "phone_number",
            "last_message_at",
            "last_preview",
            "unread_count",
            "created_at",
            "updated_at",
        )


class AutoReplyRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AutoReplyRule
        fields = (
            "id",
            "project",
            "name",
            "keyword",
            "match_type",
            "reply_body",
            "priority",
            "enabled",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def create(self, validated_data):
        return AutoReplyRule.objects.create(
            tenant=self.context["tenant"], **validated_data
        )
