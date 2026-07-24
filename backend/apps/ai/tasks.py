from celery import shared_task

from apps.ai.services.anomaly import run_anomaly_scan


@shared_task(name="ai.scan_anomalies")
def scan_anomalies() -> int:
    return run_anomaly_scan()
