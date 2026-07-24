from django.db import transaction
from django.utils import timezone

from apps.contacts.models import Contact, Conversation
from apps.routing.services.operators import is_valid_phone_number, normalize_number


def upsert_contact(*, tenant, phone_number: str, name: str = "", **kwargs) -> Contact:
    number = normalize_number(phone_number)
    defaults = {**kwargs}
    if name:
        defaults["name"] = name
    contact, _ = Contact.objects.update_or_create(
        tenant=tenant,
        phone_number=number,
        defaults=defaults,
    )
    return contact


def is_send_allowed(*, tenant, phone_number: str, project=None) -> tuple[bool, str | None]:
    number = normalize_number(phone_number)
    contact = Contact.objects.filter(tenant=tenant, phone_number=number).first()
    if contact and contact.is_blacklisted:
        return False, "NUMBER_BLACKLISTED"
    settings = (project.settings if project else {}) or {}
    if settings.get("whitelist_only"):
        if not contact or not contact.is_whitelisted:
            return False, "NUMBER_NOT_WHITELISTED"
    return True, None


def touch_conversation(
    *,
    tenant,
    phone_number: str,
    preview: str,
    when,
    project=None,
    inbound: bool = False,
) -> Conversation:
    number = normalize_number(phone_number)
    contact = Contact.objects.filter(tenant=tenant, phone_number=number).first()
    defaults = {
        "last_message_at": when,
        "last_preview": (preview or "")[:255],
        "contact": contact,
    }
    conversation, created = Conversation.objects.get_or_create(
        tenant=tenant,
        phone_number=number,
        project=project,
        defaults=defaults,
    )
    if not created:
        conversation.last_message_at = when
        conversation.last_preview = defaults["last_preview"]
        if contact:
            conversation.contact = contact
        if inbound:
            conversation.unread_count = (conversation.unread_count or 0) + 1
        conversation.save()
    elif inbound:
        conversation.unread_count = 1
        conversation.save(update_fields=["unread_count", "updated_at"])
    return conversation


def matches_rule(rule, body: str) -> bool:
    text = (body or "").strip()
    keyword = (rule.keyword or "").strip()
    if not keyword:
        return False
    if rule.match_type == rule.MatchType.EXACT:
        return text.lower() == keyword.lower()
    if rule.match_type == rule.MatchType.STARTS_WITH:
        return text.lower().startswith(keyword.lower())
    return keyword.lower() in text.lower()


def find_auto_reply(*, tenant, body: str, project=None):
    from apps.contacts.models import AutoReplyRule

    qs = AutoReplyRule.objects.filter(tenant=tenant, enabled=True).order_by("-priority")
    if project is not None:
        # Prefer project-specific, then tenant-global (project null)
        candidates = list(qs.filter(project=project)) + list(qs.filter(project__isnull=True))
    else:
        candidates = list(qs.filter(project__isnull=True))
    for rule in candidates:
        if matches_rule(rule, body):
            return rule
    return None


def preview_contact_import(*, tenant, rows: list[dict]) -> dict:
    """
    Validate raw phonebook rows before import.
    Each row: {name?, phone|phone_number}
    """
    valid: list[dict] = []
    invalid: list[dict] = []
    seen: set[str] = set()
    candidates: list[tuple[str, str, str]] = []  # name, phone, phone_raw

    for raw_row in rows or []:
        if not isinstance(raw_row, dict):
            invalid.append({"name": "", "phone": "", "reason": "invalid_row"})
            continue
        name = str(raw_row.get("name") or "").strip()[:255]
        phone_raw = str(
            raw_row.get("phone")
            or raw_row.get("phone_number")
            or raw_row.get("number")
            or ""
        ).strip()
        if not is_valid_phone_number(phone_raw):
            invalid.append(
                {
                    "name": name,
                    "phone": phone_raw,
                    "reason": "invalid_number",
                }
            )
            continue
        phone = normalize_number(phone_raw)
        if phone in seen:
            invalid.append(
                {
                    "name": name,
                    "phone": phone_raw,
                    "normalized": phone,
                    "reason": "duplicate_in_batch",
                }
            )
            continue
        seen.add(phone)
        candidates.append((name, phone, phone_raw))

    existing_map = {
        c.phone_number: c
        for c in Contact.objects.filter(
            tenant=tenant, phone_number__in=[p for _, p, _ in candidates]
        ).only("id", "phone_number", "name")
    }

    for name, phone, phone_raw in candidates:
        existing = existing_map.get(phone)
        valid.append(
            {
                "name": name,
                "phone": phone,
                "phone_raw": phone_raw,
                "exists": bool(existing),
                "existing_id": str(existing.id) if existing else None,
                "existing_name": (existing.name if existing else "") or "",
            }
        )

    return {
        "valid": valid,
        "invalid": invalid,
        "summary": {
            "total": len(rows or []),
            "valid": len(valid),
            "invalid": len(invalid),
            "already_exist": sum(1 for row in valid if row["exists"]),
        },
    }


