from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0013_profile_is_shadowbanned"),
    ]

    operations = [
        migrations.CreateModel(
            name="PhotoBlacklist",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("photo_hash", models.CharField(max_length=64, unique=True)),
                ("source_url", models.TextField(blank=True, default="")),
                ("reason", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "profile",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="blacklisted_photos",
                        to="core.profile",
                    ),
                ),
                (
                    "report",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="blacklisted_photos",
                        to="core.report",
                    ),
                ),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AlterField(
            model_name="notification",
            name="type",
            field=models.CharField(
                choices=[
                    ("new_like", "Nouveau like"),
                    ("new_match", "Nouveau match"),
                    ("new_message", "Nouveau message"),
                    ("subscription_activated", "Abonnement activé"),
                    ("subscription_expired", "Abonnement expiré"),
                    ("profile_approved", "Profil approuvé"),
                    ("profile_rejected", "Profil refusé"),
                    ("new_registration", "Nouvelle inscription"),
                    ("boost_activated", "Boost activé"),
                    ("moderation_warning", "Avertissement modération"),
                ],
                max_length=40,
            ),
        ),
        migrations.AlterField(
            model_name="report",
            name="reason",
            field=models.CharField(
                choices=[
                    ("fake_profile", "Faux profil / Bot"),
                    ("harassment", "Harcèlement"),
                    ("hate_speech", "Propos haineux"),
                    ("inappropriate_content", "Photos inappropriées"),
                    ("scam", "Demande d'argent"),
                    ("spam", "Spam"),
                    ("other", "Autre"),
                    ("platform", "Plateforme"),
                ],
                max_length=40,
            ),
        ),
    ]
