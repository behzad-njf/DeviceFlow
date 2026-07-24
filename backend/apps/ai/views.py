from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ai.services.anomaly import detect_tenant_anomalies
from apps.ai.services.drafts import suggest_inbox_draft
from apps.ai.services.routing_assist import suggest_routing_rules
from apps.common.permissions import RequirePermission
from apps.contacts.models import Conversation


class AnomalyScanView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "analytics.read"

    def get(self, request):
        findings = detect_tenant_anomalies(request.tenant, notify_on_find=False)
        return Response({"results": findings, "count": len(findings)})

    def post(self, request):
        # Demo path: scan + fire notification alerts
        findings = detect_tenant_anomalies(request.tenant, notify_on_find=True)
        return Response({"results": findings, "count": len(findings)})


class RoutingSuggestionsView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "routing.read"

    def get(self, request):
        hours = min(int(request.query_params.get("hours", 24)), 168)
        suggestions = suggest_routing_rules(tenant=request.tenant, hours=hours)
        return Response({"results": suggestions})


class InboxDraftView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "inbound.read"

    def post(self, request, conversation_id):
        conversation = Conversation.objects.filter(
            tenant=request.tenant, id=conversation_id
        ).first()
        if not conversation:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Conversation not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        result = suggest_inbox_draft(conversation=conversation)
        return Response(result)
