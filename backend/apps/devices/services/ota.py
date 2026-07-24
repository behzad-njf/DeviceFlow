"""OTA agent release helpers."""
from __future__ import annotations

import hashlib

from django.db.models import Q

from apps.devices.models import AgentRelease, Device, DeviceCommand
from apps.devices.services.commands import CommandService


def latest_release(*, tenant) -> AgentRelease | None:
    return (
        AgentRelease.objects.filter(is_active=True)
        .filter(Q(tenant=tenant) | Q(tenant__isnull=True))
        .order_by("-created_at")
        .first()
    )


def enqueue_ota(*, device: Device, release: AgentRelease, user=None, request=None):
    url = release.resolved_download_url(request)
    return CommandService.enqueue(
        device=device,
        action=DeviceCommand.Action.INSTALL_UPDATE,
        params={
            "version": release.version,
            "download_url": url,
            "checksum_sha256": release.checksum_sha256,
            "release_id": str(release.id),
        },
        user=user,
    )


def sha256_file(path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()
