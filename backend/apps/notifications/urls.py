from django.urls import path

from .views import (
    NotificationChannelDetailView,
    NotificationChannelListCreateView,
    NotificationLogListView,
    NotificationRuleDetailView,
    NotificationRuleListCreateView,
)

urlpatterns = [
    path(
        "notifications/channels/",
        NotificationChannelListCreateView.as_view(),
        name="notification-channels",
    ),
    path(
        "notifications/channels/<uuid:channel_id>/",
        NotificationChannelDetailView.as_view(),
        name="notification-channel-detail",
    ),
    path(
        "notifications/rules/",
        NotificationRuleListCreateView.as_view(),
        name="notification-rules",
    ),
    path(
        "notifications/rules/<uuid:rule_id>/",
        NotificationRuleDetailView.as_view(),
        name="notification-rule-detail",
    ),
    path(
        "notifications/logs/",
        NotificationLogListView.as_view(),
        name="notification-logs",
    ),
]
