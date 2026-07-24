from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.automations.models import AutomationRule
from apps.automations.serializers import AutomationRuleSerializer
from apps.common.permissions import RequirePermission


class AutomationRuleListCreateView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "settings.write" if self.request.method == "POST" else "tenant.read"
        )
        # Admins have settings.write; developers get webhooks.write as proxy
        if self.request.method == "POST":
            self.required_permission = "webhooks.write"
        else:
            self.required_permission = "webhooks.read"
        return super().get_permissions()

    def get(self, request):
        qs = AutomationRule.objects.filter(tenant=request.tenant)
        return Response({"results": AutomationRuleSerializer(qs, many=True).data})

    def post(self, request):
        serializer = AutomationRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = AutomationRule.objects.create(
            tenant=request.tenant, **serializer.validated_data
        )
        return Response(
            AutomationRuleSerializer(rule).data, status=status.HTTP_201_CREATED
        )


class AutomationRuleDetailView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "webhooks.write"
            if self.request.method in {"PATCH", "DELETE"}
            else "webhooks.read"
        )
        return super().get_permissions()

    def _get(self, request, rule_id):
        return AutomationRule.objects.filter(tenant=request.tenant, id=rule_id).first()

    def patch(self, request, rule_id):
        rule = self._get(request, rule_id)
        if not rule:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = AutomationRuleSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, rule_id):
        rule = self._get(request, rule_id)
        if not rule:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
