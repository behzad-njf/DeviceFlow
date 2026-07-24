from django.urls import path

from .views import (
    AnalyticsDevicesView,
    AnalyticsLatencyView,
    AnalyticsOperatorsView,
    AnalyticsOverviewView,
    AnalyticsTimeseriesView,
    DeviceMapView,
    QueuesSummaryView,
)

urlpatterns = [
    path("analytics/overview/", AnalyticsOverviewView.as_view(), name="analytics-overview"),
    path(
        "analytics/timeseries/",
        AnalyticsTimeseriesView.as_view(),
        name="analytics-timeseries",
    ),
    path(
        "analytics/operators/",
        AnalyticsOperatorsView.as_view(),
        name="analytics-operators",
    ),
    path("analytics/devices/", AnalyticsDevicesView.as_view(), name="analytics-devices"),
    path("analytics/latency/", AnalyticsLatencyView.as_view(), name="analytics-latency"),
    path("devices/map/", DeviceMapView.as_view(), name="devices-map"),
    path("queues/summary/", QueuesSummaryView.as_view(), name="queues-summary"),
]
