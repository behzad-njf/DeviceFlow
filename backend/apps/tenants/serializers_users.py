from rest_framework import serializers

from apps.tenants.models import Membership, Role, TenantInvite


class MembershipSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    name = serializers.CharField(source="user.name", read_only=True)

    class Meta:
        model = Membership
        fields = (
            "id",
            "email",
            "name",
            "role",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "email", "name", "created_at", "updated_at")


class InviteCreateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.ChoiceField(choices=Role.choices, default=Role.VIEWER)


class InviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TenantInvite
        fields = (
            "id",
            "email",
            "role",
            "expires_at",
            "accepted_at",
            "revoked_at",
            "created_at",
        )


class InviteAcceptSerializer(serializers.Serializer):
    token = serializers.CharField()
    email = serializers.EmailField(required=False)
    password = serializers.CharField(required=False, allow_blank=True)
    name = serializers.CharField(required=False, allow_blank=True)
