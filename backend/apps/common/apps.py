from django.apps import AppConfig


class CommonConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.common"
    label = "common"
    default = True

    def ready(self):
        # Configure SQLite for concurrent agent heartbeats + dashboard writes.
        from django.db.backends.signals import connection_created
        from django.dispatch import receiver

        @receiver(connection_created)
        def _configure_sqlite(sender, connection, **kwargs):  # noqa: ARG001
            if connection.vendor != "sqlite":
                return
            with connection.cursor() as cursor:
                cursor.execute("PRAGMA journal_mode=WAL;")
                cursor.execute("PRAGMA busy_timeout=30000;")
                cursor.execute("PRAGMA synchronous=NORMAL;")
