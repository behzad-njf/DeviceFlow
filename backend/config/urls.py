from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.common.metrics import MetricsView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.tenants.urls")),
    path("api/v1/", include("apps.projects.urls")),
    path("api/v1/", include("apps.devices.urls")),
    path("api/v1/", include("apps.messaging.urls")),
    path("api/v1/", include("apps.routing.urls")),
    path("api/v1/", include("apps.webhooks.urls")),
    path("api/v1/", include("apps.contacts.urls")),
    path("api/v1/", include("apps.audit.urls")),
    path("api/v1/", include("apps.analytics.urls")),
    path("api/v1/", include("apps.plugins.urls")),
    path("api/v1/", include("apps.notifications.urls")),
    path("api/v1/", include("apps.automations.urls")),
    path("api/v1/", include("apps.ai.urls")),
    path("api/v1/health/", include("apps.common.urls")),
    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/v1/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path("metrics", MetricsView.as_view(), name="metrics"),
    path("metrics/", MetricsView.as_view()),
]

if settings.DEBUG:
    urlpatterns += [
        path(
            "media/<path:path>",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        ),
    ]
