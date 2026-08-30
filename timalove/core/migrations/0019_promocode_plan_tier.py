from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_crm_marketing"),
    ]

    operations = [
        migrations.AddField(
            model_name="promocode",
            name="plan_tier",
            field=models.CharField(blank=True, default="", max_length=30),
        ),
    ]
