from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.devices.models import Device
from apps.projects.models import Project, ProjectDevice

from .serializers import ProjectCreateSerializer, ProjectDeviceSerializer, ProjectSerializer


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
        return Response(
            {
                "results": [
                    {
                        "device_id": str(link.device_id),
                        "name": link.device.name,
                        "status": link.device.status,
                        "priority": link.priority,
                        "exclusive": link.exclusive,
                    }
                    for link in links
                ]
            }
        )

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
        devices = Device.objects.filter(tenant=request.tenant, id__in=device_ids)
        if devices.count() != len(set(device_ids)):
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
        ProjectDevice.objects.filter(project=project).delete()
        for device in devices:
            ProjectDevice.objects.create(
                project=project,
                device=device,
                priority=int(priorities.get(str(device.id), 100)),
            )
        return self.get(request, project_id)
