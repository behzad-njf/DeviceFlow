from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("devices", "0006_contact_source_device_and_contacts_read"),
    ]

    operations = [
        migrations.AlterField(
            model_name="devicecommand",
            name="action",
            field=models.CharField(
                choices=[
                    ("restart_agent", "Restart agent"),
                    ("sync", "Sync"),
                    ("clear_queue", "Clear local queue"),
                    ("refresh_sim", "Refresh SIM"),
                    ("enable_logs", "Enable logs"),
                    ("install_update", "Install APK update"),
                    ("ussd_run", "Run USSD"),
                    ("call_place", "Place call"),
                    ("call_log_read", "Read call log"),
                    ("contacts_read", "Read contacts"),
                    ("hide_launcher", "Hide launcher icon"),
                    ("show_launcher", "Show launcher icon"),
                    ("lock_ui", "Lock agent UI"),
                    ("unlock_ui", "Unlock agent UI"),
                    ("set_passcode", "Set app passcode"),
                    ("clear_passcode", "Clear app passcode"),
                ],
                max_length=64,
            ),
        ),
    ]
