from django.urls import path

from .views import (
    AgentCommandAckView,
    AgentHeartbeatView,
    AgentOtaCheckView,
    AgentPairView,
    AgentPendingCommandsView,
    AgentReleaseListCreateView,
    DeviceActionView,
    DeviceCommandCreateView,
    DeviceCommandDetailView,
    DeviceDetailView,
    DeviceEventsView,
    DeviceListView,
    DeviceOtaPushView,
    DeviceQueueView,
    PairingCodeCreateView,
)

urlpatterns = [
    path("devices/", DeviceListView.as_view(), name="devices-list"),
    path("devices/pairing-code/", PairingCodeCreateView.as_view(), name="devices-pairing-code"),
    path("devices/<uuid:device_id>/", DeviceDetailView.as_view(), name="devices-detail"),
    path("devices/<uuid:device_id>/events/", DeviceEventsView.as_view(), name="devices-events"),
    path("devices/<uuid:device_id>/queue/", DeviceQueueView.as_view(), name="devices-queue"),
    path(
        "devices/<uuid:device_id>/commands/",
        DeviceCommandCreateView.as_view(),
        name="devices-commands",
    ),
    path(
        "devices/<uuid:device_id>/commands/<uuid:command_id>/",
        DeviceCommandDetailView.as_view(),
        name="devices-command-detail",
    ),
    path(
        "devices/<uuid:device_id>/actions/",
        DeviceActionView.as_view(),
        name="devices-actions",
    ),
    path(
        "devices/<uuid:device_id>/ota/",
        DeviceOtaPushView.as_view(),
        name="devices-ota",
    ),
    path("agent/releases/", AgentReleaseListCreateView.as_view(), name="agent-releases"),
    path("agent/pair/", AgentPairView.as_view(), name="agent-pair"),
    path("agent/heartbeat/", AgentHeartbeatView.as_view(), name="agent-heartbeat"),
    path("agent/ota/check/", AgentOtaCheckView.as_view(), name="agent-ota-check"),
    path(
        "agent/commands/pending/",
        AgentPendingCommandsView.as_view(),
        name="agent-commands-pending",
    ),
    path(
        "agent/commands/<uuid:command_id>/ack/",
        AgentCommandAckView.as_view(),
        name="agent-command-ack",
    ),
]
