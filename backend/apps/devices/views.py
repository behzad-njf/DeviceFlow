from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.devices.authentication import DeviceTokenAuthentication
from apps.devices.models import AgentRelease, Device, DeviceCommand, DeviceEvent
from apps.devices.services.commands import CommandService
from apps.devices.services.ota import enqueue_ota, latest_release, sha256_file
from apps.devices.services.pairing import DeviceService
from apps.messaging.services.messages import MessageService
from apps.realtime.events import queue_summary_for_device

from .serializers import (
    AgentPairSerializer,
    DeviceActionSerializer,
    DeviceCommandCreateSerializer,
    DeviceCommandSerializer,
    DeviceEventSerializer,
    DeviceSerializer,
    DeviceUpdateSerializer,
    HeartbeatSerializer,
    PairingCodeCreateSerializer,
)


class DeviceListView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "devices.read"

    def get(self, request):
        qs = Device.objects.filter(tenant=request.tenant).prefetch_related("sims")
        status_filter = request.query_params.get("status")
        q = request.query_params.get("q")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if q:
            qs = qs.filter(name__icontains=q)
        return Response({"results": DeviceSerializer(qs, many=True).data})


class DeviceDetailView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "devices.write"
            if self.request.method in {"PATCH", "DELETE"}
            else "devices.read"
        )
        return super().get_permissions()

    def _get(self, request, device_id):
        return (
            Device.objects.filter(tenant=request.tenant, id=device_id)
            .prefetch_related("sims")
            .first()
        )

    def get(self, request, device_id):
        device = self._get(request, device_id)
        if not device:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Device not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(DeviceSerializer(device).data)

    def patch(self, request, device_id):
        device = self._get(request, device_id)
        if not device:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Device not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = DeviceUpdateSerializer(device, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(DeviceSerializer(device).data)

    def delete(self, request, device_id):
        device = self._get(request, device_id)
        if not device:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Device not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        device.status = Device.Status.DISABLED
        device.device_token_hash = ""
        device.save(update_fields=["status", "device_token_hash", "updated_at"])
        return Response(status=status.HTTP_204_NO_CONTENT)


class PairingCodeCreateView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "devices.write"

    def post(self, request):
        serializer = PairingCodeCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        device, code = DeviceService.create_pairing(
            tenant=request.tenant,
            name=serializer.validated_data.get("name") or "",
        )
        return Response(
            {
                "device_id": str(device.id),
                "name": device.name,
                "code": code,
                "expires_at": device.pairing_code_expires_at,
            },
            status=status.HTTP_201_CREATED,
        )


class DeviceEventsView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "devices.read"

    def get(self, request, device_id):
        device = Device.objects.filter(tenant=request.tenant, id=device_id).first()
        if not device:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Device not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = int(request.query_params.get("page_size", 20))
        except (TypeError, ValueError):
            page_size = 20
        page_size = max(1, min(page_size, 100))

        qs = DeviceEvent.objects.filter(device=device)
        total = qs.count()
        start = (page - 1) * page_size
        events = qs[start : start + page_size]
        total_pages = max(1, (total + page_size - 1) // page_size)
        return Response(
            {
                "results": DeviceEventSerializer(events, many=True).data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                    "total_pages": total_pages,
                    "has_next": page < total_pages,
                    "has_prev": page > 1,
                },
            }
        )


class DeviceCommandDetailView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "devices.read"

    def get(self, request, device_id, command_id):
        device = Device.objects.filter(tenant=request.tenant, id=device_id).first()
        if not device:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Device not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        command = DeviceCommand.objects.filter(device=device, id=command_id).first()
        if not command:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Command not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(DeviceCommandSerializer(command).data)


class DeviceQueueView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "queues.read"

    def get(self, request, device_id):
        device = Device.objects.filter(tenant=request.tenant, id=device_id).first()
        if not device:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Device not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        summary = queue_summary_for_device(device)
        summary["name"] = device.name
        summary["status"] = device.status
        return Response(summary)


class DeviceCommandCreateView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "devices.command"

    def post(self, request, device_id):
        device = Device.objects.filter(tenant=request.tenant, id=device_id).first()
        if not device:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Device not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = DeviceCommandCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            command = CommandService.enqueue(
                device=device,
                action=serializer.validated_data["command"],
                params=serializer.validated_data.get("params") or {},
                user=request.user,
            )
        except ValueError as exc:
            return Response(
                {"error": {"code": "BAD_REQUEST", "message": str(exc), "details": None}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(DeviceCommandSerializer(command).data, status=status.HTTP_201_CREATED)


class DeviceActionView(APIView):
    """Generic capability-based actions (Platform API)."""

    permission_classes = [RequirePermission]
    required_permission = "devices.command"

    def post(self, request, device_id):
        from apps.devices.services.actions import ActionError, enqueue_action

        device = Device.objects.filter(tenant=request.tenant, id=device_id).first()
        if not device:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Device not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = DeviceActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            command = enqueue_action(
                device=device,
                capability=serializer.validated_data["capability"],
                params=serializer.validated_data.get("params") or {},
                user=request.user,
            )
        except ActionError as exc:
            return Response(
                {"error": {"code": exc.code, "message": exc.message, "details": None}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(DeviceCommandSerializer(command).data, status=status.HTTP_201_CREATED)


class AgentPairView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        serializer = AgentPairSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            device, token = DeviceService.pair_device(
                code=serializer.validated_data["pairing_code"],
                device_info=serializer.validated_data.get("device_info") or {},
            )
        except ValueError as exc:
            return Response(
                {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": str(exc),
                        "details": None,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                "device_id": str(device.id),
                "device_token": token,
                "name": device.name,
                "config": {
                    "heartbeat_interval_sec": 15,
                    "poll_interval_sec": 3,
                },
            },
            status=status.HTTP_201_CREATED,
        )


class AgentHeartbeatView(APIView):
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        if not getattr(request, "device", None):
            return Response(
                {"error": {"code": "UNAUTHORIZED", "message": "Device auth required", "details": None}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = HeartbeatSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        DeviceService.ingest_heartbeat(device=request.device, payload=serializer.validated_data)
        MessageService.promote_retries()
        return Response({"status": "ok", "device_status": request.device.status})


class AgentPendingCommandsView(APIView):
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        if not getattr(request, "device", None):
            return Response(
                {"error": {"code": "UNAUTHORIZED", "message": "Device auth required", "details": None}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        MessageService.promote_retries()
        messages = MessageService.pending_for_device(request.device)
        commands = []
        for message in messages:
            commands.append(
                {
                    "type": "command.send_sms",
                    "command_id": str(message.id),
                    "payload": {
                        "message_id": str(message.id),
                        "to": message.to_number,
                        "text": message.body,
                        "sim_slot": message.sim_slot.slot_index if message.sim_slot else None,
                        "timeout_sec": 60,
                    },
                }
            )
        for command in CommandService.pending_for_device(request.device):
            command.status = DeviceCommand.Status.SENT
            command.save(update_fields=["status", "updated_at"])
            commands.append(
                {
                    "type": "command.control",
                    "command_id": str(command.id),
                    "payload": {
                        "action": command.action,
                        "params": command.params,
                    },
                }
            )
        return Response({"results": commands})


class AgentCommandAckView(APIView):
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, command_id):
        if not getattr(request, "device", None):
            return Response(
                {"error": {"code": "UNAUTHORIZED", "message": "Device auth required", "details": None}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        command = DeviceCommand.objects.filter(
            id=command_id, device=request.device
        ).first()
        if not command:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Command not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        status_value = request.data.get("status") or "acked"
        try:
            command = CommandService.ack(
                command=command,
                status=status_value,
                result=request.data.get("result") or {},
            )
        except ValueError as exc:
            return Response(
                {"error": {"code": "BAD_REQUEST", "message": str(exc), "details": None}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        # OTA success: bump reported agent version from command params / result
        if (
            command.action == DeviceCommand.Action.INSTALL_UPDATE
            and command.status == DeviceCommand.Status.ACKED
        ):
            new_version = (
                (command.result or {}).get("version")
                or (command.params or {}).get("version")
            )
            if new_version:
                request.device.agent_version = str(new_version)
                request.device.save(update_fields=["agent_version", "updated_at"])
        return Response(DeviceCommandSerializer(command).data)


class AgentReleaseListCreateView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "devices.write" if self.request.method == "POST" else "devices.read"
        )
        return super().get_permissions()

    def get(self, request):
        from django.db.models import Q

        qs = AgentRelease.objects.filter(
            Q(tenant=request.tenant) | Q(tenant__isnull=True)
        ).order_by("-created_at")[:50]
        results = [
            {
                "id": str(r.id),
                "version": r.version,
                "changelog": r.changelog,
                "checksum_sha256": r.checksum_sha256,
                "download_url": r.resolved_download_url(request),
                "is_active": r.is_active,
                "created_at": r.created_at,
            }
            for r in qs
        ]
        return Response({"results": results})

    def post(self, request):
        version = (request.data.get("version") or "").strip()
        if not version:
            return Response(
                {"error": {"code": "BAD_REQUEST", "message": "version required", "details": None}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        release = AgentRelease(
            tenant=request.tenant,
            version=version,
            changelog=request.data.get("changelog") or "",
            download_url=request.data.get("download_url") or "",
            is_active=bool(request.data.get("is_active", True)),
        )
        apk = request.FILES.get("apk")
        if apk:
            release.apk = apk
        release.save()
        if release.apk and not release.checksum_sha256:
            try:
                release.checksum_sha256 = sha256_file(release.apk.path)
                release.save(update_fields=["checksum_sha256"])
            except Exception:
                pass
        if request.data.get("checksum_sha256"):
            release.checksum_sha256 = request.data["checksum_sha256"]
            release.save(update_fields=["checksum_sha256"])
        return Response(
            {
                "id": str(release.id),
                "version": release.version,
                "download_url": release.resolved_download_url(request),
                "checksum_sha256": release.checksum_sha256,
            },
            status=status.HTTP_201_CREATED,
        )


class DeviceOtaPushView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "devices.command"

    def post(self, request, device_id):
        device = Device.objects.filter(tenant=request.tenant, id=device_id).first()
        if not device:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Device not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        release_id = request.data.get("release_id")
        if release_id:
            release = AgentRelease.objects.filter(id=release_id).first()
        else:
            release = latest_release(tenant=request.tenant)
        if release is None:
            return Response(
                {"error": {"code": "NO_RELEASE", "message": "No active agent release", "details": None}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        command = enqueue_ota(
            device=device, release=release, user=request.user, request=request
        )
        return Response(DeviceCommandSerializer(command).data, status=status.HTTP_201_CREATED)


class AgentOtaCheckView(APIView):
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [AllowAny]

    def get(self, request):
        if not getattr(request, "device", None):
            return Response(
                {"error": {"code": "UNAUTHORIZED", "message": "Device auth required", "details": None}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        release = latest_release(tenant=request.device.tenant)
        if release is None:
            return Response({"update_available": False})
        current = request.device.agent_version or ""
        available = release.version != current
        return Response(
            {
                "update_available": available,
                "current_version": current,
                "latest_version": release.version,
                "download_url": release.resolved_download_url(request),
                "checksum_sha256": release.checksum_sha256,
                "changelog": release.changelog,
            }
        )

