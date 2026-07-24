from django.urls import path

from .views import PluginCatalogView, PluginInstallView, PluginInstallationDetailView

urlpatterns = [
    path("plugins/", PluginCatalogView.as_view(), name="plugins-catalog"),
    path("plugins/install/", PluginInstallView.as_view(), name="plugins-install"),
    path(
        "plugins/<str:plugin_id>/",
        PluginInstallationDetailView.as_view(),
        name="plugins-detail",
    ),
]
