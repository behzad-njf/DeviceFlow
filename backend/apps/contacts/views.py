from django.db.models import Q
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.contacts.models import AutoReplyRule, Contact, ContactGroup, Conversation
from apps.contacts.serializers import (
    AutoReplyRuleSerializer,
    ContactGroupSerializer,
    ContactImportConfirmSerializer,
    ContactImportPreviewSerializer,
    ContactSerializer,
    ConversationSerializer,
)
from apps.contacts.services import import_contacts, preview_contact_import
from apps.devices.models import Device
from apps.messaging.models import InboundMessage, Message
from apps.messaging.serializers import InboundMessageSerializer, MessageSerializer
from apps.routing.services.operators import normalize_number


class ContactListCreateView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "contacts.write" if self.request.method == "POST" else "contacts.read"
        )
        return super().get_permissions()

    def get(self, request):
        qs = Contact.objects.filter(tenant=request.tenant).select_related("source_device")
        if q := request.query_params.get("q"):
            qs = qs.filter(Q(name__icontains=q) | Q(phone_number__icontains=q))
        if request.query_params.get("blacklisted") == "1":
            qs = qs.filter(is_blacklisted=True)
        if tag := request.query_params.get("tag"):
            qs = qs.filter(tags__contains=[tag])
        if device_id := request.query_params.get("device"):
            qs = qs.filter(source_device_id=device_id)
        return Response({"results": ContactSerializer(qs[:500], many=True).data})

    def post(self, request):
        serializer = ContactSerializer(
            data=request.data, context={"tenant": request.tenant}
        )
        serializer.is_valid(raise_exception=True)
        contact = serializer.save()
        return Response(ContactSerializer(contact).data, status=status.HTTP_201_CREATED)


class ContactDetailView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "contacts.write"
            if self.request.method in {"PATCH", "DELETE"}
            else "contacts.read"
        )
        return super().get_permissions()

    def _get(self, request, contact_id):
        return Contact.objects.filter(tenant=request.tenant, id=contact_id).first()

    def get(self, request, contact_id):
        contact = self._get(request, contact_id)
        if not contact:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Contact not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(ContactSerializer(contact).data)

    def patch(self, request, contact_id):
        contact = self._get(request, contact_id)
        if not contact:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Contact not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ContactSerializer(contact, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, contact_id):
        contact = self._get(request, contact_id)
        if not contact:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Contact not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        contact.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ContactImportPreviewView(APIView):
    """Validate phonebook rows and return valid/invalid preview (no writes)."""

    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = "contacts.write"
        return super().get_permissions()

    def post(self, request):
        serializer = ContactImportPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            preview_contact_import(
                tenant=request.tenant,
                rows=serializer.validated_data["contacts"],
            )
        )


class ContactImportConfirmView(APIView):
    """Import only valid phone numbers from a previewed phonebook batch."""

    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = "contacts.write"
        return super().get_permissions()

    def post(self, request):
        serializer = ContactImportConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        device = None
        device_id = data.get("device_id")
        if device_id:
            device = Device.objects.filter(tenant=request.tenant, id=device_id).first()
            if not device:
                return Response(
                    {
                        "error": {
                            "code": "NOT_FOUND",
                            "message": "Device not found",
                            "details": None,
                        }
                    },
                    status=status.HTTP_404_NOT_FOUND,
                )
        result = import_contacts(
            tenant=request.tenant,
            rows=data["contacts"],
            device=device,
            update_existing=data.get("update_existing", True),
        )
        return Response(result, status=status.HTTP_200_OK)


class ContactGroupListCreateView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "contacts.write" if self.request.method == "POST" else "contacts.read"
        )
        return super().get_permissions()

    def get(self, request):
        qs = ContactGroup.objects.filter(tenant=request.tenant)
        return Response({"results": ContactGroupSerializer(qs, many=True).data})

    def post(self, request):
        serializer = ContactGroupSerializer(
            data=request.data, context={"tenant": request.tenant}
        )
        serializer.is_valid(raise_exception=True)
        group = serializer.save()
        return Response(
            ContactGroupSerializer(group).data, status=status.HTTP_201_CREATED
        )


