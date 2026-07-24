from rest_framework import serializers

from apps.common.permissions import ROLE_PERMISSIONS

from .models import Tenant


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = (
            "id",
            "name",
            "slug",
            "plan",
            "settings",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class TenantMeSerializer(serializers.Serializer):
    tenant = TenantSerializer()
    role = serializers.CharField()
    permissions = serializers.ListField(child=serializers.CharField())

    @staticmethod
    def from_membership(membership):
        return {
            "tenant": TenantSerializer(membership.tenant).data,
            "role": membership.role,
            "permissions": sorted(ROLE_PERMISSIONS.get(membership.role, set())),
        }
