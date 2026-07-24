"""
RBAC permission helpers.

Supports JWT membership roles and API key scopes.
"""
from rest_framework.permissions import BasePermission

from apps.tenants.models import Membership, Role


ROLE_PERMISSIONS: dict[str, set[str]] = {
    Role.ADMIN: {
        "tenant.read",
        "tenant.write",
        "users.read",
        "users.invite",
        "users.manage",
        "projects.read",
        "projects.write",
        "apikeys.read",
        "apikeys.write",
        "devices.read",
        "devices.write",
        "devices.command",
        "messages.read",
        "messages.send",
        "messages.cancel",
        "messages.retry",
        "inbound.read",
        "inbound.manage",
        "contacts.read",
        "contacts.write",
        "queues.read",
        "routing.read",
        "routing.write",
        "webhooks.read",
        "webhooks.write",
        "templates.read",
        "templates.write",
        "analytics.read",
        "audit.read",
        "exports.create",
        "settings.write",
        "notifications.write",
        "plugins.manage",
    },
    Role.DEVELOPER: {
        "tenant.read",
        "users.read",
        "projects.read",
        "projects.write",
        "apikeys.read",
        "apikeys.write",
        "devices.read",
        "messages.read",
        "messages.send",
        "messages.cancel",
        "messages.retry",
        "inbound.read",
        "contacts.read",
        "contacts.write",
        "queues.read",
        "routing.read",
        "routing.write",
        "webhooks.read",
        "webhooks.write",
        "templates.read",
        "templates.write",
        "analytics.read",
        "exports.create",
    },
    Role.OPERATOR: {
        "tenant.read",
        "users.read",
        "projects.read",
        "devices.read",
        "devices.write",
        "devices.command",
        "messages.read",
        "messages.send",
        "messages.cancel",
        "messages.retry",
        "inbound.read",
        "inbound.manage",
        "contacts.read",
        "contacts.write",
        "queues.read",
        "routing.read",
        "templates.read",
        "analytics.read",
        "exports.create",
    },
    Role.VIEWER: {
        "tenant.read",
        "users.read",
        "projects.read",
        "devices.read",
        "messages.read",
        "inbound.read",
        "contacts.read",
        "queues.read",
        "routing.read",
        "templates.read",
        "analytics.read",
    },
}

# API key scopes (dot or colon) → permission keys
SCOPE_ALIASES = {
    "messages:send": "messages.send",
    "messages:read": "messages.read",
    "webhooks:manage": "webhooks.write",
    "webhooks:read": "webhooks.read",
    "templates:manage": "templates.write",
    "templates:read": "templates.read",
    "*": "*",
}


def role_has_permission(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, set())


def normalize_scope(scope: str) -> str:
    return SCOPE_ALIASES.get(scope, scope)


def api_key_has_permission(api_key, permission: str) -> bool:
    scopes = [normalize_scope(s) for s in (api_key.scopes or [])]
    if "*" in scopes:
        return True
    if permission in scopes:
        return True
    # Broad read/write helpers
    if permission.startswith("messages.") and "messages.read" in scopes:
        if permission in {"messages.read", "messages.cancel", "messages.retry"}:
            return True
    if permission == "webhooks.read" and "webhooks.write" in scopes:
        return True
    if permission == "templates.read" and "templates.write" in scopes:
        return True
    if permission == "inbound.read" and "messages.read" in scopes:
        return True
    return False


def _resolve_tenant_id(request) -> str | None:
    if getattr(request, "tenant_id", None):
        return str(request.tenant_id)
    header = request.headers.get("X-Tenant-ID")
    if header:
        return header
    token = getattr(request, "auth", None)
    if token is not None and hasattr(token, "get"):
        claim = token.get("tenant_id")
        if claim:
            return str(claim)
    return None


class IsAuthenticatedOrApiKey(BasePermission):
    """JWT user or valid API key."""

    def has_permission(self, request, view):
        if getattr(request, "api_key", None):
            return True
        return bool(request.user and request.user.is_authenticated)


class IsTenantMember(BasePermission):
    """Requires authenticated user with an active membership, or API key context."""

    def has_permission(self, request, view):
        if getattr(request, "api_key", None):
            if not getattr(request, "tenant", None):
                request.tenant = request.api_key.project.tenant
            if not getattr(request, "project", None):
                request.project = request.api_key.project
            return True

        if not request.user or not request.user.is_authenticated:
            return False
        tenant_id = _resolve_tenant_id(request)
        if not tenant_id:
            memberships = Membership.objects.select_related("tenant").filter(
                user=request.user, is_active=True
            )
            if memberships.count() == 1:
                request.membership = memberships.first()
                request.tenant = request.membership.tenant
                return True
            return False
        try:
            membership = Membership.objects.select_related("tenant").get(
                user=request.user, tenant_id=tenant_id, is_active=True
            )
        except Membership.DoesNotExist:
            return False
        request.membership = membership
        request.tenant = membership.tenant
        return True


class RequirePermission(IsTenantMember):
    """Tenant membership / API key + optional `required_permission` on the view."""

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        key = getattr(view, "required_permission", None)
        if not key:
            return True
        if getattr(request, "api_key", None):
            return api_key_has_permission(request.api_key, key)
        return role_has_permission(request.membership.role, key)
