from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0009_match_is_one_sided"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="likes_inbox_seen_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
