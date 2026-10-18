import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0008_set_dialer_code"),
        ("projects", "0004_projectdevice_sim_preference"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProjectRouteBinding",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "route_key",
                    models.CharField(
                        help_text="External caller id (e.g. PizoGold customer UUID).",
                        max_length=128,
                    ),
                ),
                (
                    "preferred_sim_slot",
                    models.PositiveSmallIntegerField(
                        blank=True,
                        help_text="Preferred SIM slot (1 or 2) for this route.",
                        null=True,
                    ),
                ),
                (
                    "sim_fallback_enabled",
                    models.BooleanField(
                        default=True,
                        help_text="Allow another SIM if the preferred slot is unavailable.",
                    ),
                ),
                ("label", models.CharField(blank=True, default="", max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="route_bindings",
                        to="devices.device",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="route_bindings",
                        to="projects.project",
                    ),
                ),
            ],
            options={
                "ordering": ["route_key"],
                "unique_together": {("project", "route_key")},
            },
        ),
        migrations.AddIndex(
            model_name="projectroutebinding",
            index=models.Index(
                fields=["project", "route_key"],
                name="projects_pr_project_7c0b0d_idx",
            ),
        ),
    ]
