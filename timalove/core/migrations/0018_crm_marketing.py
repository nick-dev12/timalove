# Generated manually

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0017_admin_rbac_audit"),
    ]

    operations = [
        migrations.CreateModel(
            name="MarketingCampaign",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "channel",
                    models.CharField(
                        choices=[
                            ("push", "Push notification"),
                            ("email", "Email"),
                            ("in_app", "Popup in-app"),
                            ("push_in_app", "Push + popup in-app"),
                        ],
                        default="push_in_app",
                        max_length=20,
                    ),
                ),
                ("name", models.CharField(max_length=120)),
                ("title", models.CharField(max_length=200)),
                ("body", models.TextField()),
                ("image_url", models.URLField(blank=True, default="", max_length=500)),
                ("deep_link", models.CharField(default="/", max_length=300)),
                ("segment", models.JSONField(blank=True, default=dict)),
                (
                    "send_mode",
                    models.CharField(
                        choices=[("immediate", "Immédiat"), ("scheduled", "Programmé")],
                        default="immediate",
                        max_length=20,
                    ),
                ),
                ("scheduled_at", models.DateTimeField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("draft", "Brouillon"),
                            ("scheduled", "Programmée"),
                            ("sending", "Envoi en cours"),
                            ("sent", "Envoyée"),
                            ("cancelled", "Annulée"),
                        ],
                        default="draft",
                        max_length=20,
                    ),
                ),
                ("recipients_count", models.PositiveIntegerField(default=0)),
                ("delivered_count", models.PositiveIntegerField(default=0)),
                ("opened_count", models.PositiveIntegerField(default=0)),
                ("clicked_count", models.PositiveIntegerField(default=0)),
                ("sent_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="campaigns_created",
                        to="core.profile",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CampaignDelivery",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                (
                    "channel",
                    models.CharField(
                        choices=[
                            ("push", "Push notification"),
                            ("email", "Email"),
                            ("in_app", "Popup in-app"),
                            ("push_in_app", "Push + popup in-app"),
                        ],
                        max_length=20,
                    ),
                ),
                ("delivered_at", models.DateTimeField(auto_now_add=True)),
                ("opened_at", models.DateTimeField(blank=True, null=True)),
                ("clicked_at", models.DateTimeField(blank=True, null=True)),
                ("dismissed_at", models.DateTimeField(blank=True, null=True)),
                ("push_sent", models.BooleanField(default=False)),
                ("email_sent", models.BooleanField(default=False)),
                ("in_app_shown", models.BooleanField(default=False)),
                (
                    "campaign",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deliveries",
                        to="core.marketingcampaign",
                    ),
                ),
                (
                    "profile",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="campaign_deliveries",
                        to="core.profile",
                    ),
                ),
            ],
            options={"ordering": ["-delivered_at"]},
        ),
        migrations.AddConstraint(
            model_name="campaigndelivery",
            constraint=models.UniqueConstraint(fields=("campaign", "profile"), name="uniq_campaign_profile_delivery"),
        ),
        migrations.AddIndex(
            model_name="campaigndelivery",
            index=models.Index(fields=["profile", "-delivered_at"], name="core_campa_profile_8a1b2c_idx"),
        ),
        migrations.AddIndex(
            model_name="campaigndelivery",
            index=models.Index(fields=["campaign", "-delivered_at"], name="core_campa_campaig_3d4e5f_idx"),
        ),
    ]