class ContactGroupDetailView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "contacts.write"
            if self.request.method in {"PATCH", "DELETE"}
            else "contacts.read"
        )
        return super().get_permissions()

    def _get(self, request, group_id):
        return ContactGroup.objects.filter(tenant=request.tenant, id=group_id).first()

    def get(self, request, group_id):
        group = self._get(request, group_id)
        if not group:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Group not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = ContactGroupSerializer(group).data
        data["members"] = ContactSerializer(group.members.all(), many=True).data
        return Response(data)

    def patch(self, request, group_id):
        group = self._get(request, group_id)
        if not group:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Group not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = ContactGroupSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(ContactGroupSerializer(group).data)

    def delete(self, request, group_id):
        group = self._get(request, group_id)
        if not group:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Group not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        group.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ConversationListView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "inbound.read"

    def get(self, request):
        qs = Conversation.objects.filter(tenant=request.tenant).select_related("contact")
        if project := request.query_params.get("project"):
            qs = qs.filter(Q(project_id=project) | Q(project__slug=project))
        if q := request.query_params.get("q"):
            qs = qs.filter(
                Q(phone_number__icontains=q)
                | Q(last_preview__icontains=q)
                | Q(contact__name__icontains=q)
            )
        return Response({"results": ConversationSerializer(qs[:100], many=True).data})


class ConversationDetailView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "inbound.read"

    def get(self, request, conversation_id):
        conversation = (
            Conversation.objects.filter(tenant=request.tenant, id=conversation_id)
            .select_related("contact")
            .first()
        )
        if not conversation:
            return Response(
                {
                    "error": {
                        "code": "NOT_FOUND",
                        "message": "Conversation not found",
                        "details": None,
                    }
                },
                status=status.HTTP_404_NOT_FOUND,
            )
        phone = conversation.phone_number
        outbound = list(
            Message.objects.filter(tenant=request.tenant, to_number=phone).order_by(
                "created_at"
            )[:200]
        )
        # Also match normalized variants loosely
        inbound = list(
            InboundMessage.objects.filter(
                tenant=request.tenant, from_number=phone
            ).order_by("received_at")[:200]
        )
        events = []
        for msg in outbound:
            events.append(
                {
                    "direction": "outbound",
                    "at": msg.created_at.isoformat(),
                    "message": MessageSerializer(msg).data,
                }
            )
        for msg in inbound:
            events.append(
                {
                    "direction": "inbound",
                    "at": msg.received_at.isoformat(),
                    "message": InboundMessageSerializer(msg).data,
                }
            )
        events.sort(key=lambda e: e["at"])
        if conversation.unread_count:
            conversation.unread_count = 0
            conversation.save(update_fields=["unread_count", "updated_at"])
        return Response(
            {
                "conversation": ConversationSerializer(conversation).data,
                "messages": events,
            }
        )


class AutoReplyListCreateView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "contacts.write" if self.request.method == "POST" else "contacts.read"
        )
        return super().get_permissions()

    def get(self, request):
        qs = AutoReplyRule.objects.filter(tenant=request.tenant)
        return Response({"results": AutoReplyRuleSerializer(qs, many=True).data})

    def post(self, request):
        serializer = AutoReplyRuleSerializer(
            data=request.data, context={"tenant": request.tenant}
        )
        serializer.is_valid(raise_exception=True)
        rule = serializer.save()
        return Response(
            AutoReplyRuleSerializer(rule).data, status=status.HTTP_201_CREATED
        )


class AutoReplyDetailView(APIView):
    permission_classes = [RequirePermission]

    def get_permissions(self):
        self.required_permission = (
            "contacts.write"
            if self.request.method in {"PATCH", "DELETE"}
            else "contacts.read"
        )
        return super().get_permissions()

    def _get(self, request, rule_id):
        return AutoReplyRule.objects.filter(tenant=request.tenant, id=rule_id).first()

    def patch(self, request, rule_id):
        rule = self._get(request, rule_id)
        if not rule:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Rule not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = AutoReplyRuleSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, rule_id):
        rule = self._get(request, rule_id)
        if not rule:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Rule not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
