import csv
import json
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from apps.messaging.models import ExportJob, Message


def run_export(job_id: str) -> ExportJob:
    job = ExportJob.objects.select_related("tenant").get(id=job_id)
    job.status = ExportJob.Status.RUNNING
    job.save(update_fields=["status", "updated_at"])

    try:
        qs = Message.objects.filter(tenant=job.tenant).select_related(
            "device", "project"
        )
        filters = job.filters or {}
        if status_filter := filters.get("status"):
            qs = qs.filter(status=status_filter)
        if project := filters.get("project"):
            qs = qs.filter(project_id=project)
        if to_number := filters.get("to"):
            qs = qs.filter(to_number__icontains=to_number)
        qs = qs.order_by("-created_at")[:5000]

        export_dir = Path(settings.BASE_DIR) / "media" / "exports" / str(job.tenant_id)
        export_dir.mkdir(parents=True, exist_ok=True)
        ext = "csv" if job.format == "csv" else "json"
        path = export_dir / f"{job.id}.{ext}"

        rows = []
        for msg in qs:
            rows.append(
                {
                    "id": str(msg.id),
                    "to": msg.to_number,
                    "body": msg.body,
                    "status": msg.status,
                    "mode": msg.mode,
                    "device": msg.device.name if msg.device_id else "",
                    "project": msg.project.slug if msg.project_id else "",
                    "created_at": msg.created_at.isoformat(),
                    "sent_at": msg.sent_at.isoformat() if msg.sent_at else "",
                }
            )

        if job.format == "csv":
            with path.open("w", newline="", encoding="utf-8") as fh:
                if rows:
                    writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
                    writer.writeheader()
                    writer.writerows(rows)
                else:
                    fh.write("id,to,body,status,mode,device,project,created_at,sent_at\n")
        else:
            path.write_text(
                json.dumps(
                    {"exported_at": timezone.now().isoformat(), "results": rows},
                    indent=2,
                ),
                encoding="utf-8",
            )

        job.file_path = str(path)
        job.row_count = len(rows)
        job.status = ExportJob.Status.READY
        job.error = ""
        job.save()
    except Exception as exc:  # noqa: BLE001
        job.status = ExportJob.Status.FAILED
        job.error = str(exc)[:2000]
        job.save(update_fields=["status", "error", "updated_at"])
    return job
