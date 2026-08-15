from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_profile_location_values"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="commune",
            field=models.CharField(blank=True, default="", max_length=180),
        ),
        migrations.AddField(
            model_name="profile",
            name="relationship_intent",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="profile",
            name="life_project",
            field=models.TextField(blank=True, default=""),
        ),
    ]
