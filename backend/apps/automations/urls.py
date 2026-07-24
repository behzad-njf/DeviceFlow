from django.urls import path

from .views import AutomationRuleDetailView, AutomationRuleListCreateView

urlpatterns = [
    path("automations/", AutomationRuleListCreateView.as_view(), name="automations-list"),
    path(
        "automations/<uuid:rule_id>/",
        AutomationRuleDetailView.as_view(),
        name="automations-detail",
    ),
]
