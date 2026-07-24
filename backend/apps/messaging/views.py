from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.devices.authentication import DeviceTokenAuthentication
from apps.messaging.models import Message, MessageTemplate
from apps.messaging.services.messages import MessageService
from apps.messaging.services.templates import (
    IdempotencyConflict,
    get_idempotent_response,
    request_fingerprint,
    resolve_send_body,
    store_idempotent_response,
)
from apps.routing.exceptions import RateLimitExceeded, RoutingError

from .serializers import (
    InboundCreateSerializer,
    InboundMessageSerializer,
    MessageAttemptSerializer,
    MessageSerializer,
    MessageStatusUpdateSerializer,
    SendMessageSerializer,
)


class MessageSendView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "messages.send"

    def post(self, request):
        serializer = SendMessageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        idem_key = (
            request.headers.get("Idempotency-Key")
            or request.headers.get("X-Idempotency-Key")
            or ""
        ).strip()
        fingerprint = request_fingerprint(
            {
                "to": data.get("to"),
                "text": data.get("text"),
                "template_id": str(data["template_id"]) if data.get("template_id") else None,
                "vars": data.get("vars") or {},
                "project": data.get("project"),
                "device": data.get("device"),
                "mode": data.get("mode"),
                "sim_slot": data.get("sim_slot"),
                "client_ref": data.get("client_ref"),
            }
        )
        if idem_key:
            try:
                cached = get_idempotent_response(
                    tenant=request.tenant, key=idem_key, request_hash=fingerprint
                )
            except IdempotencyConflict:
                return Response(
                    {
                        "error": {
                            "code": "IDEMPOTENCY_CONFLICT",
                            "message": "Idempotency key reused with different payload",
                            "details": None,
                        }
                    },
                    status=status.HTTP_409_CONFLICT,
                )
            if cached is not None:
                return Response(cached.response_body, status=cached.response_status)

        try:
            project_ref = data.get("project") or None
            if not project_ref and getattr(request, "project", None):
                project = request.project
            else:
                project = MessageService.resolve_project(
                    tenant=request.tenant, project_ref=project_ref
                )

            template = None
            if data.get("template_id"):
                template = MessageTemplate.objects.filter(
                    tenant=request.tenant, id=data["template_id"], is_active=True
                ).first()
                if template is None:
                    raise ValueError("Template not found")

            body = resolve_send_body(
                text=data.get("text") or None,
                template=template,
                variables=data.get("vars") or {},
            )

            device = None
            if data.get("device"):
                device = MessageService.resolve_device(
                    tenant=request.tenant,
                    device_ref=data.get("device"),
                    project=project,
                )
            message = MessageService.enqueue(
                tenant=request.tenant,
                to_number=data["to"],
                body=body,
                project=project,
                device=device,
                sim_slot_index=data.get("sim_slot"),
                mode=data.get("mode") or Message.Mode.GENERAL,
                client_ref=data.get("client_ref") or idem_key or "",
                meta=data.get("meta") or {},
                scheduled_at=data.get("scheduled_at"),
            )
            api_key = getattr(request, "api_key", None)
            if api_key:
                from apps.projects.authentication import bump_api_key_messages

                bump_api_key_messages(api_key, 1)
                meta = dict(message.meta or {})
                meta["api_key_id"] = str(api_key.id)
                message.meta = meta
                message.save(update_fields=["meta", "updated_at"])
        except IdempotencyConflict as exc:
            return Response(
                {
                    "error": {
                        "code": "IDEMPOTENCY_CONFLICT",
                        "message": exc.message,
                        "details": None,
                    }
                },
                status=status.HTTP_409_CONFLICT,
            )
        except RateLimitExceeded as exc:
            return Response(
                {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": None,
                    }
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )
        except RoutingError as exc:
            return Response(
                {
                    "error": {
                        "code": exc.code,
                        "message": exc.message,
                        "details": None,
                    }
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except ValueError as exc:
            return Response(
                {
                    "error": {
                        "code": "UNPROCESSABLE",
                        "message": str(exc),
                        "details": None,
                    }
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        response_body = MessageSerializer(message).data
        if idem_key:
            store_idempotent_response(
                tenant=request.tenant,
                key=idem_key,
                request_hash=fingerprint,
                status_code=status.HTTP_202_ACCEPTED,
                body=response_body,
            )
        return Response(response_body, status=status.HTTP_202_ACCEPTED)


class MessageListView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "messages.read"

    def get(self, request):
        qs = Message.objects.filter(tenant=request.tenant).select_related(
            "device", "project", "sim_slot"
        )
        if getattr(request, "api_key", None) and getattr(request, "project", None):
            qs = qs.filter(project=request.project)
        if status_filter := request.query_params.get("status"):
            qs = qs.filter(status=status_filter)
        if device := request.query_params.get("device"):
            qs = qs.filter(Q(device_id=device) | Q(device__name=device))
        if project := request.query_params.get("project"):
            qs = qs.filter(Q(project_id=project) | Q(project__slug=project))
        if to_number := request.query_params.get("to"):
            qs = qs.filter(to_number__icontains=to_number)
        if q := request.query_params.get("q"):
            qs = qs.filter(Q(body__icontains=q) | Q(to_number__icontains=q))
        qs = qs.distinct()[:200]
        return Response({"results": MessageSerializer(qs, many=True).data})


class MessageDetailView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "messages.read"

    def get(self, request, message_id):
        qs = Message.objects.filter(tenant=request.tenant, id=message_id)
        if getattr(request, "api_key", None) and getattr(request, "project", None):
            qs = qs.filter(project=request.project)
        message = qs.select_related("device", "project", "sim_slot").first()
        if not message:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Message not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(MessageSerializer(message).data)


class MessageCancelView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "messages.cancel"

    def post(self, request, message_id):
        message = Message.objects.filter(tenant=request.tenant, id=message_id).first()
        if not message:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Message not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            message = MessageService.cancel(message)
        except ValueError as exc:
            return Response(
                {"error": {"code": "UNPROCESSABLE", "message": str(exc), "details": None}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(MessageSerializer(message).data)


class MessageRetryView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "messages.retry"

    def post(self, request, message_id):
        message = Message.objects.filter(tenant=request.tenant, id=message_id).first()
        if not message:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Message not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        try:
            message = MessageService.retry(message)
        except ValueError as exc:
            return Response(
                {"error": {"code": "UNPROCESSABLE", "message": str(exc), "details": None}},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        return Response(MessageSerializer(message).data)


class MessageAttemptsView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "messages.read"

    def get(self, request, message_id):
        message = Message.objects.filter(tenant=request.tenant, id=message_id).first()
        if not message:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Message not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            {"results": MessageAttemptSerializer(message.attempts.all(), many=True).data}
        )


class AgentMessageStatusView(APIView):
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request, message_id):
        if not getattr(request, "device", None):
            return Response(
                {"error": {"code": "UNAUTHORIZED", "message": "Device auth required", "details": None}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        message = Message.objects.filter(id=message_id, device=request.device).first()
        if not message:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Message not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = MessageStatusUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        message = MessageService.update_status(
            message=message,
            status=data["status"],
            error_code=data.get("error_code") or "",
            error_message=data.get("error_message") or "",
            latency_ms=data.get("latency_ms"),
            sim_slot_index=data.get("sim_slot"),
        )
        return Response(MessageSerializer(message).data)


class AgentInboundView(APIView):
    authentication_classes = [DeviceTokenAuthentication]
    permission_classes = [AllowAny]

    def post(self, request):
        if not getattr(request, "device", None):
            return Response(
                {"error": {"code": "UNAUTHORIZED", "message": "Device auth required", "details": None}},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = InboundCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        inbound = MessageService.create_inbound(
            device=request.device,
            from_number=data["from_number"],
            body=data["body"],
            received_at=data["received_at"],
            sim_slot_index=data.get("sim_slot"),
            meta=data.get("meta") or {},
        )
        return Response(
            InboundMessageSerializer(inbound).data, status=status.HTTP_201_CREATED
        )


class InboundListView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "inbound.read"

    def get(self, request):
        from apps.messaging.models import InboundMessage

        qs = InboundMessage.objects.filter(tenant=request.tenant).select_related("device")[
            :200
        ]
        return Response({"results": InboundMessageSerializer(qs, many=True).data})
