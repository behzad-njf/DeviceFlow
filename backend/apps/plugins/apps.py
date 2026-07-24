from django.apps import AppConfig


class PluginsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.plugins"
    label = "plugins"

    def ready(self):
        # Discover filesystem plugins once Django is fully loaded
        try:
            from apps.plugins.registry import get_registry

            get_registry().discover()
        except Exception:  # noqa: BLE001 — never block startup
            pass
