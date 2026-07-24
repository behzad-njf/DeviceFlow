from django.utils.text import slugify

from .models import Membership, Role, Tenant


def create_tenant_with_owner(*, owner, name: str, slug: str | None = None) -> Tenant:
    tenant = Tenant(name=name, slug=slug or slugify(name)[:64])
    tenant.save()
    Membership.objects.create(
        tenant=tenant,
        user=owner,
        role=Role.ADMIN,
    )
    return tenant
