"""Generic capability-based device actions."""
from __future__ import annotations

from apps.common.features import feature_enabled, require_feature
from apps.devices.models import Device, DeviceCommand
from apps.devices.services import capabilities as caps
from apps.devices.services.commands import CommandService


class ActionError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def enqueue_action(
    *,
    device: Device,
    capability: str,
    params: dict | None = None,
    user=None,
) -> DeviceCommand:
    capability = str(capability or "").strip()
    if capability not in caps.ALL_CAPABILITIES and capability not in caps.CAPABILITY_COMMAND:
        # Allow only registered platform capabilities
        if capability not in caps.CAPABILITY_COMMAND:
            raise ActionError("UNKNOWN_CAPABILITY", f"Unknown capability: {capability}")

    flag = caps.CAPABILITY_FEATURE_FLAG.get(capability)
    if flag:
        try:
            require_feature(device.tenant, key=flag, default=False)
        except PermissionError as exc:
            raise ActionError("FEATURE_DISABLED", str(exc)) from exc

    if not caps.device_has_capability(device, capability):
        raise ActionError(
            "CAPABILITY_MISSING",
            f"Device does not advertise capability {capability}",
        )

    action = caps.CAPABILITY_COMMAND.get(capability)
    if not action:
        raise ActionError(
            "NOT_ACTIONABLE",
            f"Capability {capability} is informational and has no device action",
        )

    # Ensure DeviceCommand.Action includes this value
    if action not in DeviceCommand.Action.values:
        raise ActionError("UNSUPPORTED_ACTION", f"Action {action} not in command enum")

    return CommandService.enqueue(
        device=device,
        action=action,
        params={**(params or {}), "capability": capability},
        user=user,
    )
