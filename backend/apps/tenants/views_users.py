from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.email_utils import normalize_email_identity
from apps.accounts.models import User
from apps.audit.services import log_audit
from apps.common.permissions import RequirePermission
from apps.tenants.models import Membership, TenantInvite
from apps.tenants.serializers_users import (
    InviteAcceptSerializer,
    InviteCreateSerializer,
    InviteSerializer,
    MembershipSerializer,
)
from apps.tenants.services_invites import accept_invite, create_invite


class MembershipListView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "users.read"

    def get(self, request):
        qs = Membership.objects.filter(tenant=request.tenant).select_related("user")
        return Response({"results": MembershipSerializer(qs, many=True).data})


class MembershipDetailView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "users.manage"

    def patch(self, request, membership_id):
        membership = (
            Membership.objects.filter(tenant=request.tenant, id=membership_id)
            .select_related("user")
            .first()
        )
        if not membership:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Membership not found",
                        "details": None,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        before = {"role": membership.role, "is_active": membership.is_active}
        if "role" in request.data:
            membership.role = request.data["role"]
        if "is_active" in request.data:
            membership.is_active = bool(request.data["is_active"])
        membership.save()
        log_audit(
            action="membership.update",
            request=request,
            object_type="membership",
            object_id=str(membership.id),
            before=before,
            after={"role": membership.role, "is_active": membership.is_active},
        )
        return Response(MembershipSerializer(membership).data)


class UserInviteView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "users.invite"

    def get(self, request):
        qs = TenantInvite.objects.filter(tenant=request.tenant)[:100]
        return Response({"results": InviteSerializer(qs, many=True).data})

    def post(self, request):
        serializer = InviteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        invite, token = create_invite(
            tenant=request.tenant,
            email=serializer.validated_data["email"],
            role=serializer.validated_data["role"],
            invited_by=request.user,
        )
        log_audit(
            action="invite.create",
            request=request,
            object_type="invite",
            object_id=str(invite.id),
            after={"email": invite.email, "role": invite.role},
        )
        data = InviteSerializer(invite).data
        data["token"] = token
        data["accept_hint"] = (
            "POST /api/v1/invites/accept/ with {token, email, password, name?}"
        )
        return Response(data, status=status.HTTP_201_CREATED)


class InviteAcceptView(APIView):
    """
    Accept an invite. Authenticated users may send only {token}.
    New users send {token, email, password, name?} matching the invite email.
    """

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = InviteAcceptSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        token = data["token"]

        user = None
        # Optional bearer for already-authenticated accept
        auth = request.headers.get("Authorization") or ""
        if auth.startswith("Bearer ") and request.user and request.user.is_authenticated:
            user = request.user
        else:
            from rest_framework_simplejwt.authentication import JWTAuthentication

            try:
                result = JWTAuthentication().authenticate(request)
                if result:
                    user = result[0]
            except Exception:
                user = None

        if user is None:
            email = normalize_email_identity(data.get("email") or "")
            password = data.get("password") or ""
            if not email or not password:
                return Response(
                    {
                        "error": {
                            "code": "BAD_REQUEST",
                            "message": "email and password required to accept invite",
                            "details": None,
                        }
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
            existing = User.objects.filter(email=email).first()
            if existing:
                if not existing.check_password(password):
                    return Response(
                        {
                            "error": {
                                "code": "UNAUTHORIZED",
                                "message": "Invalid credentials",
                                "details": None,
                            }
                        },
                        status=status.HTTP_401_UNAUTHORIZED,
                    )
                user = existing
            else:
                user = User.objects.create_user(
                    email=email,
                    password=password,
                    name=data.get("name") or email.split("@")[0],
                )

        try:
            membership = accept_invite(token=token, user=user)
        except ValueError as exc:
            return Response(
                {
                    "error": {
                        "code": "UNPROCESSABLE",
                        "message": str(exc),
                        "details": None,
                    }
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        log_audit(
            action="invite.accept",
            tenant=membership.tenant,
            actor_user=user,
            object_type="membership",
            object_id=str(membership.id),
            after={"role": membership.role, "email": user.email},
        )
        return Response(MembershipSerializer(membership).data)
