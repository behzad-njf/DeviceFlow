from django.urls import path

from .views import (
    OperatorPrefixListView,
    RoutingConfigView,
    RoutingRuleDetailView,
    RoutingRuleListCreateView,
)

urlpatterns = [
    path("routing-rules/", RoutingRuleListCreateView.as_view(), name="routing-rules-list"),
    path(
        "routing-rules/<uuid:rule_id>/",
        RoutingRuleDetailView.as_view(),
        name="routing-rules-detail",
    ),
    path("routing/config/", RoutingConfigView.as_view(), name="routing-config"),
    path(
        "routing/operators/",
        OperatorPrefixListView.as_view(),
        name="routing-operators",
    ),
]
