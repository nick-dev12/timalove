from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0012_match_conversation_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="is_shadowbanned",
            field=models.BooleanField(default=False),
        ),
    ]
