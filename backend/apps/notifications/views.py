from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.notifications.models import NotificationChannel, NotificationLog, NotificationRule
from apps.notifications.serializers import (
    NotificationChannelSerializer,
    NotificationLogSerializer,
    NotificationRuleSerializer,
)


class NotificationChannelListCreateView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "notifications.write"

    def get(self, request):
        qs = NotificationChannel.objects.filter(tenant=request.tenant)
        return Response({"results": NotificationChannelSerializer(qs, many=True).data})

    def post(self, request):
        serializer = NotificationChannelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        channel = NotificationChannel.objects.create(
            tenant=request.tenant, **serializer.validated_data
        )
        return Response(
            NotificationChannelSerializer(channel).data, status=status.HTTP_201_CREATED
        )


class NotificationChannelDetailView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "notifications.write"

    def _get(self, request, channel_id):
        return NotificationChannel.objects.filter(
            tenant=request.tenant, id=channel_id
        ).first()

    def patch(self, request, channel_id):
        channel = self._get(request, channel_id)
        if not channel:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = NotificationChannelSerializer(channel, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, channel_id):
        channel = self._get(request, channel_id)
        if not channel:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        channel.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationRuleListCreateView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "notifications.write"

    def get(self, request):
        qs = NotificationRule.objects.filter(tenant=request.tenant)
        return Response({"results": NotificationRuleSerializer(qs, many=True).data})

    def post(self, request):
        serializer = NotificationRuleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rule = NotificationRule.objects.create(
            tenant=request.tenant, **serializer.validated_data
        )
        return Response(
            NotificationRuleSerializer(rule).data, status=status.HTTP_201_CREATED
        )


class NotificationRuleDetailView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "notifications.write"

    def _get(self, request, rule_id):
        return NotificationRule.objects.filter(tenant=request.tenant, id=rule_id).first()

    def patch(self, request, rule_id):
        rule = self._get(request, rule_id)
        if not rule:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = NotificationRuleSerializer(rule, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, rule_id):
        rule = self._get(request, rule_id)
        if not rule:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        rule.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class NotificationLogListView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "notifications.write"

    def get(self, request):
        qs = NotificationLog.objects.filter(tenant=request.tenant)[:100]
        return Response({"results": NotificationLogSerializer(qs, many=True).data})
