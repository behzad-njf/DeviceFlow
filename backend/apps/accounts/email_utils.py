"""Canonical email identity for login uniqueness."""
from __future__ import annotations


def normalize_email_identity(email: str) -> str:
    """
    Normalize an email for account identity / uniqueness.

    - trim whitespace
    - lowercase entire address (case-insensitive)
    - remove '.' from the local-part (behzad.njf == behzadnjf)
    """
    value = (email or "").strip().lower()
    if not value:
        return value
    if "@" not in value:
        return value.replace(".", "")
    local, _, domain = value.partition("@")
    local = local.replace(".", "")
    # Domain already lowercased; keep host as-is otherwise.
    return f"{local}@{domain}"
