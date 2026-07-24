from collections import defaultdict

from django.db import migrations

from apps.accounts.email_utils import normalize_email_identity


def _score(user):
    last_login = user.last_login.timestamp() if user.last_login else 0.0
    joined = user.date_joined.timestamp() if user.date_joined else 0.0
    # Prefer superuser/staff, then most recent login, then earliest account.
    return (
        1 if user.is_superuser else 0,
        1 if user.is_staff else 0,
        last_login,
        -joined,
    )


def normalize_and_dedupe_emails(apps, schema_editor):
    User = apps.get_model("accounts", "User")
    Membership = apps.get_model("tenants", "Membership")
    TenantInvite = apps.get_model("tenants", "TenantInvite")
    AuditLog = apps.get_model("audit", "AuditLog")
    DeviceCommand = apps.get_model("devices", "DeviceCommand")

    groups: dict[str, list] = defaultdict(list)
    for user in User.objects.all():
        groups[normalize_email_identity(user.email)].append(user)

    for email_key, users in groups.items():
        users.sort(key=_score, reverse=True)
        keeper = users[0]

        for dup in users[1:]:
            for membership in Membership.objects.filter(user_id=dup.id):
                exists = Membership.objects.filter(
                    tenant_id=membership.tenant_id, user_id=keeper.id
                ).exists()
                if exists:
                    membership.delete()
                else:
                    membership.user_id = keeper.id
                    membership.save(update_fields=["user_id"])

            TenantInvite.objects.filter(invited_by_id=dup.id).update(
                invited_by_id=keeper.id
            )
            TenantInvite.objects.filter(email__iexact=dup.email).update(email=email_key)
            AuditLog.objects.filter(actor_user_id=dup.id).update(actor_user_id=keeper.id)
            DeviceCommand.objects.filter(created_by_id=dup.id).update(
                created_by_id=keeper.id
            )
            # Delete first so unique(email) is free for keeper rename.
            dup.delete()

        if keeper.email != email_key:
            keeper.email = email_key
            keeper.save(update_fields=["email"])

    # Normalize remaining invite emails even without user duplicates.
    for invite in TenantInvite.objects.all():
        normalized = normalize_email_identity(invite.email)
        if invite.email != normalized:
            invite.email = normalized
            invite.save(update_fields=["email"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("accounts", "0001_initial"),
        ("tenants", "0002_tenantinvite"),
        ("audit", "0001_initial"),
        ("devices", "0002_devicecommand"),
    ]

    operations = [
        migrations.RunPython(normalize_and_dedupe_emails, noop_reverse),
    ]
