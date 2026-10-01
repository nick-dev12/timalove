from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0026_guided_intro_clips"),
    ]

    operations = [
        migrations.AlterField(
            model_name="guidedintroclip",
            name="voice_url",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AddField(
            model_name="guidedintroclip",
            name="answer_text",
            field=models.TextField(blank=True, default=""),
        ),
        migrations.AlterField(
            model_name="guidedintroclip",
            name="duration_seconds",
            field=models.PositiveSmallIntegerField(default=0),
        ),
    ]
