# Generated manually for per-project SIM preference on ProjectDevice

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0003_apikey_usage_stats"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectdevice",
            name="preferred_sim_slot",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Preferred SIM slot (1 or 2) when sending for this project on this device.",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="projectdevice",
            name="sim_fallback_enabled",
            field=models.BooleanField(
                default=True,
                help_text="If preferred SIM is unavailable, allow another active SIM on the device.",
            ),
        ),
    ]
