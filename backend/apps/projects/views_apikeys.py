from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.projects.models import ApiKey, Project
from apps.projects.serializers_apikeys import ApiKeyCreateSerializer, ApiKeySerializer
from apps.projects.services.apikeys import delete_api_key, revoke_api_key


class ProjectApiKeyListCreateView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "apikeys.write" if self.request.method == "POST" else "apikeys.read"
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
        keys = ApiKey.objects.filter(project=project)
        return Response({"results": ApiKeySerializer(keys, many=True).data})

    def post(self, request, project_id):
        project = self._project(request, project_id)
        if not project:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Project not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ApiKeyCreateSerializer(
            data=request.data, context={"project": project}
        )
        serializer.is_valid(raise_exception=True)
        api_key = serializer.save()
        data = ApiKeySerializer(api_key).data
        data["key"] = serializer.context["plaintext"]
        from apps.audit.services import log_audit

        log_audit(
            action="apikey.create",
            request=request,
            object_type="apikey",
            object_id=str(api_key.id),
            after={"name": api_key.name, "prefix": api_key.key_prefix},
        )
        return Response(data, status=status.HTTP_201_CREATED)


class ProjectApiKeyRevokeView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "apikeys.write"

    def post(self, request, project_id, key_id):
        api_key = (
            ApiKey.objects.filter(
                project_id=project_id,
                project__tenant=request.tenant,
                id=key_id,
            )
            .select_related("project")
            .first()
        )
        if not api_key:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "API key not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        revoke_api_key(api_key)
        from apps.audit.services import log_audit

        log_audit(
            action="apikey.revoke",
            request=request,
            object_type="apikey",
            object_id=str(api_key.id),
            after={"revoked": True, "prefix": api_key.key_prefix},
        )
        return Response(ApiKeySerializer(api_key).data)


class ProjectApiKeyDeleteView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "apikeys.write"

    def delete(self, request, project_id, key_id):
        api_key = (
            ApiKey.objects.filter(
                project_id=project_id,
                project__tenant=request.tenant,
                id=key_id,
            )
            .select_related("project")
            .first()
        )
        if not api_key:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "API key not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        prefix = api_key.key_prefix
        name = api_key.name
        key_pk = str(api_key.id)
        delete_api_key(api_key)
        from apps.audit.services import log_audit

        log_audit(
            action="apikey.delete",
            request=request,
            object_type="apikey",
            object_id=key_pk,
            after={"deleted": True, "prefix": prefix, "name": name},
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
