"""Tenant / project feature flags (Phase 10 platform gates)."""
from __future__ import annotations


def tenant_settings(tenant) -> dict:
    return dict(getattr(tenant, "settings", None) or {})


def feature_enabled(tenant, *, key: str, default: bool = False) -> bool:
    """
    Read nested flags from Tenant.settings.
    Examples:
      features.ussd
      features.call_hooks
      ai.anomaly_enabled
    """
    settings = tenant_settings(tenant)
    parts = key.split(".")
    cur: object = settings
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    if isinstance(cur, bool):
        return cur
    return bool(cur) if cur is not None else default


def require_feature(tenant, *, key: str, default: bool = False) -> None:
    if not feature_enabled(tenant, key=key, default=default):
        raise PermissionError(f"Feature disabled: {key}")
