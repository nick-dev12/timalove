from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_profile_apple_uid"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="latitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="longitude",
            field=models.DecimalField(blank=True, decimal_places=6, max_digits=10, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="location_updated_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="life_values",
            field=models.JSONField(blank=True, default=list),
        ),
    ]
