from rest_framework.response import Response
from rest_framework.views import APIView

from apps.audit.models import AuditLog
from apps.audit.serializers import AuditLogSerializer
from apps.common.permissions import RequirePermission


class AuditLogListView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "audit.read"

    def get(self, request):
        qs = AuditLog.objects.filter(tenant=request.tenant)
        if action := request.query_params.get("action"):
            qs = qs.filter(action=action)
        if object_type := request.query_params.get("object_type"):
            qs = qs.filter(object_type=object_type)
        return Response({"results": AuditLogSerializer(qs[:200], many=True).data})
