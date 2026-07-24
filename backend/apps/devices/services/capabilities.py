"""Device capability registry (Device Automation Platform)."""
from __future__ import annotations

# Canonical capability IDs
SMS_SEND = "sms.send"
SMS_RECEIVE = "sms.receive"
USSD_RUN = "ussd.run"
CALL_PLACE = "call.place"
CALL_LOG_READ = "call.log.read"
CONTACTS_READ = "contacts.read"
OTA_UPDATE = "ota.update"
APP_HIDE = "app.hide"
APP_LOCK = "app.lock"

ALL_CAPABILITIES = {
    SMS_SEND,
    SMS_RECEIVE,
    USSD_RUN,
    CALL_PLACE,
    CALL_LOG_READ,
    CONTACTS_READ,
    OTA_UPDATE,
    APP_HIDE,
    APP_LOCK,
}

# Default capabilities for a new SMS agent
DEFAULT_CAPABILITIES = [SMS_SEND, SMS_RECEIVE, OTA_UPDATE]

# Capability → DeviceCommand.Action
CAPABILITY_COMMAND = {
    USSD_RUN: "ussd_run",
    CALL_PLACE: "call_place",
    CALL_LOG_READ: "call_log_read",
    CONTACTS_READ: "contacts_read",
    OTA_UPDATE: "install_update",
}

# Feature flag required for experimental capabilities
CAPABILITY_FEATURE_FLAG = {
    USSD_RUN: "features.ussd",
    CALL_PLACE: "features.call_hooks",
    CALL_LOG_READ: "features.call_hooks",
}


def normalize_capabilities(raw) -> list[str]:
    """Map legacy / agent-reported values to canonical IDs."""
    if not raw:
        return list(DEFAULT_CAPABILITIES)
    out: list[str] = []
    for item in raw:
        value = str(item).strip().lower()
        if not value:
            continue
        if value in {"sms", "sms.send_receive"}:
            out.extend([SMS_SEND, SMS_RECEIVE])
            continue
        if value in ALL_CAPABILITIES:
            out.append(value)
            continue
        # Allow dotted custom caps for forward-compat, but keep known only for gating
        if "." in value:
            out.append(value)
    # Always ensure SMS baselines if anything SMS-like was intended
    if not out:
        out = list(DEFAULT_CAPABILITIES)
    # Dedupe preserve order
    seen = set()
    unique = []
    for cap in out:
        if cap not in seen:
            seen.add(cap)
            unique.append(cap)
    return unique


def device_has_capability(device, capability: str) -> bool:
    caps = normalize_capabilities(device.capabilities or [])
    return capability in caps


def merge_reported_capabilities(device, reported) -> list[str]:
    return normalize_capabilities(reported if reported is not None else device.capabilities)
