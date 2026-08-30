# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0014_photo_blacklist_moderation"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="currency",
            field=models.CharField(default="XOF", max_length=8),
        ),
        migrations.AddField(
            model_name="transaction",
            name="refunded_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="payment_method",
            field=models.CharField(
                blank=True,
                choices=[
                    ("wave", "Wave"),
                    ("orange_money", "Orange Money"),
                    ("cb", "Carte bancaire"),
                    ("stripe", "Stripe"),
                    ("apple_pay", "Apple Pay"),
                    ("google_pay", "Google Pay"),
                ],
                max_length=30,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="status",
            field=models.CharField(
                choices=[
                    ("pending", "En attente"),
                    ("paid", "Payé"),
                    ("failed", "Échoué"),
                    ("refunded", "Remboursé"),
                    ("dispute", "Litige / Chargeback"),
                ],
                default="pending",
                max_length=20,
            ),
        ),
        migrations.AlterField(
            model_name="transaction",
            name="type",
            field=models.CharField(
                choices=[
                    ("subscription", "Abonnement"),
                    ("coaching", "Coaching"),
                    ("boost", "Boost"),
                    ("super_like", "Super-Like"),
                ],
                max_length=30,
            ),
        ),
    ]
