from django.utils import timezone

from apps.common.crypto import api_key_prefix, generate_api_key, hash_secret
from apps.projects.models import ApiKey, Project

DEFAULT_SCOPES = [
    "messages.send",
    "messages.read",
    "inbound.read",
]


def create_api_key(
    *,
    project: Project,
    name: str,
    scopes: list[str] | None = None,
    ip_whitelist: list[str] | None = None,
) -> tuple[ApiKey, str]:
    plaintext = generate_api_key()
    api_key = ApiKey.objects.create(
        project=project,
        name=name or "default",
        key_prefix=api_key_prefix(plaintext),
        key_hash=hash_secret(plaintext),
        scopes=scopes or list(DEFAULT_SCOPES),
        ip_whitelist=ip_whitelist or [],
    )
    return api_key, plaintext


def revoke_api_key(api_key: ApiKey) -> ApiKey:
    if api_key.revoked_at is None:
        api_key.revoked_at = timezone.now()
        api_key.save(update_fields=["revoked_at"])
    return api_key


def delete_api_key(api_key: ApiKey) -> None:
    api_key.delete()
