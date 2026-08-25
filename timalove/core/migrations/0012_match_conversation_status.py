# Generated manually — conversation accept/block for VIP recipients

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0011_alter_message_message_type_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="conversation_status",
            field=models.CharField(
                choices=[
                    ("pending", "En attente"),
                    ("accepted", "Acceptée"),
                    ("declined", "Refusée"),
                    ("blocked", "Bloquée"),
                ],
                default="accepted",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="match",
            name="conversation_initiator",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="initiated_conversations",
                to="core.profile",
            ),
        ),
    ]
