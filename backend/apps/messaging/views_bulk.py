from pathlib import Path

from django.http import FileResponse
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.permissions import RequirePermission
from apps.messaging.models import BulkCampaign, BulkCampaignItem, ExportJob
from apps.messaging.services.bulk import create_campaign, parse_bulk_payload
from apps.messaging.services.messages import MessageService
from apps.messaging.tasks import process_bulk_campaign, run_export_job


class BulkCampaignSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkCampaign
        fields = (
            "id",
            "project",
            "name",
            "status",
            "body_template",
            "mode",
            "total",
            "sent",
            "failed",
            "scheduled_at",
            "created_at",
            "updated_at",
        )


class ExportJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExportJob
        fields = (
            "id",
            "export_type",
            "format",
            "filters",
            "status",
            "file_path",
            "row_count",
            "error",
            "created_at",
            "updated_at",
        )


class MessageBulkSendView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "messages.send"

    def post(self, request):
        try:
            rows = parse_bulk_payload(request.data if isinstance(request.data, dict) else {})
        except ValueError as exc:
            return Response(
                {"error": {"code": "BAD_REQUEST", "message": str(exc), "details": None}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not rows:
            return Response(
                {
                    "error": {
                        "code": "BAD_REQUEST",
                        "message": "No rows to send",
                        "details": None,
                    }
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        project = None
        if request.data.get("project") or getattr(request, "project", None):
            try:
                project = MessageService.resolve_project(
                    tenant=request.tenant,
                    project_ref=request.data.get("project")
                    or (
                        str(request.project.id)
                        if getattr(request, "project", None)
                        else None
                    ),
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
        campaign = create_campaign(
            tenant=request.tenant,
            project=project,
            name=request.data.get("name") or "",
            rows=rows,
            body_template=request.data.get("text") or request.data.get("body") or "",
            mode=request.data.get("mode") or "general",
            scheduled_at=request.data.get("scheduled_at"),
        )
        api_key = getattr(request, "api_key", None)
        if api_key:
            from apps.projects.authentication import bump_api_key_messages

            bump_api_key_messages(api_key, int(campaign.total or len(rows) or 0))
        process_bulk_campaign.delay(str(campaign.id))
        return Response(
            BulkCampaignSerializer(campaign).data, status=status.HTTP_202_ACCEPTED
        )


class BulkCampaignListView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "messages.read"

    def get(self, request):
        qs = BulkCampaign.objects.filter(tenant=request.tenant)[:50]
        return Response({"results": BulkCampaignSerializer(qs, many=True).data})


class BulkCampaignDetailView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "messages.read"

    def get(self, request, campaign_id):
        campaign = BulkCampaign.objects.filter(
            tenant=request.tenant, id=campaign_id
        ).first()
        if not campaign:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Campaign not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        items = BulkCampaignItem.objects.filter(campaign=campaign)[:100]
        data = BulkCampaignSerializer(campaign).data
        data["items"] = [
            {
                "id": str(i.id),
                "to_number": i.to_number,
                "status": i.status,
                "error": i.error,
                "message_id": str(i.message_id) if i.message_id else None,
            }
            for i in items
        ]
        return Response(data)


class ExportCreateView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "exports.create"

    def post(self, request):
        job = ExportJob.objects.create(
            tenant=request.tenant,
            export_type=request.data.get("type") or "messages",
            format=request.data.get("format") or "json",
            filters=request.data.get("filters") or {},
        )
        run_export_job.delay(str(job.id))
        return Response(ExportJobSerializer(job).data, status=status.HTTP_202_ACCEPTED)


class ExportDetailView(APIView):
    permission_classes = [RequirePermission]
    required_permission = "exports.create"

    def get(self, request, export_id):
        job = ExportJob.objects.filter(tenant=request.tenant, id=export_id).first()
        if not job:
            return Response(
                {"error": {"code": "NOT_FOUND", "message": "Export not found", "details": None}},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = ExportJobSerializer(job).data
        if job.status == ExportJob.Status.READY and request.query_params.get("download") == "1":
            path = Path(job.file_path)
            if path.exists():
                return FileResponse(path.open("rb"), as_attachment=True, filename=path.name)
        return Response(data)
