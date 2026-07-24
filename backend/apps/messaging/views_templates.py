from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.messaging.models import MessageTemplate
from apps.messaging.serializers_templates import (
    MessageTemplateCreateSerializer,
    MessageTemplateSerializer,
    TemplateRenderSerializer,
)


class TemplateListCreateView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "templates.write" if self.request.method == "POST" else "templates.read"
        )
        return super().get_permissions()

    def get(self, request):
        qs = MessageTemplate.objects.filter(tenant=request.tenant)
        if project := request.query_params.get("project"):
            qs = qs.filter(project_id=project)
        return Response({"results": MessageTemplateSerializer(qs, many=True).data})

    def post(self, request):
        serializer = MessageTemplateCreateSerializer(
            data=request.data, context={"tenant": request.tenant}
        )
        serializer.is_valid(raise_exception=True)
        template = serializer.save()
        return Response(
            MessageTemplateSerializer(template).data, status=status.HTTP_201_CREATED
        )


class TemplateDetailView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "templates.write"
            if self.request.method in {"PATCH", "DELETE"}
            else "templates.read"
        )
        return super().get_permissions()

    def _get(self, request, template_id):
        return MessageTemplate.objects.filter(
            tenant=request.tenant, id=template_id
        ).first()

    def get(self, request, template_id):
        template = self._get(request, template_id)
        if not template:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Template not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(MessageTemplateSerializer(template).data)

    def patch(self, request, template_id):
        template = self._get(request, template_id)
        if not template:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Template not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MessageTemplateSerializer(template, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, template_id):
        template = self._get(request, template_id)
        if not template:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Template not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        template.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class TemplateRenderView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "templates.read"

    def post(self, request, template_id):
        template = MessageTemplate.objects.filter(
            tenant=request.tenant, id=template_id
        ).first()
        if not template:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Template not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = TemplateRenderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            text = serializer.render(template)
        except ValueError as exc:
            return Response(
                {"error": {"code": "UNPROCESSABLE", "message": str(exc), "details": None}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response({"text": text, "variables": serializer.validated_data.get("vars") or {}})
