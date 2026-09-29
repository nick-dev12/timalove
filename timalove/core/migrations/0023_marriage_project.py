from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0022_auto_approve_registration"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="marriage_timeline",
            field=models.CharField(
                blank=True,
                choices=[
                    ("under_1y", "Moins d'un an"),
                    ("1_2y", "1-2 ans"),
                    ("over_2y", "Plus de 2 ans"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="union_type",
            field=models.CharField(
                blank=True,
                choices=[
                    ("monogame", "Monogame"),
                    ("polygame", "Polygame"),
                    ("open", "Ouvert(e) aux deux"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="children_wish",
            field=models.CharField(
                blank=True,
                choices=[
                    ("yes", "Oui"),
                    ("no", "Non"),
                    ("maybe", "Peut-être"),
                    ("already", "J'en ai déjà"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="partner_religion_importance",
            field=models.CharField(
                blank=True,
                choices=[
                    ("same", "Même religion"),
                    ("some", "Certaines religions"),
                    ("any", "Peu importe"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="profile",
            name="meet_place",
            field=models.CharField(
                blank=True,
                choices=[
                    ("near", "Près de moi"),
                    ("country", "Dans mon pays"),
                    ("diaspora", "Afrique & diaspora"),
                    ("anywhere", "Partout"),
                ],
                default="",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="match",
            name="close_reason",
            field=models.CharField(blank=True, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="match",
            name="user_1_ready",
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name="match",
            name="user_2_ready",
            field=models.BooleanField(default=False),
        ),
        migrations.AlterField(
            model_name="match",
            name="conversation_status",
            field=models.CharField(
                choices=[
                    ("pending", "En attente"),
                    ("accepted", "Acceptée"),
                    ("declined", "Refusée"),
                    ("closed", "Clôturée"),
                    ("blocked", "Bloquée"),
                ],
                default="accepted",
                max_length=20,
            ),
        ),
    ]
