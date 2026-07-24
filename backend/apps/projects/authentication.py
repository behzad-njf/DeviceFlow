from ipaddress import ip_address, ip_network

from django.contrib.auth.models import AnonymousUser
from django.db.models import F
from django.utils import timezone
from rest_framework import authentication, exceptions

from apps.common.crypto import hash_secret
from apps.projects.models import ApiKey


class ApiKeyAuthentication(authentication.BaseAuthentication):
    """
    Authenticate with `Authorization: ApiKey df_live_...` or `X-API-Key`.
    Attaches request.api_key, request.tenant, request.project.
    """

    keyword = "ApiKey"

    def authenticate(self, request):
        raw = self._extract_key(request)
        if not raw:
            return None

        key_hash = hash_secret(raw)
        api_key = (
            ApiKey.objects.select_related("project", "project__tenant")
            .filter(key_hash=key_hash, revoked_at__isnull=True)
            .first()
        )
        if api_key is None or not api_key.project.is_active:
            raise exceptions.AuthenticationFailed(
                detail="Invalid API key", code="invalid_api_key"
            )

        client_ip = self._client_ip(request)
        if api_key.ip_whitelist and not self._ip_allowed(client_ip, api_key.ip_whitelist):
            raise exceptions.AuthenticationFailed(
                detail="Client IP not allowed for this API key",
                code="ip_not_allowed",
            )

        ApiKey.objects.filter(id=api_key.id).update(
            last_used_at=timezone.now(),
            usage_count=F("usage_count") + 1,
        )
        # Keep in-memory instance roughly in sync for this request.
        api_key.last_used_at = timezone.now()
        api_key.usage_count = (api_key.usage_count or 0) + 1

        request.api_key = api_key
        request.tenant = api_key.project.tenant
        request.project = api_key.project
        return (AnonymousUser(), api_key)

    def authenticate_header(self, request):
        return self.keyword

    def _extract_key(self, request) -> str | None:
        header = request.headers.get("Authorization") or ""
        if header.startswith(f"{self.keyword} "):
            return header[len(self.keyword) + 1 :].strip()
        return request.headers.get("X-API-Key") or None

    def _client_ip(self, request) -> str | None:
        forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.META.get("REMOTE_ADDR")

    def _ip_allowed(self, client_ip: str | None, whitelist: list) -> bool:
        if not client_ip:
            return False
        try:
            addr = ip_address(client_ip)
        except ValueError:
            return False
        for entry in whitelist:
            try:
                if "/" in str(entry):
                    if addr in ip_network(str(entry), strict=False):
                        return True
                elif addr == ip_address(str(entry)):
                    return True
            except ValueError:
                continue
        return False


def bump_api_key_messages(api_key, count: int = 1) -> None:
    if not api_key or count <= 0:
        return
    ApiKey.objects.filter(id=api_key.id).update(
        messages_sent=F("messages_sent") + count,
        last_used_at=timezone.now(),
    )
