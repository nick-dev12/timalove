# Generated manually

import uuid

import django.db.models.deletion
from django.db import migrations, models


def promote_superusers_to_super_admin(apps, schema_editor):
    Profile = apps.get_model("core", "Profile")
    User = apps.get_model("auth", "User")
    for user in User.objects.filter(is_superuser=True):
        Profile.objects.filter(user_id=user.id, role="admin").update(role="super_admin")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0016_promo_codes_monetization"),
    ]

    operations = [
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(max_length=80)),
                ("target_type", models.CharField(blank=True, default="", max_length=40)),
                ("target_id", models.CharField(blank=True, default="", max_length=64)),
                ("target_label", models.CharField(blank=True, default="", max_length=200)),
                ("message", models.TextField()),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "actor",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="audit_actions",
                        to="core.profile",
                    ),
                ),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="AdminTwoFactor",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("secret", models.CharField(max_length=64)),
                ("is_enabled", models.BooleanField(default=False)),
                ("backup_codes", models.JSONField(blank=True, default=list)),
                ("enabled_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "profile",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="admin_two_factor",
                        to="core.profile",
                    ),
                ),
            ],
        ),
        migrations.AlterField(
            model_name="profile",
            name="role",
            field=models.CharField(
                choices=[
                    ("member", "Membre"),
                    ("super_admin", "Super administrateur"),
                    ("admin", "Administrateur"),
                    ("moderator", "Modérateur"),
                    ("support", "Support client"),
                ],
                default="member",
                max_length=20,
            ),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["-created_at"], name="core_auditl_created_6a0b0d_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["action", "-created_at"], name="core_auditl_action_8e1f2a_idx"),
        ),
        migrations.AddIndex(
            model_name="auditlog",
            index=models.Index(fields=["actor", "-created_at"], name="core_auditl_actor_i_5c3d1e_idx"),
        ),
        migrations.RunPython(promote_superusers_to_super_admin, migrations.RunPython.noop),
    ]
