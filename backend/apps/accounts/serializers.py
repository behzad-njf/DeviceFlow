from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.accounts.email_utils import normalize_email_identity
from apps.tenants.models import Membership, Tenant
from apps.tenants.services import create_tenant_with_owner

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "email", "name", "locale", "theme", "date_joined")
        read_only_fields = fields


class TenantBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ("id", "name", "slug", "plan", "is_active")
        read_only_fields = fields


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    name = serializers.CharField(max_length=255, required=False, allow_blank=True)
    tenant_name = serializers.CharField(max_length=255)
    tenant_slug = serializers.SlugField(max_length=64, required=False)
    locale = serializers.ChoiceField(choices=["en", "fa"], default="en")

    def validate_email(self, value):
        email = normalize_email_identity(value)
        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    def create(self, validated_data):
        with transaction.atomic():
            user = User.objects.create_user(
                email=validated_data["email"],
                password=validated_data["password"],
                name=validated_data.get("name") or "",
                locale=validated_data.get("locale", "en"),
            )
            tenant = create_tenant_with_owner(
                owner=user,
                name=validated_data["tenant_name"],
                slug=validated_data.get("tenant_slug"),
            )
            membership = Membership.objects.get(user=user, tenant=tenant)
        return {"user": user, "tenant": tenant, "membership": membership}


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    tenant_slug = serializers.SlugField(required=False, allow_blank=True)

    def validate(self, attrs):
        email = normalize_email_identity(attrs["email"])
        password = attrs["password"]
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist as exc:
            raise serializers.ValidationError("Invalid email or password.") from exc
        if not user.is_active or not user.check_password(password):
            raise serializers.ValidationError("Invalid email or password.")

        memberships = (
            Membership.objects.select_related("tenant")
            .filter(user=user, is_active=True, tenant__is_active=True)
            .order_by("tenant__name")
        )
        if not memberships.exists():
            raise serializers.ValidationError("User has no active tenant membership.")

        tenant_slug = attrs.get("tenant_slug") or ""
        if tenant_slug:
            membership = memberships.filter(tenant__slug=tenant_slug).first()
            if membership is None:
                raise serializers.ValidationError("Tenant not found for this user.")
        else:
            membership = memberships.first()

        attrs["user"] = user
        attrs["membership"] = membership
        attrs["tenant"] = membership.tenant
        return attrs


class MembershipSerializer(serializers.ModelSerializer):
    tenant = TenantBriefSerializer(read_only=True)

    class Meta:
        model = Membership
        fields = ("id", "role", "tenant", "is_active", "created_at")
        read_only_fields = fields
