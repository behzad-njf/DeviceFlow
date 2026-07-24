import csv
import io
import json

from django.db import transaction
from django.utils import timezone

from apps.messaging.models import BulkCampaign, BulkCampaignItem
from apps.messaging.services.messages import MessageService
from apps.messaging.services.templates import render_template
from apps.realtime.broadcast import broadcast_tenant
from apps.routing.services.operators import normalize_number


def parse_bulk_payload(data: dict) -> list[dict]:
    """
    Accept:
      { "messages": [ {"to": "...", "text": "..."}, ... ] }
      { "csv": "to,text\\n..." }
      { "rows": [ {"to": "...", "vars": {...}} ], "text": "Hi {{name}}" }
    """
    if data.get("messages"):
        return [
            {
                "to": normalize_number(row["to"]),
                "text": row.get("text") or row.get("body") or "",
                "vars": row.get("vars") or {},
            }
            for row in data["messages"]
            if row.get("to")
        ]

    if data.get("csv"):
        reader = csv.DictReader(io.StringIO(data["csv"]))
        rows = []
        for row in reader:
            to = row.get("to") or row.get("phone") or row.get("number")
            if not to:
                continue
            text = row.get("text") or row.get("body") or data.get("text") or ""
            vars_ = {k: v for k, v in row.items() if k not in {"to", "phone", "number", "text", "body"}}
            rows.append({"to": normalize_number(to), "text": text, "vars": vars_})
        return rows

    if data.get("rows"):
        template = data.get("text") or data.get("body") or ""
        rows = []
        for row in data["rows"]:
            to = row.get("to")
            if not to:
                continue
            vars_ = row.get("vars") or {
                k: v for k, v in row.items() if k not in {"to", "text", "body"}
            }
            text = row.get("text") or row.get("body") or template
            if "{{" in text:
                text = render_template(text, vars_)
            rows.append({"to": normalize_number(to), "text": text, "vars": vars_})
        return rows

    raise ValueError("Provide messages, csv, or rows")


@transaction.atomic
def create_campaign(
    *,
    tenant,
    project=None,
    name: str = "",
    rows: list[dict],
    body_template: str = "",
    mode: str = "general",
    scheduled_at=None,
) -> BulkCampaign:
    campaign = BulkCampaign.objects.create(
        tenant=tenant,
        project=project,
        name=name or f"Bulk {timezone.now().isoformat()}",
        body_template=body_template,
        mode=mode,
        total=len(rows),
        scheduled_at=scheduled_at,
        status=BulkCampaign.Status.PENDING,
    )
    BulkCampaignItem.objects.bulk_create(
        [
            BulkCampaignItem(
                campaign=campaign,
                to_number=row["to"],
                body=row["text"],
            )
            for row in rows
        ]
    )
    return campaign


def publish_campaign_progress(campaign: BulkCampaign) -> None:
    broadcast_tenant(
        campaign.tenant_id,
        "bulk.progress",
        {
            "campaign_id": str(campaign.id),
            "status": campaign.status,
            "total": campaign.total,
            "sent": campaign.sent,
            "failed": campaign.failed,
        },
    )


def process_campaign(campaign_id: str, *, batch_size: int = 50) -> str:
    campaign = BulkCampaign.objects.select_related("project", "tenant").get(id=campaign_id)
    if campaign.status == BulkCampaign.Status.CANCELLED:
        return campaign.status
    if campaign.scheduled_at and campaign.scheduled_at > timezone.now():
        return "scheduled"
    campaign.status = BulkCampaign.Status.RUNNING
    campaign.save(update_fields=["status", "updated_at"])
    publish_campaign_progress(campaign)

    items = list(
        campaign.items.filter(status=BulkCampaignItem.Status.PENDING)[:batch_size]
    )
    for item in items:
        try:
            message = MessageService.enqueue(
                tenant=campaign.tenant,
                to_number=item.to_number,
                body=item.body,
                project=campaign.project,
                mode=campaign.mode,
                meta={"bulk_campaign_id": str(campaign.id)},
            )
            item.message = message
            item.status = BulkCampaignItem.Status.SENT
            campaign.sent += 1
        except Exception as exc:  # noqa: BLE001
            item.status = BulkCampaignItem.Status.FAILED
            item.error = str(exc)[:255]
            campaign.failed += 1
        item.save()
    campaign.save(update_fields=["sent", "failed", "updated_at"])
    publish_campaign_progress(campaign)

    remaining = campaign.items.filter(status=BulkCampaignItem.Status.PENDING).exists()
    if remaining:
        from apps.messaging.tasks import process_bulk_campaign

        process_bulk_campaign.delay(str(campaign.id))
        return campaign.status

    campaign.status = BulkCampaign.Status.COMPLETED
    campaign.save(update_fields=["status", "updated_at"])
    publish_campaign_progress(campaign)
    return campaign.status
