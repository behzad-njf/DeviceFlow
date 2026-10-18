from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.devices.models import Device
from apps.projects.models import Project, ProjectDevice, ProjectRouteBinding

from .serializers import ProjectRouteBindingSerializer, ProjectRouteBindingWriteSerializer


def _get_project(request, project_id):
    return Project.objects.filter(tenant=request.tenant, id=project_id).first()


class ProjectRouteListCreateView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "projects.write" if self.request.method == "POST" else "projects.read"
        )
        return super().get_permissions()

    def get(self, request, project_id):
        project = _get_project(request, project_id)
        if not project:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Project not found",
                        "details": None,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        rows = (
            ProjectRouteBinding.objects.filter(project=project)
            .select_related("device")
            .order_by("route_key")
        )
        return Response(
            {"results": ProjectRouteBindingSerializer(rows, many=True).data}
        )

    def post(self, request, project_id):
        project = _get_project(request, project_id)
        if not project:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Project not found",
                        "details": None,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProjectRouteBindingWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        error = _validate_route_device(request.tenant, project, data)
        if error is not None:
            return error
        if ProjectRouteBinding.objects.filter(
            project=project, route_key=data["route_key"]
        ).exists():
            return Response(
                {
                    "error": {
                        "code": "CONFLICT",
                        "message": "route_key already exists on this project",
                        "details": {"route_key": data["route_key"]},
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        binding = ProjectRouteBinding.objects.create(
            project=project,
            route_key=data["route_key"],
            device_id=data["device_id"],
            preferred_sim_slot=data.get("preferred_sim_slot"),
            sim_fallback_enabled=data.get("sim_fallback_enabled", True),
            label=(data.get("label") or "").strip(),
            is_active=data.get("is_active", True),
        )
        return Response(
            ProjectRouteBindingSerializer(binding).data,
            status=status.HTTP_201_CREATED,
        )


class ProjectRouteDetailView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "projects.write"
            if self.request.method in {"PATCH", "DELETE"}
            else "projects.read"
        )
        return super().get_permissions()

    def _get(self, request, project_id, route_id):
        project = _get_project(request, project_id)
        if not project:
            return None, None
        binding = (
            ProjectRouteBinding.objects.filter(project=project, id=route_id)
            .select_related("device")
            .first()
        )
        return project, binding

    def get(self, request, project_id, route_id):
        _project, binding = self._get(request, project_id, route_id)
        if binding is None:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Route not found",
                        "details": None,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ProjectRouteBindingSerializer(binding).data)

    def patch(self, request, project_id, route_id):
        project, binding = self._get(request, project_id, route_id)
        if binding is None:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Route not found",
                        "details": None,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProjectRouteBindingWriteSerializer(
            data=request.data, partial=True
        )
        # Allow partial: merge with existing for required fields.
        payload = {
            "route_key": binding.route_key,
            "device_id": binding.device_id,
            "preferred_sim_slot": binding.preferred_sim_slot,
            "sim_fallback_enabled": binding.sim_fallback_enabled,
            "label": binding.label,
            "is_active": binding.is_active,
        }
        payload.update(request.data)
        serializer = ProjectRouteBindingWriteSerializer(data=payload)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        error = _validate_route_device(request.tenant, project, data)
        if error is not None:
            return error
        conflict = (
            ProjectRouteBinding.objects.filter(
                project=project, route_key=data["route_key"]
            )
            .exclude(id=binding.id)
            .exists()
        )
        if conflict:
            return Response(
                {
                    "error": {
                        "code": "CONFLICT",
                        "message": "route_key already exists on this project",
                        "details": {"route_key": data["route_key"]},
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        binding.route_key = data["route_key"]
        binding.device_id = data["device_id"]
        binding.preferred_sim_slot = data.get("preferred_sim_slot")
        binding.sim_fallback_enabled = data.get("sim_fallback_enabled", True)
        binding.label = (data.get("label") or "").strip()
        binding.is_active = data.get("is_active", True)
        binding.save()
        return Response(ProjectRouteBindingSerializer(binding).data)

    def delete(self, request, project_id, route_id):
        _project, binding = self._get(request, project_id, route_id)
        if binding is None:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Route not found",
                        "details": None,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        binding.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


def _validate_route_device(tenant, project, data: dict):
    device = Device.objects.filter(tenant=tenant, id=data["device_id"]).first()
    if device is None:
        return Response(
            {
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "Device not found in tenant",
                    "details": None,
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    if not ProjectDevice.objects.filter(
        project=project, device_id=device.id
    ).exists():
        return Response(
            {
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "Device must be attached to the project first",
                    "details": {"device_id": str(device.id)},
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    preferred = data.get("preferred_sim_slot")
    if preferred is not None and not device.sims.filter(
        slot_index=preferred, is_active=True
    ).exists():
        return Response(
            {
                "error": {
                    "code": "BAD_REQUEST",
                    "message": "Preferred SIM slot is not active on this device",
                    "details": {
                        "device_id": str(device.id),
                        "preferred_sim_slot": preferred,
                    },
                }
            },
            status=status.HTTP_400_BAD_REQUEST,
        )
    return None
