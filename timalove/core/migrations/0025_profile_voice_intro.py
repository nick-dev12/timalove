from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0024_match_pending_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="voice_intro_url",
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="profile",
            name="voice_intro_duration_seconds",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
