"""Test live like / super like / messagerie entre teste1 et teste2."""

import os
import sys

import django

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from django.contrib.auth import get_user_model
from django.test import Client

from core.controllers import message_controller, swipe_controller
from core.models import Match, Message, Notification, Profile, Swipe
from core.models.choices import MatchStatus, NotificationType

User = get_user_model()
EMAILS = ("teste1@gmail.com", "teste2@gmail.com")
PASSWORD = "Ludvanne12"


def reset_pair(p1, p2):
    Swipe.objects.filter(swiper__in=[p1, p2], swiped__in=[p1, p2]).delete()
    Match.objects.filter(user_1__in=[p1, p2], user_2__in=[p1, p2]).delete()
    Notification.objects.filter(user__in=[p1, p2]).delete()
    Message.objects.filter(match__user_1__in=[p1, p2], match__user_2__in=[p1, p2]).delete()


def main():
    p1 = Profile.objects.get(email=EMAILS[0])
    p2 = Profile.objects.get(email=EMAILS[1])
    for profile in (p1, p2):
        user = profile.user
        user.set_password(PASSWORD)
        user.save()

    reset_pair(p1, p2)
    print("Reset OK")

    r1 = swipe_controller.record_swipe(p1, p2.id, "like")
    assert r1["ok"] and not r1["matched"], r1
    assert Notification.objects.filter(
        user=p2, type=NotificationType.NEW_LIKE, related_user=p1
    ).exists()
    print("teste1 -> like -> teste2 OK + notification")

    client = Client(enforce_csrf_checks=False)
    assert client.login(username=p1.user.username, password=PASSWORD)
    likes = client.get("/likes/")
    assert likes.status_code == 200
    assert str(p2.id).encode() not in likes.content
    print("/likes/ teste1 : teste2 absent (like envoyé, pas reçu) OK")

    client.logout()
    assert client.login(username=p2.user.username, password=PASSWORD)
    likes = client.get("/likes/")
    assert likes.status_code == 200 and str(p1.id).encode() in likes.content
    print("/likes/ teste2 voit teste1 OK")

    r2 = swipe_controller.record_swipe(p2, p1.id, "super_like")
    assert r2["ok"] and r2["matched"], r2
    match = Match.objects.filter(
        user_1__in=[p1, p2], user_2__in=[p1, p2], status=MatchStatus.ACTIVE
    ).first()
    assert match, "match manquant"
    print("teste2 -> super_like -> teste1 OK + match", match.id)

    likes = client.get("/likes/")
    assert likes.status_code == 200 and str(p1.id).encode() not in likes.content
    print("/likes/ teste2 : teste1 absent après match OK")

    ok1, err1, _ = message_controller.send_text(p1, p2.id, "Salut depuis teste1")
    assert ok1, err1
    ok2, err2, _ = message_controller.send_text(p2, p1.id, "Réponse teste2")
    assert ok2, err2
    print("Messages envoyés OK")

    client.logout()
    assert client.login(username=p1.user.username, password=PASSWORD)
    inbox = client.get("/messages/")
    assert inbox.status_code == 200 and b"teste2" in inbox.content.lower()
    thread = client.get(f"/discussions/{p2.id}/")
    assert thread.status_code == 200 and b"teste2" in thread.content.lower()
    post = client.post(f"/discussions/{p2.id}/", data={"content": "Via formulaire teste1"})
    assert post.status_code == 302
    assert Message.objects.filter(content="Via formulaire teste1", sender=p1).exists()
    print("Inbox + fil + POST formulaire OK")

    print("\n=== TOUS LES TESTS LIVE OK ===")


if __name__ == "__main__":
    main()
