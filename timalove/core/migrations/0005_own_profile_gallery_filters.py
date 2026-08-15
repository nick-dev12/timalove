from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0004_onboarding_fields"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="profilegalleryphoto",
            name="gallery_position_1_3",
        ),
        migrations.AddField(
            model_name="profile",
            name="discover_filters",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
