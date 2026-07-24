from django.urls import re_path

from apps.realtime.consumers import AgentConsumer, DashboardConsumer

websocket_urlpatterns = [
    re_path(r"ws/dashboard/$", DashboardConsumer.as_asgi()),
    re_path(r"ws/agent/$", AgentConsumer.as_asgi()),
]
