from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0025_profile_voice_intro"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="guided_intro_submitted",
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name="GuidedIntroClip",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("step", models.PositiveSmallIntegerField()),
                ("question", models.CharField(max_length=280)),
                ("voice_url", models.TextField()),
                ("duration_seconds", models.PositiveSmallIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "match",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="guided_clips",
                        to="core.match",
                    ),
                ),
                (
                    "sender",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="guided_intro_clips",
                        to="core.profile",
                    ),
                ),
            ],
            options={
                "ordering": ["step", "created_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="guidedintroclip",
            constraint=models.UniqueConstraint(
                fields=("match", "sender", "step"),
                name="unique_guided_clip_step",
            ),
        ),
        migrations.AddIndex(
            model_name="guidedintroclip",
            index=models.Index(fields=["match", "step"], name="core_guided_match_i_idx"),
        ),
    ]
