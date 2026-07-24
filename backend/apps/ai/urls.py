from django.urls import path

from .views import AnomalyScanView, InboxDraftView, RoutingSuggestionsView

urlpatterns = [
    path("ai/anomalies/scan/", AnomalyScanView.as_view(), name="ai-anomaly-scan"),
    path(
        "ai/routing/suggestions/",
        RoutingSuggestionsView.as_view(),
        name="ai-routing-suggestions",
    ),
    path(
        "ai/conversations/<uuid:conversation_id>/draft/",
        InboxDraftView.as_view(),
        name="ai-inbox-draft",
    ),
]
