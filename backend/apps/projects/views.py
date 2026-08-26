from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.devices.models import Device
from apps.projects.models import Project, ProjectDevice

from .serializers import ProjectCreateSerializer, ProjectDeviceSerializer, ProjectSerializer


def _serialize_project_device_link(link: ProjectDevice) -> dict:
    return {
        "device_id": str(link.device_id),
        "name": link.device.name,
        "status": link.device.status,
        "priority": link.priority,
        "exclusive": link.exclusive,
        "preferred_sim_slot": link.preferred_sim_slot,
        "sim_fallback_enabled": link.sim_fallback_enabled,
    }


class ProjectListCreateView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "projects.write" if self.request.method == "POST" else "projects.read"
        )
        return super().get_permissions()

    def get(self, request):
        projects = (
            Project.objects.filter(tenant=request.tenant)
            .prefetch_related("project_devices__device")
            .order_by("name")
        )
        return Response({"results": ProjectSerializer(projects, many=True).data})

    def post(self, request):
        serializer = ProjectCreateSerializer(
            data=request.data, context={"tenant": request.tenant}
        )
        serializer.is_valid(raise_exception=True)
        project = serializer.save()
        return Response(ProjectSerializer(project).data, status=status.HTTP_201_CREATED)


class ProjectDetailView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "projects.write"
            if self.request.method in {"PATCH", "DELETE"}
            else "projects.read"
        )
        return super().get_permissions()

    def _get(self, request, project_id):
        return (
            Project.objects.filter(tenant=request.tenant, id=project_id)
            .prefetch_related("project_devices__device")
            .first()
        )

    def get(self, request, project_id):
        project = self._get(request, project_id)
        if not project:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Project not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ProjectSerializer(project).data)

    def patch(self, request, project_id):
        project = self._get(request, project_id)
        if not project:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Project not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProjectSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, project_id):
        project = self._get(request, project_id)
        if not project:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Project not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        project.is_active = False
        project.save(update_fields=["is_active", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProjectDevicesView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "projects.write" if self.request.method == "PUT" else "projects.read"
        )
        return super().get_permissions()

    def get(self, request, project_id):
        project = Project.objects.filter(tenant=request.tenant, id=project_id).first()
        if not project:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Project not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        links = ProjectDevice.objects.filter(project=project).select_related("device")
        return Response({"results": [_serialize_project_device_link(link) for link in links]})

    def put(self, request, project_id):
        project = Project.objects.filter(tenant=request.tenant, id=project_id).first()
        if not project:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Project not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ProjectDeviceSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device_ids = serializer.validated_data["device_ids"]
        priorities = serializer.validated_data.get("priorities") or {}
        device_settings = serializer.validated_data.get("device_settings") or {}
        devices = list(Device.objects.filter(tenant=request.tenant, id__in=device_ids))
        if len(devices) != len(set(device_ids)):
            return Response(
                {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "One or more devices not found in tenant",
                        "details": None,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        devices_by_id = {str(device.id): device for device in devices}
        for device_id in device_ids:
            device_key = str(device_id)
            device = devices_by_id[device_key]
            settings = device_settings.get(device_key) or {}
            preferred_sim_slot = settings.get("preferred_sim_slot")
            if preferred_sim_slot is not None:
                if preferred_sim_slot not in (1, 2):
                    return Response(
                        {
                            "error": {
                                "code": "BAD_REQUEST",
                                "message": "preferred_sim_slot must be 1 or 2",
                                "details": {"device_id": device_key},
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                if not device.sims.filter(
                    slot_index=preferred_sim_slot, is_active=True
                ).exists():
                    return Response(
                        {
                            "error": {
                                "code": "BAD_REQUEST",
                                "message": "Preferred SIM slot is not active on this device",
                                "details": {
                                    "device_id": device_key,
                                    "preferred_sim_slot": preferred_sim_slot,
                                },
                            }
                        },
                        status=status.HTTP_400_BAD_REQUEST,
                    )

        ProjectDevice.objects.filter(project=project).delete()
        for device in devices:
            device_key = str(device.id)
            settings = device_settings.get(device_key) or {}
            ProjectDevice.objects.create(
                project=project,
                device=device,
                priority=int(
                    settings.get("priority", priorities.get(device_key, 100))
                ),
                preferred_sim_slot=settings.get("preferred_sim_slot"),
                sim_fallback_enabled=settings.get("sim_fallback_enabled", True),
            )
        return self.get(request, project_id)
