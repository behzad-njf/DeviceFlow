from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from apps.tenants.models import Membership

from .serializers import (
    LoginSerializer,
    MembershipSerializer,
    RegisterSerializer,
    TenantBriefSerializer,
    UserSerializer,
)

User = get_user_model()


def issue_tokens(user, tenant, role: str) -> dict:
    refresh = RefreshToken.for_user(user)
    refresh["tenant_id"] = str(tenant.id)
    refresh["role"] = role
    refresh["locale"] = user.locale
    access = refresh.access_token
    access["tenant_id"] = str(tenant.id)
    access["role"] = role
    access["locale"] = user.locale
    return {
        "access": str(access),
        "refresh": str(refresh),
    }


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = serializer.save()
        tokens = issue_tokens(
            result["user"], result["tenant"], result["membership"].role
        )
        return Response(
            {
                **tokens,
                "user": UserSerializer(result["user"]).data,
                "tenant": TenantBriefSerializer(result["tenant"]).data,
                "role": result["membership"].role,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        tenant = serializer.validated_data["tenant"]
        membership = serializer.validated_data["membership"]
        tokens = issue_tokens(user, tenant, membership.role)
        return Response(
            {
                **tokens,
                "user": UserSerializer(user).data,
                "tenant": TenantBriefSerializer(tenant).data,
                "role": membership.role,
            }
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh = request.data.get("refresh")
        if not refresh:
            return Response(
                {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "refresh token is required",
                        "details": None,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh)
            token.blacklist()
        except Exception:
            return Response(
                {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "Invalid refresh token",
                        "details": None,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        memberships = (
            Membership.objects.select_related("tenant")
            .filter(user=request.user, is_active=True)
            .order_by("tenant__name")
        )
        return Response(
            {
                "user": UserSerializer(request.user).data,
                "memberships": MembershipSerializer(memberships, many=True).data,
            }
        )


class RefreshView(TokenRefreshView):
    permission_classes = [AllowAny]
