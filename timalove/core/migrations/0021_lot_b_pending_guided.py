# Generated for Lot B — validation pending + messages guidés

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0020_system_event_monitoring"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="registration_status",
            field=models.CharField(
                choices=[
                    ("pending", "En attente"),
                    ("approved", "Approuvé"),
                    ("rejected", "Rejeté"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="match",
            name="guided_intro_completed",
            field=models.BooleanField(
                default=False,
                help_text="Premier message guidé envoyé dans la conversation.",
            ),
        ),
    ]
