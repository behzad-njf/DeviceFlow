import hashlib
import json
import re

from django.db import IntegrityError, transaction

from apps.messaging.models import IdempotencyRecord, Message, MessageTemplate


VAR_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def render_template(body: str, variables: dict | None = None) -> str:
    variables = variables or {}

    def repl(match: re.Match) -> str:
        name = match.group(1)
        if name not in variables:
            raise ValueError(f"Missing template variable: {name}")
        return str(variables[name])

    return VAR_RE.sub(repl, body)


def extract_variables(body: str) -> list[str]:
    return sorted(set(VAR_RE.findall(body or "")))


def request_fingerprint(payload: dict) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class IdempotencyConflict(Exception):
    def __init__(self, message: str = "Idempotency key reused with different payload"):
        self.message = message
        super().__init__(message)


def get_idempotent_response(*, tenant, key: str, request_hash: str):
    record = IdempotencyRecord.objects.filter(tenant=tenant, key=key).first()
    if record is None:
        return None
    if record.request_hash != request_hash:
        raise IdempotencyConflict()
    return record


def store_idempotent_response(
    *, tenant, key: str, request_hash: str, status_code: int, body: dict
) -> IdempotencyRecord:
    # Ensure JSONField-safe payload (UUIDs etc. from DRF ReturnDict)
    safe_body = json.loads(json.dumps(body, default=str))
    try:
        with transaction.atomic():
            return IdempotencyRecord.objects.create(
                tenant=tenant,
                key=key,
                request_hash=request_hash,
                response_status=status_code,
                response_body=safe_body,
            )
    except IntegrityError:
        existing = get_idempotent_response(
            tenant=tenant, key=key, request_hash=request_hash
        )
        if existing is None:
            raise IdempotencyConflict()
        return existing


def resolve_send_body(
    *,
    text: str | None,
    template: MessageTemplate | None,
    variables: dict | None,
) -> str:
    if template is not None:
        return render_template(template.body, variables)
    if not text:
        raise ValueError("text or template is required")
    return text
