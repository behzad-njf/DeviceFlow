from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.plugins.models import PluginInstallation
from apps.plugins.registry import PLUGIN_API_VERSION, get_registry
from apps.plugins.serializers import (
    PluginInstallCreateSerializer,
    PluginInstallationSerializer,
)


class PluginCatalogView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "plugins.manage"

    def get(self, request):
        registry = get_registry()
        installs = {
            row.plugin_id: row
            for row in PluginInstallation.objects.filter(tenant=request.tenant)
        }
        results = []
        for manifest in registry.list():
            inst = installs.get(manifest.id)
            results.append(
                {
                    "id": manifest.id,
                    "name": manifest.name,
                    "version": manifest.version,
                    "hooks": manifest.hooks,
                    "config_schema": manifest.config_schema,
                    "plugin_api": manifest.plugin_api,
                    "installed": inst is not None,
                    "enabled": inst.enabled if inst else None,
                    "config": inst.config if inst else {},
                }
            )
        return Response(
            {"plugin_api_version": PLUGIN_API_VERSION, "results": results}
        )


class PluginInstallView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "plugins.manage"

    def post(self, request):
        serializer = PluginInstallCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        inst, created = PluginInstallation.objects.update_or_create(
            tenant=request.tenant,
            plugin_id=data["plugin_id"],
            defaults={
                "enabled": data.get("enabled", True),
                "config": data.get("config") or {},
            },
        )
        return Response(
            PluginInstallationSerializer(inst).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class PluginInstallationDetailView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "plugins.manage"

    def _get(self, request, plugin_id):
        return PluginInstallation.objects.filter(
            tenant=request.tenant, plugin_id=plugin_id
        ).first()

    def patch(self, request, plugin_id):
        inst = self._get(request, plugin_id)
        if not inst:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Not installed", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = PluginInstallationSerializer(inst, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, plugin_id):
        inst = self._get(request, plugin_id)
        if not inst:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Not installed", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        inst.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
