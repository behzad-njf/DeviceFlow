from apps.audit.models import AuditLog


def _client_ip(request) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def log_audit(
    *,
    action: str,
    tenant=None,
    request=None,
    actor_user=None,
    actor_type: str = "user",
    actor_label: str = "",
    object_type: str = "",
    object_id: str = "",
    before: dict | None = None,
    after: dict | None = None,
) -> AuditLog:
    if request is not None:
        if actor_user is None and getattr(request, "user", None) and request.user.is_authenticated:
            actor_user = request.user
        if not actor_label and actor_user is not None:
            actor_label = getattr(actor_user, "email", "") or str(actor_user.pk)
        if getattr(request, "api_key", None) and actor_type == "user":
            actor_type = "api_key"
            actor_label = request.api_key.key_prefix
        if tenant is None:
            tenant = getattr(request, "tenant", None)
        ip = _client_ip(request)
        ua = (request.META.get("HTTP_USER_AGENT") or "")[:512]
    else:
        ip = None
        ua = ""

    return AuditLog.objects.create(
        tenant=tenant,
        actor_user=actor_user,
        actor_type=actor_type,
        actor_label=actor_label or "",
        action=action,
        object_type=object_type,
        object_id=str(object_id) if object_id else "",
        before=before or {},
        after=after or {},
        ip=ip,
        user_agent=ua,
    )
