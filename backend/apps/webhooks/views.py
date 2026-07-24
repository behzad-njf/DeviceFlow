from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.projects.models import Project
from apps.webhooks.models import WebhookDelivery, WebhookEndpoint
from apps.webhooks.serializers import (
    WebhookDeliverySerializer,
    WebhookEndpointCreateSerializer,
    WebhookEndpointSerializer,
)
from apps.webhooks.services.delivery import redeliver


class ProjectWebhookListCreateView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "webhooks.write" if self.request.method == "POST" else "webhooks.read"
        )
        return super().get_permissions()

    def _project(self, request, project_id):
        return Project.objects.filter(tenant=request.tenant, id=project_id).first()

    def get(self, request, project_id):
        project = self._project(request, project_id)
        if not project:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Project not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        qs = WebhookEndpoint.objects.filter(project=project)
        return Response({"results": WebhookEndpointSerializer(qs, many=True).data})

    def post(self, request, project_id):
        project = self._project(request, project_id)
        if not project:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Project not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = WebhookEndpointCreateSerializer(
            data=request.data, context={"project": project}
        )
        serializer.is_valid(raise_exception=True)
        endpoint = serializer.save()
        data = WebhookEndpointSerializer(endpoint).data
        data["secret"] = serializer.context["plaintext_secret"]
        return Response(data, status=status.HTTP_201_CREATED)


class ProjectWebhookDetailView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "webhooks.write"
            if self.request.method in {"PATCH", "DELETE"}
            else "webhooks.read"
        )
        return super().get_permissions()

    def _get(self, request, project_id, endpoint_id):
        return WebhookEndpoint.objects.filter(
            project_id=project_id,
            project__tenant=request.tenant,
            id=endpoint_id,
        ).first()

    def get(self, request, project_id, endpoint_id):
        endpoint = self._get(request, project_id, endpoint_id)
        if not endpoint:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Webhook not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(WebhookEndpointSerializer(endpoint).data)

    def patch(self, request, project_id, endpoint_id):
        endpoint = self._get(request, project_id, endpoint_id)
        if not endpoint:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Webhook not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = WebhookEndpointSerializer(endpoint, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, project_id, endpoint_id):
        endpoint = self._get(request, project_id, endpoint_id)
        if not endpoint:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Webhook not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        endpoint.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class WebhookDeliveryListView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "webhooks.read"

    def get(self, request):
        qs = WebhookDelivery.objects.filter(
            endpoint__project__tenant=request.tenant
        ).select_related("endpoint")
        if project := request.query_params.get("project"):
            qs = qs.filter(endpoint__project_id=project)
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        return Response(
            {"results": WebhookDeliverySerializer(qs[:100], many=True).data}
        )


class WebhookDeliveryRedeliverView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "webhooks.write"

    def post(self, request, delivery_id):
        delivery = (
            WebhookDelivery.objects.filter(
                id=delivery_id, endpoint__project__tenant=request.tenant
            )
            .select_related("endpoint")
            .first()
        )
        if not delivery:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Delivery not found",
                        "details": None,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        delivery = redeliver(delivery)
        return Response(WebhookDeliverySerializer(delivery).data)
