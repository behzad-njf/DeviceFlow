import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.email_utils import normalize_email_identity
from apps.accounts.models import User
from apps.common.crypto import hash_secret
from apps.tenants.models import Membership, Role, TenantInvite


def create_invite(*, tenant, email: str, role: str, invited_by=None, ttl_days: int = 7):
    email = normalize_email_identity(email)
    if role not in {c.value for c in Role}:
        raise ValueError("Invalid role")
    token = secrets.token_urlsafe(32)
    invite = TenantInvite.objects.create(
        tenant=tenant,
        email=email,
        role=role,
        token_hash=hash_secret(token),
        invited_by=invited_by,
        expires_at=timezone.now() + timedelta(days=ttl_days),
    )
    return invite, token


@transaction.atomic
def accept_invite(*, token: str, user: User) -> Membership:
    token_hash = hash_secret(token)
    invite = (
        TenantInvite.objects.select_for_update()
        .select_related("tenant")
        .filter(token_hash=token_hash)
        .first()
    )
    if invite is None or not invite.is_open:
        raise ValueError("Invite is invalid or expired")
    if normalize_email_identity(invite.email) != normalize_email_identity(user.email):
        raise ValueError("Invite email does not match signed-in user")

    membership, created = Membership.objects.get_or_create(
        tenant=invite.tenant,
        user=user,
        defaults={"role": invite.role, "is_active": True},
    )
    if not created:
        membership.role = invite.role
        membership.is_active = True
        membership.save(update_fields=["role", "is_active", "updated_at"])

    invite.accepted_at = timezone.now()
    invite.save(update_fields=["accepted_at"])
    return membership