def import_contacts(
    *,
    tenant,
    rows: list[dict],
    device=None,
    update_existing: bool = True,
) -> dict:
    """
    Import only rows with valid phone numbers.
    Uses bulk create/update in chunks to reduce SQLite lock time.
    """
    preview = preview_contact_import(tenant=tenant, rows=rows)
    created = 0
    updated = 0
    skipped = 0
    imported: list[dict] = []

    phones = [row["phone"] for row in preview["valid"]]
    existing_map = {
        c.phone_number: c
        for c in Contact.objects.filter(tenant=tenant, phone_number__in=phones)
    }

    to_create: list[Contact] = []
    to_update: list[Contact] = []

    for row in preview["valid"]:
        phone = row["phone"]
        name = row["name"]
        contact = existing_map.get(phone)
        if contact:
            if not update_existing:
                skipped += 1
                imported.append(
                    {
                        "id": str(contact.id),
                        "phone": contact.phone_number,
                        "name": contact.name,
                        "action": "skipped",
                    }
                )
                continue
            changed = False
            if name and contact.name != name:
                contact.name = name
                changed = True
            if device is not None and contact.source_device_id != getattr(device, "id", None):
                contact.source_device = device
                changed = True
            meta = dict(contact.meta or {})
            sources = list(meta.get("import_device_ids") or [])
            if device is not None and str(device.id) not in sources:
                sources.append(str(device.id))
                meta["import_device_ids"] = sources
                contact.meta = meta
                changed = True
            if changed:
                to_update.append(contact)
                updated += 1
                action = "updated"
            else:
                skipped += 1
                action = "skipped"
            imported.append(
                {
                    "id": str(contact.id),
                    "phone": contact.phone_number,
                    "name": contact.name if not name else (name or contact.name),
                    "action": action,
                }
            )
            continue

        meta = {}
        if device is not None:
            meta["import_device_ids"] = [str(device.id)]
        contact = Contact(
            tenant=tenant,
            phone_number=phone,
            name=name,
            source_device=device,
            meta=meta,
        )
        to_create.append(contact)
        created += 1

    chunk_size = 80
    now = timezone.now()
    for contact in to_update:
        contact.updated_at = now
    with transaction.atomic():
        for i in range(0, len(to_create), chunk_size):
            chunk = to_create[i : i + chunk_size]
            Contact.objects.bulk_create(chunk, batch_size=chunk_size)
        if to_update:
            Contact.objects.bulk_update(
                to_update,
                fields=["name", "source_device", "meta", "updated_at"],
                batch_size=chunk_size,
            )

    # Refresh created IDs for response (bulk_create may not set them on all backends,
    # but SQLite/Django does set PKs when using UUIDField default).
    for contact in to_create:
        imported.append(
            {
                "id": str(contact.id),
                "phone": contact.phone_number,
                "name": contact.name,
                "action": "created",
            }
        )

    return {
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "rejected": len(preview["invalid"]),
        "invalid": preview["invalid"],
        "imported": imported,
        "summary": {
            **preview["summary"],
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "rejected": len(preview["invalid"]),
        },
    }
