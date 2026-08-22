"""Match.is_one_sided — conversations sans like retour."""

from django.db import migrations, models
from django.db.models import Q


LIKE_Q = Q(is_like=True) | Q(is_super_like=True) | Q(action="like") | Q(action="super_like")


def mark_one_sided_matches(apps, schema_editor):
    Match = apps.get_model("core", "Match")
    Swipe = apps.get_model("core", "Swipe")
    Profile = apps.get_model("core", "Profile")

    for match in Match.objects.filter(status="active").iterator():
        p1_id = match.user_1_id
        p2_id = match.user_2_id
        p1_liked_p2 = Swipe.objects.filter(swiper_id=p1_id, swiped_id=p2_id).filter(LIKE_Q).exists()
        p2_liked_p1 = Swipe.objects.filter(swiper_id=p2_id, swiped_id=p1_id).filter(LIKE_Q).exists()
        one_sided = (p1_liked_p2 and not p2_liked_p1) or (p2_liked_p1 and not p1_liked_p2)
        if one_sided and match.is_one_sided != one_sided:
            Match.objects.filter(pk=match.pk).update(is_one_sided=one_sided)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0008_profile_signup_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="match",
            name="is_one_sided",
            field=models.BooleanField(
                default=False,
                help_text="Conversation ouverte après like envoyé, sans like retour.",
            ),
        ),
        migrations.RunPython(mark_one_sided_matches, migrations.RunPython.noop),
    ]
