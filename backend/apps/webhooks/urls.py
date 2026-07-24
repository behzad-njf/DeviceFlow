from django.urls import path

from .views import (
    ProjectWebhookDetailView,
    ProjectWebhookListCreateView,
    WebhookDeliveryListView,
    WebhookDeliveryRedeliverView,
)

urlpatterns = [
    path(
        "projects/<uuid:project_id>/webhooks/",
        ProjectWebhookListCreateView.as_view(),
        name="project-webhooks",
    ),
    path(
        "projects/<uuid:project_id>/webhooks/<uuid:endpoint_id>/",
        ProjectWebhookDetailView.as_view(),
        name="project-webhooks-detail",
    ),
    path("webhooks/deliveries/", WebhookDeliveryListView.as_view(), name="webhook-deliveries"),
    path(
        "webhooks/deliveries/<uuid:delivery_id>/redeliver/",
        WebhookDeliveryRedeliverView.as_view(),
        name="webhook-redeliver",
    ),
]
