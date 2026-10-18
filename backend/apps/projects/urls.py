from django.urls import path

from .views import ProjectDetailView, ProjectDevicesView, ProjectListCreateView
from .views_apikeys import (
    ProjectApiKeyDeleteView,
    ProjectApiKeyListCreateView,
    ProjectApiKeyRevokeView,
)
from .views_routes import ProjectRouteDetailView, ProjectRouteListCreateView

urlpatterns = [
    path("projects/", ProjectListCreateView.as_view(), name="projects-list"),
    path("projects/<uuid:project_id>/", ProjectDetailView.as_view(), name="projects-detail"),
    path(
        "projects/<uuid:project_id>/devices/",
        ProjectDevicesView.as_view(),
        name="projects-devices",
    ),
    path(
        "projects/<uuid:project_id>/routes/",
        ProjectRouteListCreateView.as_view(),
        name="projects-routes",
    ),
    path(
        "projects/<uuid:project_id>/routes/<uuid:route_id>/",
        ProjectRouteDetailView.as_view(),
        name="projects-routes-detail",
    ),
    path(
        "projects/<uuid:project_id>/api-keys/",
        ProjectApiKeyListCreateView.as_view(),
        name="project-api-keys",
    ),
    path(
        "projects/<uuid:project_id>/api-keys/<uuid:key_id>/revoke/",
        ProjectApiKeyRevokeView.as_view(),
        name="project-api-keys-revoke",
    ),
    path(
        "projects/<uuid:project_id>/api-keys/<uuid:key_id>/",
        ProjectApiKeyDeleteView.as_view(),
        name="project-api-keys-delete",
    ),
]
