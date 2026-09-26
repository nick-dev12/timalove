from django.db import migrations, models


def approve_pending_members(apps, schema_editor):
    Profile = apps.get_model("core", "Profile")
    Profile.objects.filter(registration_status="pending", role="member").update(
        registration_status="approved"
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0021_lot_b_pending_guided"),
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
                default="approved",
                max_length=20,
            ),
        ),
        migrations.RunPython(approve_pending_members, noop_reverse),
    ]
