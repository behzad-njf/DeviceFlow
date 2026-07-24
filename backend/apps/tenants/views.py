from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import IsTenantMember
from apps.tenants.models import Membership

from .serializers import TenantMeSerializer, TenantSerializer


class TenantMeView(APIView):
    """Return the current tenant context (from JWT claim or sole membership)."""

    permission_classes = [IsTenantMember]

    def get(self, request):
        tenant_id = request.auth.get("tenant_id") if request.auth else None
        if tenant_id:
            membership = (
                Membership.objects.select_related("tenant")
                .filter(user=request.user, tenant_id=tenant_id, is_active=True)
                .first()
            )
            if membership:
                request.membership = membership
                request.tenant = membership.tenant
        return Response(TenantMeSerializer.from_membership(request.membership))


class TenantListView(APIView):
    """List tenants the user belongs to."""

    def get(self, request):
        memberships = (
            Membership.objects.select_related("tenant")
            .filter(user=request.user, is_active=True)
            .order_by("tenant__name")
        )
        data = [
            {
                "tenant": TenantSerializer(m.tenant).data,
                "role": m.role,
            }
            for m in memberships
        ]
        return Response({"results": data})
