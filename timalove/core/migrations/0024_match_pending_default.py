from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0023_marriage_project"),
    ]

    operations = [
        migrations.AlterField(
            model_name="match",
            name="conversation_status",
            field=models.CharField(
                choices=[
                    ("pending", "En attente"),
                    ("accepted", "Acceptée"),
                    ("declined", "Refusée"),
                    ("closed", "Clôturée"),
                    ("blocked", "Bloquée"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
    ]
