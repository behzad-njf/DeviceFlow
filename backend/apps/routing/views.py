from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.routing.models import OperatorPrefix, RoutingRule
from apps.routing.services.engine import get_or_create_config

from .serializers import (
    OperatorPrefixSerializer,
    RoutingRuleCreateSerializer,
    RoutingRuleSerializer,
    TenantRoutingConfigSerializer,
)


class RoutingRuleListCreateView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "routing.write" if self.request.method == "POST" else "routing.read"
        )
        return super().get_permissions()

    def get(self, request):
        qs = RoutingRule.objects.filter(tenant=request.tenant)
        if project := request.query_params.get("project"):
            qs = qs.filter(project_id=project)
        return Response({"results": RoutingRuleSerializer(qs, many=True).data})

    def post(self, request):
        serializer = RoutingRuleCreateSerializer(
            data=request.data, context={"tenant": request.tenant}
        )
        serializer.is_valid(raise_exception=True)
        rule = serializer.save()
        return Response(
            RoutingRuleSerializer(rule).data, status=status.HTTP_201_CREATED
        )


class RoutingRuleDetailView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "routing.write"
            if self.request.method in {"PATCH", "DELETE"}
            else "routing.read"
        )
        return super().get_permissions()

    def _get(self, request, rule_id):
        return RoutingRule.objects.filter(tenant=request.tenant, id=rule_id).first()

    def get(self, request, rule_id):
        rule = self._get(request, rule_id)
        if not rule:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Routing rule not found",
                        "details": None,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(RoutingRuleSerializer(rule).data)

    def patch(self, request, rule_id):
        rule = self._get(request, rule_id)
        if not rule:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Routing rule not found",
                        "details": None,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = RoutingRuleSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, rule_id):
        rule = self._get(request, rule_id)
        if not rule:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Routing rule not found",
                        "details": None,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class RoutingConfigView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "routing.write" if self.request.method == "PATCH" else "routing.read"
        )
        return super().get_permissions()

    def get(self, request):
        config = get_or_create_config(request.tenant)
        return Response(TenantRoutingConfigSerializer(config).data)

    def patch(self, request):
        config = get_or_create_config(request.tenant)
        serializer = TenantRoutingConfigSerializer(
            config, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class OperatorPrefixListView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "routing.read"

    def get(self, request):
        qs = OperatorPrefix.objects.filter(is_active=True)
        country = request.query_params.get("country")
        if country:
            qs = qs.filter(country=country.upper())
        return Response({"results": OperatorPrefixSerializer(qs, many=True).data})
