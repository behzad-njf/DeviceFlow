from django.urls import path

from .views import (
    AgentInboundView,
    AgentMessageStatusView,
    InboundListView,
    MessageAttemptsView,
    MessageCancelView,
    MessageDetailView,
    MessageListView,
    MessageRetryView,
    MessageSendView,
)
from .views_bulk import (
    BulkCampaignDetailView,
    BulkCampaignListView,
    ExportCreateView,
    ExportDetailView,
    MessageBulkSendView,
)
from .views_templates import TemplateDetailView, TemplateListCreateView, TemplateRenderView

urlpatterns = [
    path("messages/send/", MessageSendView.as_view(), name="messages-send"),
    path("messages/send-bulk/", MessageBulkSendView.as_view(), name="messages-send-bulk"),
    path("messages/", MessageListView.as_view(), name="messages-list"),
    path("messages/<uuid:message_id>/", MessageDetailView.as_view(), name="messages-detail"),
    path(
        "messages/<uuid:message_id>/cancel/",
        MessageCancelView.as_view(),
        name="messages-cancel",
    ),
    path(
        "messages/<uuid:message_id>/retry/",
        MessageRetryView.as_view(),
        name="messages-retry",
    ),
    path(
        "messages/<uuid:message_id>/attempts/",
        MessageAttemptsView.as_view(),
        name="messages-attempts",
    ),
    path("bulk-campaigns/", BulkCampaignListView.as_view(), name="bulk-campaigns-list"),
    path(
        "bulk-campaigns/<uuid:campaign_id>/",
        BulkCampaignDetailView.as_view(),
        name="bulk-campaigns-detail",
    ),
    path("exports/", ExportCreateView.as_view(), name="exports-create"),
    path("exports/<uuid:export_id>/", ExportDetailView.as_view(), name="exports-detail"),
    path("inbound/", InboundListView.as_view(), name="inbound-list"),
    path("templates/", TemplateListCreateView.as_view(), name="templates-list"),
    path(
        "templates/<uuid:template_id>/",
        TemplateDetailView.as_view(),
        name="templates-detail",
    ),
    path(
        "templates/<uuid:template_id>/render/",
        TemplateRenderView.as_view(),
        name="templates-render",
    ),
    path(
        "agent/messages/<uuid:message_id>/status/",
        AgentMessageStatusView.as_view(),
        name="agent-message-status",
    ),
    path("agent/inbound/", AgentInboundView.as_view(), name="agent-inbound"),
]
