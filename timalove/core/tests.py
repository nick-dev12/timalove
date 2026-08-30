from django.contrib.auth import get_user_model
from django.db.models import Q
from django.test import Client, TestCase, override_settings
from datetime import date
from unittest.mock import patch

from core.controllers import swipe_controller, message_controller, payment_controller, profile_controller
from core.models import Profile
from core.models.choices import Gender, RegistrationStatus, UserRole
from core.controllers import site_settings_controller


User = get_user_model()


def make_profile(email, gender, name="Test"):
    user = User.objects.create_user(username=email, email=email, password="pass12345")
    return Profile.objects.create(
        user=user,
        first_name=name,
        last_name="User",
        email=email,
        date_of_birth=date(1998, 5, 5),
        gender=gender,
        city="Dakar",
        registration_status=RegistrationStatus.APPROVED,
        role=UserRole.MEMBER,
    )


class SwipeMatchTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.a = make_profile("a@test.com", Gender.MALE, "Amadou")
        self.b = make_profile("b@test.com", Gender.FEMALE, "Awa")

    def test_reciprocal_like_creates_match(self):
        r1 = swipe_controller.record_swipe(self.a, self.b.id, "like")
        self.assertTrue(r1["ok"])
        self.assertFalse(r1["matched"])
        r2 = swipe_controller.record_swipe(self.b, self.a.id, "like")
        self.assertTrue(r2["matched"])


@override_settings(FREEMIUM_LIMITS_ENABLED=True)
class FreemiumMessageTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        site_settings_controller.set_value("free_messages_limit", 1)
        self.a = make_profile("m1@test.com", Gender.MALE, "Mamadou")
        self.b = make_profile("f1@test.com", Gender.FEMALE, "Fatou")
        swipe_controller.record_swipe(self.a, self.b.id, "like")
        swipe_controller.record_swipe(self.b, self.a.id, "like")

    def test_free_limit(self):
        ok1, _, _ = message_controller.send_text(self.a, self.b.id, "Salut")
        self.assertTrue(ok1)
        ok2, msg, _ = message_controller.send_text(self.a, self.b.id, "Encore")
        self.assertFalse(ok2)
        self.assertIn("Limite", msg)


@override_settings(CINETPAY_APIKEY="", CINETPAY_SITE_ID="", PAYMENT_SIMULATION=True)
class PaymentFulfillTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.a = make_profile("pay@test.com", Gender.MALE, "Pay")

    def test_checkout_and_fulfill(self):
        out = payment_controller.create_checkout(self.a, "premium_10d")
        self.assertTrue(out.get("ok"), out)
        self.assertTrue(out.get("simulated"))
        ok, _ = payment_controller.fulfill_order(out["order_id"])
        self.assertTrue(ok)
        self.a.refresh_from_db()
        self.assertTrue(self.a.has_active_subscription)

    def test_simulate_confirm_only_in_debug_without_keys(self):
        out = payment_controller.create_checkout(self.a, "premium_10d")
        ok, _ = payment_controller.confirm_order(out["order_id"], simulate=True)
        self.assertTrue(ok)

    def test_hmac_token(self):
        from django.test import override_settings
        from core.controllers import cinetpay_controller

        payload = {field: f"v{i}" for i, field in enumerate(cinetpay_controller.HMAC_FIELDS)}
        with override_settings(CINETPAY_SECRET_KEY="secret-test"):
            import hashlib
            import hmac

            data = "".join(str(payload[field]) for field in cinetpay_controller.HMAC_FIELDS)
            token = hmac.new(b"secret-test", data.encode(), hashlib.sha256).hexdigest()
            self.assertTrue(cinetpay_controller.hmac_matches(payload, token))
            self.assertFalse(cinetpay_controller.hmac_matches(payload, "bad"))


@override_settings(CINETPAY_APIKEY="test-key", CINETPAY_SITE_ID="123", NABOOPAY_API_KEY="", PAYMENT_PROVIDER="cinetpay", PAYMENT_SIMULATION=True, DEBUG=True)
class PaymentNetworkFallbackTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.a = make_profile("net@test.com", Gender.MALE, "Net")

    @patch("core.controllers.cinetpay_controller.initialize")
    def test_dns_failure_falls_back_to_local_simulation(self, init):
        init.return_value = {
            "ok": False,
            "network": True,
            "error": "Le service de paiement CinetPay est injoignable pour le moment. Réessayez dans quelques minutes.",
        }
        out = payment_controller.create_checkout(self.a, "pass_amour")
        self.assertTrue(out.get("ok"), out)
        self.assertTrue(out.get("simulated"))
        ok, _ = payment_controller.confirm_order(out["order_id"], simulate=True)
        self.assertTrue(ok)
        self.a.refresh_from_db()
        self.assertTrue(self.a.has_active_subscription)

    def test_network_error_hides_urlopen(self):
        from core.controllers import cinetpay_controller

        with patch("core.controllers.cinetpay_controller.urllib.request.urlopen") as urlopen:
            urlopen.side_effect = OSError("[Errno 11001] getaddrinfo failed")
            result = cinetpay_controller.initialize(
                transaction_id="tx1",
                amount=1000,
                description="test",
                notify_url="https://example.com/n",
                return_url="https://example.com/r",
            )
        self.assertFalse(result.get("ok"))
        self.assertTrue(result.get("network"))
        self.assertNotIn("urlopen", result.get("error", "").lower())
        self.assertNotIn("11001", result.get("error", ""))
        self.assertIn("injoignable", result.get("error", "").lower())

    def test_base_url_override(self):
        from django.test import override_settings
        from core.controllers import cinetpay_controller

        with override_settings(CINETPAY_BASE_URL="https://example.test/v2"):
            self.assertEqual(cinetpay_controller.init_url(), "https://example.test/v2/payment")
            self.assertEqual(cinetpay_controller.check_url(), "https://example.test/v2/payment/check")


class SubscriptionPricesMergeTests(TestCase):
    def test_legacy_prices_fill_current_offers(self):
        site_settings_controller.set_value(
            "subscription_prices",
            {"vip_1m": 20000, "premium_1m": 9000, "premium_10d": 6000},
        )
        prices = site_settings_controller.get("subscription_prices")
        self.assertEqual(prices["vip_1m"], 20000)
        self.assertEqual(prices["journee_amoureuse"], 1000)
        self.assertEqual(prices["pass_amour"], 4500)
        self.assertEqual(prices["eternite"], 29900)
        profile = make_profile("prix@test.com", Gender.MALE, "Prix")
        plans = {item["id"]: item for item in profile_controller.subscription_plans_for(profile)}
        self.assertEqual(plans["premium_1m"]["price"], 9000)
        self.assertEqual(plans["vip_1m"]["price"], 20000)
        self.assertEqual(payment_controller.price_for_tier("premium_1m"), 9000)

    def test_seed_defaults_persists_missing_keys(self):
        site_settings_controller.set_value("subscription_prices", {"vip_1m": 20000})
        site_settings_controller.seed_defaults()
        from core.models import SiteSetting

        stored = SiteSetting.objects.get(key="subscription_prices").value
        self.assertEqual(stored["vip_1m"], 20000)
        self.assertEqual(stored["journee_amoureuse"], 1000)


class LikesMessagingFlowTests(TestCase):
    """Like, super like, match et messagerie entre deux comptes."""

    def setUp(self):
        site_settings_controller.seed_defaults()
        site_settings_controller.set_value("free_messages_limit", 10)
        self.client = Client(enforce_csrf_checks=False)
        self.p1 = make_profile("teste1@gmail.com", Gender.MALE, "Testeur1")
        self.p2 = make_profile("teste2@gmail.com", Gender.FEMALE, "Testeur2")
        for profile in (self.p1, self.p2):
            profile.photo_url = "https://example.com/photo.webp"
            profile.onboarding_completed = True
            profile.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
        self.u1 = self.p1.user
        self.u2 = self.p2.user
        self.u1.set_password("Ludvanne12")
        self.u2.set_password("Ludvanne12")
        self.u1.save()
        self.u2.save()

    def _login(self, user):
        self.assertTrue(self.client.login(username=user.username, password="Ludvanne12"))

    def test_like_super_like_match_and_messages(self):
        from core.models import Match, Message, Notification, Swipe
        from core.models.choices import NotificationType

        self._login(self.u1)
        r = self.client.post(
            "/api/swipes/",
            data='{"swiped_id": "%s", "action": "like"}' % self.p2.id,
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertFalse(r.json()["matched"])
        self.assertTrue(
            Swipe.objects.filter(swiper=self.p1, swiped=self.p2, is_like=True).exists()
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.p2, type=NotificationType.NEW_LIKE, related_user=self.p1
            ).exists()
        )

        self.client.logout()
        self._login(self.u2)
        likes_page = self.client.get("/likes/")
        self.assertEqual(likes_page.status_code, 200)
        self.assertContains(likes_page, str(self.p1.id))

        like_count_before_match = Notification.objects.filter(
            user=self.p1, type=NotificationType.NEW_LIKE, related_user=self.p2
        ).count()

        r = self.client.post(
            "/api/swipes/",
            data='{"swiped_id": "%s", "action": "super_like"}' % self.p1.id,
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["matched"])
        self.assertEqual(
            Notification.objects.filter(
                user=self.p1, type=NotificationType.NEW_LIKE, related_user=self.p2
            ).count(),
            like_count_before_match,
            "Pas de notification like en double lors d'un match.",
        )
        self.assertTrue(
            Notification.objects.filter(
                user=self.p1, type=NotificationType.NEW_MATCH, related_user=self.p2
            ).exists()
        )

        likes_page = self.client.get("/likes/")
        self.assertEqual(likes_page.status_code, 200)
        self.assertContains(likes_page, str(self.p1.id))
        self.assertContains(likes_page, "likes__match-badge")

        self.client.logout()
        self._login(self.u1)
        likes_page = self.client.get("/likes/")
        self.assertEqual(likes_page.status_code, 200)
        self.assertContains(likes_page, str(self.p2.id))
        self.assertContains(likes_page, "likes__match-badge")

        ok, _, msg = message_controller.send_text(self.p1, self.p2.id, "Salut teste2 !")
        self.assertTrue(ok)
        ok2, _, msg2 = message_controller.send_text(self.p2, self.p1.id, "Salut teste1 !")
        self.assertTrue(ok2)
        self.assertEqual(Message.objects.filter(match__user_1__in=[self.p1, self.p2]).count(), 2)

        unread = self.client.get("/api/messages/unread-count/")
        self.assertEqual(unread.status_code, 200)
        self.assertGreaterEqual(unread.json()["count"], 1)
        dock = self.client.get("/likes/")
        self.assertContains(dock, "explorer__tab-badge")
        self.assertContains(dock, "Messages, ")
        self.assertContains(dock, "non lu")

        inbox = self.client.get("/messages/")
        self.assertEqual(inbox.status_code, 200)
        self.assertContains(inbox, "Testeur2")
        self.assertContains(inbox, "Salut teste1")

        thread = self.client.get("/discussions/%s/" % self.p2.id)
        self.assertEqual(thread.status_code, 200)
        self.assertContains(thread, "Salut teste2")

        post_msg = self.client.post(
            "/discussions/%s/" % self.p2.id,
            data={"content": "Message via formulaire"},
        )
        self.assertEqual(post_msg.status_code, 302)
        self.assertTrue(
            Message.objects.filter(content="Message via formulaire", sender=self.p1).exists()
        )

    def test_one_sided_match_shows_no_match_badge_on_likes(self):
        """Conversation ouverte sans like retour : pas de badge match sur /likes/."""
        from core.controllers import likes_controller, message_controller, swipe_controller
        from core.models import Match
        from core.models.choices import MatchStatus

        swipe_controller.record_swipe(self.p1, self.p2.id, "like")
        ok, _, match = message_controller.ensure_conversation(self.p1, self.p2.id)
        self.assertTrue(ok)
        self.assertTrue(match.is_one_sided)

        self._login(self.u2)
        likes_page = self.client.get("/likes/")
        self.assertEqual(likes_page.status_code, 200)
        self.assertContains(likes_page, str(self.p1.id))
        self.assertNotContains(likes_page, "likes__match-badge")

        feed = likes_controller.feed_context(self.p2)
        card = next(item for item in feed["likes"] if item["id"] == str(self.p1.id))
        self.assertFalse(card["is_matched"])
        self.assertFalse(card["already_liked_back"])

    def test_mutual_like_shows_match_badge_on_likes(self):
        from core.controllers import likes_controller, swipe_controller

        swipe_controller.record_swipe(self.p1, self.p2.id, "like")
        swipe_controller.record_swipe(self.p2, self.p1.id, "like")

        feed = likes_controller.feed_context(self.p2)
        card = next(item for item in feed["likes"] if item["id"] == str(self.p1.id))
        self.assertTrue(card["is_matched"])

        self._login(self.u2)
        likes_page = self.client.get("/likes/")
        self.assertContains(likes_page, "likes__match-badge")

    def test_incoming_visible_after_search_like_despite_earlier_pass(self):
        """Like via recherche : visible même si un pass explorer plus ancien existe."""
        from datetime import timedelta

        from django.utils import timezone

        from core.models import Swipe
        from core.models.choices import SwipeAction

        old_pass = Swipe.objects.create(
            swiper=self.p2,
            swiped=self.p1,
            action=SwipeAction.PASS,
            is_like=False,
            is_super_like=False,
        )
        Swipe.objects.filter(pk=old_pass.pk).update(created_at=timezone.now() - timedelta(hours=3))

        self._login(self.u1)
        r = self.client.post(
            "/api/swipes/",
            data='{"swiped_id": "%s", "action": "like"}' % self.p2.id,
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

        self._login(self.u2)
        likes_page = self.client.get("/likes/")
        self.assertEqual(likes_page.status_code, 200)
        self.assertContains(likes_page, str(self.p1.id))

    def test_pass_from_likes_hides_incoming_after_like(self):
        """Passer depuis /likes/ masque le profil après le like reçu."""
        from core.models import Swipe
        from core.models.choices import SwipeAction

        self._login(self.u1)
        self.client.post(
            "/api/swipes/",
            data='{"swiped_id": "%s", "action": "like"}' % self.p2.id,
            content_type="application/json",
        )

        self._login(self.u2)
        r = self.client.post(
            "/api/swipes/",
            data='{"swiped_id": "%s", "action": "pass"}' % self.p1.id,
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertTrue(
            Swipe.objects.filter(
                swiper=self.p2, swiped=self.p1, action=SwipeAction.PASS, is_like=False
            ).exists()
        )

        likes_page = self.client.get("/likes/")
        self.assertEqual(likes_page.status_code, 200)
        self.assertNotContains(likes_page, str(self.p1.id))

    def test_pass_hides_profile_from_explorer_feed_for_14_days(self):
        """Pass explorer : enregistré en base et masqué du feed pendant 14 jours."""
        from datetime import timedelta

        from django.utils import timezone

        from core.controllers import explore_controller
        from core.models import Swipe
        from core.models.choices import SwipeAction

        self._login(self.u1)
        r = self.client.post(
            "/api/swipes/",
            data='{"swiped_id": "%s", "action": "pass"}' % self.p2.id,
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])

        swipe = Swipe.objects.get(swiper=self.p1, swiped=self.p2)
        self.assertEqual(swipe.action, SwipeAction.PASS)
        self.assertFalse(swipe.is_like)

        cards, _ = explore_controller.public_feed(viewer=self.p1, offset=0, limit=50, seed="test")
        self.assertFalse(any(c["id"] == str(self.p2.id) for c in cards))

        Swipe.objects.filter(pk=swipe.pk).update(
            created_at=timezone.now() - timedelta(days=15)
        )
        cards_after, _ = explore_controller.public_feed(viewer=self.p1, offset=0, limit=50, seed="test")
        self.assertTrue(any(c["id"] == str(self.p2.id) for c in cards_after))

    def test_open_conversation_after_outgoing_like(self):
        """Like envoyé : ouverture de conversation sans match réciproque."""
        from core.controllers import message_controller, swipe_controller
        from core.models import Match

        swipe_controller.record_swipe(self.p1, self.p2.id, "like")
        self.assertFalse(Match.objects.filter(user_1=self.p1, user_2=self.p2).exists())
        self.assertFalse(Match.objects.filter(user_1=self.p2, user_2=self.p1).exists())

        ok, msg, match = message_controller.ensure_conversation(self.p1, self.p2.id)
        self.assertTrue(ok, msg)
        self.assertIsNotNone(match)
        self.assertTrue(message_controller.get_active_match(self.p1, self.p2.id))

        from core.controllers import likes_controller

        feed = likes_controller.feed_context(self.p1)
        ids = {item["id"] for item in feed["likes"]}
        self.assertNotIn(str(self.p2.id), ids)

    def test_open_conversation_requires_outgoing_like(self):
        """Sans like envoyé : impossible d'ouvrir une conversation."""
        self._login(self.u1)
        denied = self.client.post(
            "/api/messages/open/",
            data='{"partner_id": "%s"}' % self.p2.id,
            content_type="application/json",
        )
        self.assertEqual(denied.status_code, 400)
        self.assertFalse(denied.json()["ok"])
        self.assertEqual(denied.json()["code"], "like_required")

        from core.controllers import swipe_controller

        swipe_controller.record_swipe(self.p1, self.p2.id, "like")
        allowed = self.client.post(
            "/api/messages/open/",
            data='{"partner_id": "%s"}' % self.p2.id,
            content_type="application/json",
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertTrue(allowed.json()["ok"])
        self.assertIn("/discussions/", allowed.json()["thread_url"])

    def test_send_compressed_chat_image(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        from core.models import Match, Message
        from core.models.choices import MatchStatus, MessageType

        Match.objects.create(user_1=self.p1, user_2=self.p2, status=MatchStatus.ACTIVE)
        canvas = Image.new("RGB", (1600, 900), (232, 99, 122))
        buf = BytesIO()
        canvas.save(buf, format="JPEG", quality=95)
        upload = SimpleUploadedFile("photo.jpg", buf.getvalue(), content_type="image/jpeg")

        self._login(self.u1)
        r = self.client.post(
            "/discussions/%s/media/" % self.p2.id,
            data={"kind": "photo", "file": upload},
        )
        self.assertEqual(r.status_code, 200, r.content)
        payload = r.json()
        self.assertTrue(payload["ok"])
        self.assertTrue(payload["item"]["is_image"])
        self.assertIn("/media/chat-photos/", payload["item"]["image_url"])
        self.assertTrue(
            Message.objects.filter(
                sender=self.p1, message_type=MessageType.IMAGE
            ).exists()
        )


class NotificationFlowTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.p1 = make_profile("notif1@gmail.com", Gender.MALE, "Notif1")
        self.p2 = make_profile("notif2@gmail.com", Gender.FEMALE, "Notif2")

    def test_message_notification_cooldown(self):
        from core.controllers import notification_controller
        from core.models import Match, Notification
        from core.models.choices import MatchStatus, NotificationType
        from unittest.mock import patch

        match = Match.objects.create(user_1=self.p1, user_2=self.p2, status=MatchStatus.ACTIVE)
        with patch("core.controllers.notification_controller._dispatch_push") as push_mock:
            notification_controller.notify_new_message(
                sender=self.p1,
                match=match,
                preview="Premier message",
            )
            notification_controller.notify_new_message(
                sender=self.p1,
                match=match,
                preview="Deuxième message rapide",
            )
        self.assertEqual(
            Notification.objects.filter(
                user=self.p2,
                type=NotificationType.NEW_MESSAGE,
                related_match=match,
            ).count(),
            2,
        )
        self.assertEqual(push_mock.call_count, 1)

    def test_notification_payload_includes_kind_and_photo(self):
        from core.controllers import notification_controller
        from core.models import Match
        from core.models.choices import MatchStatus

        match = Match.objects.create(user_1=self.p1, user_2=self.p2, status=MatchStatus.ACTIVE)
        notif = notification_controller.notify_like(
            recipient=self.p2, sender=self.p1, is_super_like=True
        )
        payload = notification_controller._notification_payload(notif)
        self.assertEqual(payload["kind"], "super_like")
        self.assertEqual(payload["related_user_id"], str(self.p1.id))
        self.assertEqual(payload["related_user_name"], "Notif1")
        self.assertIn("unread_messages", payload)
        self.assertTrue(payload["url"])
        self.assertTrue(payload["url"].startswith("/"))

        msg_notif = notification_controller.notify_new_message(
            sender=self.p1, match=match, preview="Salut"
        )
        msg_payload = notification_controller._notification_payload(msg_notif)
        self.assertEqual(msg_payload["kind"], "new_message")
        self.assertEqual(msg_payload["url"], f"/discussions/{self.p1.id}/")
        self.assertGreaterEqual(msg_payload["unread_messages"], 0)

    def test_push_test_requires_device(self):
        from core.models import PushDevice

        self.client = Client(enforce_csrf_checks=False)
        user = self.p1.user
        user.set_password("Ludvanne12")
        user.save()
        self.client.login(username=user.username, password="Ludvanne12")
        profile_controller.activate_push_preferences(self.p1)

        r = self.client.post("/api/push/test/")
        self.assertEqual(r.status_code, 400)

        PushDevice.objects.create(profile=self.p1, token="test-token-abc", platform="web")
        with patch("core.controllers.push_controller.send_for_notification") as mocked:
            mocked.return_value = {"sent": 1, "failed": 0, "skipped": 0}
            r = self.client.post("/api/push/test/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"]        )


@override_settings(FREEMIUM_LIMITS_ENABLED=True)
class BlockMessagingTests(TestCase):
    def setUp(self):
        from core.models import Match
        from core.models.choices import MatchStatus

        site_settings_controller.seed_defaults()
        site_settings_controller.set_value("free_messages_limit", 10)
        self.p1 = make_profile("block1@gmail.com", Gender.MALE, "Block1")
        self.p2 = make_profile("block2@gmail.com", Gender.FEMALE, "Block2")
        for p in (self.p1, self.p2):
            p.onboarding_completed = True
            p.save(update_fields=["onboarding_completed", "updated_at"])
        Match.objects.create(user_1=self.p1, user_2=self.p2, status=MatchStatus.ACTIVE)

    def test_block_prevents_messaging(self):
        from core.controllers import moderation_controller

        moderation_controller.block_user(self.p1, self.p2.id)
        ok, msg, _ = message_controller.send_text(self.p1, self.p2.id, "Salut")
        self.assertFalse(ok)
        self.assertIn("bloqué", msg.lower())

    def test_block_api_and_inbox_flag(self):
        from core.models import BlockedUser

        self.client = Client(enforce_csrf_checks=False)
        user = self.p1.user
        user.set_password("Ludvanne12")
        user.save()
        self.client.login(username=user.username, password="Ludvanne12")
        r = self.client.post(
            "/api/blocked-users/",
            data='{"blocked_id": "%s"}' % self.p2.id,
            content_type="application/json",
        )
        self.assertTrue(r.json()["ok"])
        self.assertTrue(BlockedUser.objects.filter(blocker=self.p1, blocked=self.p2).exists())
        convos = message_controller.list_conversations(self.p1)
        match = next(c for c in convos if c["partner"].id == self.p2.id)
        self.assertTrue(match["blocked_by_me"])

    def test_delete_own_message(self):
        from core.models import Message

        ok, _, msg = message_controller.send_text(self.p1, self.p2.id, "À supprimer")
        self.assertTrue(ok)
        self.assertIsNotNone(msg)

        ok_del, text = message_controller.delete_message(self.p1, msg.id)
        self.assertTrue(ok_del)
        self.assertFalse(Message.objects.filter(pk=msg.id).exists())

        ok_other, text_other = message_controller.delete_message(self.p2, msg.id)
        self.assertFalse(ok_other)

        self.client = Client(enforce_csrf_checks=False)
        user = self.p1.user
        user.set_password("Ludvanne12")
        user.save()
        self.client.login(username=user.username, password="Ludvanne12")
        ok2, _, msg2 = message_controller.send_text(self.p1, self.p2.id, "Via API")
        r = self.client.delete("/api/messages/%s/" % msg2.id)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertFalse(Message.objects.filter(pk=msg2.id).exists())

    def test_read_receipts_after_partner_opens_thread(self):
        ok, _, msg = message_controller.send_text(self.p1, self.p2.id, "Hello")
        self.assertTrue(ok)
        self.assertFalse(msg.is_read)

        receipts_before = message_controller.read_receipts(self.p1, self.p2.id)
        self.assertEqual(receipts_before, [])

        message_controller.mark_read(self.p2, self.p1.id)
        msg.refresh_from_db()
        self.assertTrue(msg.is_read)

        receipts_after = message_controller.read_receipts(self.p1, self.p2.id)
        self.assertEqual(receipts_after, [str(msg.id)])

        self.client = Client(enforce_csrf_checks=False)
        user = self.p1.user
        user.set_password("Ludvanne12")
        user.save()
        self.client.login(username=user.username, password="Ludvanne12")
        r = self.client.get("/api/messages/read-receipts/?partner_id=%s" % self.p2.id)
        self.assertEqual(r.status_code, 200)
        self.assertIn(str(msg.id), r.json()["read_ids"])

    def test_mark_read_api_works_when_sender_at_free_limit(self):
        """Un homme à la limite peut toujours marquer les messages reçus comme lus."""
        from core.models import Match
        from core.models.choices import MatchStatus

        site_settings_controller.set_value("free_messages_limit", 1)
        limited = make_profile("limited@gmail.com", Gender.MALE, "Limited")
        partner = make_profile("partner@gmail.com", Gender.FEMALE, "Partner")
        for p in (limited, partner):
            p.onboarding_completed = True
            p.save(update_fields=["onboarding_completed", "updated_at"])
        Match.objects.create(user_1=limited, user_2=partner, status=MatchStatus.ACTIVE)

        ok_send, _, _ = message_controller.send_text(limited, partner.id, "Premier")
        self.assertTrue(ok_send)
        ok_blocked, msg_blocked, _ = message_controller.send_text(limited, partner.id, "Deuxième")
        self.assertFalse(ok_blocked)
        self.assertIn("limite", msg_blocked.lower())

        ok_in, _, incoming = message_controller.send_text(partner, limited.id, "Réponse")
        self.assertTrue(ok_in)
        self.assertFalse(incoming.is_read)

        self.client = Client(enforce_csrf_checks=False)
        user = limited.user
        user.set_password("Ludvanne12")
        user.save()
        self.client.login(username=user.username, password="Ludvanne12")
        r = self.client.post(
            "/api/messages/mark-read/",
            data='{"partner_id": "%s"}' % partner.id,
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()["ok"])
        self.assertGreaterEqual(r.json()["marked"], 1)

        incoming.refresh_from_db()
        self.assertTrue(incoming.is_read)
        receipts = message_controller.read_receipts(partner, limited.id)
        self.assertIn(str(incoming.id), receipts)

    def test_restricted_recipient_gets_message_notification(self):
        """Un homme à la limite reçoit toujours la notif quand le partenaire écrit."""
        from core.models import Match, Notification
        from core.models.choices import MatchStatus, NotificationType

        site_settings_controller.set_value("free_messages_limit", 1)
        limited = make_profile("limited2@gmail.com", Gender.MALE, "Limited2")
        partner = make_profile("partner2@gmail.com", Gender.FEMALE, "Partner2")
        for p in (limited, partner):
            p.onboarding_completed = True
            p.save(update_fields=["onboarding_completed", "updated_at"])
        Match.objects.create(user_1=limited, user_2=partner, status=MatchStatus.ACTIVE)

        message_controller.send_text(limited, partner.id, "Premier")
        ok, msg, _ = message_controller.send_text(limited, partner.id, "Deuxième")
        self.assertFalse(ok)

        ok_in, _, _ = message_controller.send_text(partner, limited.id, "Réponse partenaire")
        self.assertTrue(ok_in)
        self.assertTrue(
            Notification.objects.filter(
                user=limited,
                type=NotificationType.NEW_MESSAGE,
                related_user=partner,
            ).exists()
        )

    def test_inbox_feed_api(self):
        message_controller.send_text(self.p1, self.p2.id, "Salut inbox")

        self.client = Client(enforce_csrf_checks=False)
        user = self.p2.user
        user.set_password("Ludvanne12")
        user.save()
        self.client.login(username=user.username, password="Ludvanne12")
        r = self.client.get("/api/messages/inbox/")
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["partner_id"], str(self.p1.id))
        self.assertGreaterEqual(data["total_unread"], 1)


class CompatibilityScoreTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.viewer = make_profile("compat-viewer@test.com", Gender.MALE, "Viewer")
        self.viewer.relationship_intent = "mariage"
        self.viewer.religion = "musulmane"
        self.viewer.interests = ["voyage", "foi", "cuisine"]
        self.viewer.personality_traits = ["bienveillant", "fidele"]
        self.viewer.life_values = ["famille", "foi", "sincerite"]
        self.viewer.looking_for = '["serieux", "familial", "foi"]'
        self.viewer.save()

        self.candidate = make_profile("compat-cand@test.com", Gender.FEMALE, "Candidate")
        self.candidate.relationship_intent = "mariage"
        self.candidate.religion = "musulmane"
        self.candidate.interests = ["voyage", "foi", "lecture"]
        self.candidate.personality_traits = ["bienveillant", "spirituel"]
        self.candidate.life_values = ["famille", "foi", "respect"]
        self.candidate.looking_for = '["serieux", "familial", "bienveillant"]'
        self.candidate.city = "Dakar"
        self.candidate.photo_url = "https://example.com/photo.jpg"
        self.candidate.save()

    def test_high_overlap_scores_high(self):
        from core.controllers.matching_controller import compatibility_percent

        score = compatibility_percent(self.viewer, self.candidate)
        self.assertGreaterEqual(score, 75)
        self.assertLessEqual(score, 99)

    def test_low_overlap_scores_lower(self):
        from core.controllers.matching_controller import compatibility_percent

        self.candidate.relationship_intent = "a_preciser"
        self.candidate.religion = "chretienne"
        self.candidate.interests = ["jeux"]
        self.candidate.personality_traits = ["drole"]
        self.candidate.life_values = ["travail"]
        self.candidate.city = "Paris"
        self.candidate.save()

        score = compatibility_percent(self.viewer, self.candidate)
        self.assertLess(score, 75)

    def test_api_compatibility_endpoint(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=False)
        user = self.viewer.user
        user.set_password("Ludvanne12")
        user.save()
        client.login(username=user.username, password="Ludvanne12")
        r = client.get("/api/compatibility/%s/" % self.candidate.id)
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertGreaterEqual(data["compatibility"], 52)
        self.assertLessEqual(data["compatibility"], 99)

    def test_guest_uses_solo_score(self):
        from core.controllers.matching_controller import compatibility_percent

        score = compatibility_percent(None, self.candidate)
        self.assertGreaterEqual(score, 58)
        self.assertLessEqual(score, 88)


class PagesSmokeTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.client = Client()

    def test_public_pages(self):
        for url in ["/", "/qui-suis-je/", "/coaching/", "/cgv/", "/mentions-legales/", "/politique-de-confidentialite/", "/connexion/", "/inscription/"]:
            resp = self.client.get(url)
            self.assertIn(resp.status_code, (200, 302), url)

    def test_api_health(self):
        resp = self.client.get("/api/health/")
        self.assertEqual(resp.status_code, 200)

    def test_firebase_sw_not_redirected_during_signup(self):
        profile = make_profile("sw@test.com", Gender.MALE, "SW")
        profile.onboarding_completed = False
        profile.registration_status = RegistrationStatus.PENDING
        profile.save(update_fields=["onboarding_completed", "registration_status", "updated_at"])
        self.client.force_login(profile.user)
        resp = self.client.get("/firebase-messaging-sw.js")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/javascript", resp["Content-Type"])
        self.assertNotIn("/connexion/", resp.get("Location", ""))


@override_settings(FREEMIUM_LIMITS_ENABLED=True)
class FreemiumQuotaTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        site_settings_controller.set_value("free_messages_limit", 5)
        site_settings_controller.set_value("free_swipes_per_day", 20)
        site_settings_controller.set_value("free_likes_per_day", 20)
        site_settings_controller.set_value("free_likes_visible", 2)
        site_settings_controller.set_value("free_history_visible", 5)
        self.client = Client(enforce_csrf_checks=False)
        self.free = make_profile("free@test.com", Gender.MALE, "Libre")
        self.p2 = make_profile("quota2@test.com", Gender.FEMALE, "Awa")
        self.p3 = make_profile("quota3@test.com", Gender.FEMALE, "Fatou")
        for profile in (self.free, self.p2, self.p3):
            profile.photo_url = "https://example.com/photo.webp"
            profile.onboarding_completed = True
            profile.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])

    def _match(self, a, b):
        swipe_controller.record_swipe(a, b.id, "like")
        swipe_controller.record_swipe(b, a.id, "like")

    def test_messages_shared_across_conversations(self):
        self._match(self.free, self.p2)
        self._match(self.free, self.p3)
        ok1, _, _ = message_controller.send_text(self.free, self.p2.id, "Un")
        ok2, _, _ = message_controller.send_text(self.free, self.p2.id, "Deux")
        ok3, _, _ = message_controller.send_text(self.free, self.p3.id, "Trois")
        ok4, _, _ = message_controller.send_text(self.free, self.p3.id, "Quatre")
        ok5, _, _ = message_controller.send_text(self.free, self.p2.id, "Cinq")
        ok6, msg, _ = message_controller.send_text(self.free, self.p3.id, "Six")
        self.assertTrue(ok1 and ok2 and ok3 and ok4 and ok5)
        self.assertFalse(ok6)
        self.assertIn("5 messages", msg)

    def test_daily_swipe_and_like_limits(self):
        site_settings_controller.set_value("free_likes_per_day", 1)
        first = swipe_controller.record_swipe(self.free, self.p2.id, "pass")
        self.assertTrue(first["ok"])
        second_pass = swipe_controller.record_swipe(self.free, self.p3.id, "pass")
        self.assertTrue(second_pass["ok"])

        like1 = swipe_controller.record_swipe(self.free, self.p2.id, "like")
        self.assertTrue(like1["ok"])
        extra = make_profile("quota4@test.com", Gender.FEMALE, "Sokhna")
        like2 = swipe_controller.record_swipe(self.free, extra.id, "like")
        self.assertFalse(like2["ok"])
        self.assertEqual(like2.get("code"), "like_limit")

    def test_historique_partial_for_freemium_male(self):
        for i in range(6):
            other = make_profile(f"hist{i}@test.com", Gender.FEMALE, f"H{i}")
            other.photo_url = "https://example.com/p.webp"
            other.onboarding_completed = True
            other.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
            swipe_controller.record_swipe(self.free, other.id, "like")
        self.client.force_login(self.free.user)
        page = self.client.get("/historique/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "history__grid")
        self.assertContains(page, "plan supérieur")

    def test_female_unlimited_freemium(self):
        from core.controllers import quota_controller

        femme = make_profile("femme@test.com", Gender.FEMALE, "Awa")
        self.assertFalse(quota_controller.is_freemium(femme))

    def test_likes_page_shows_two_profiles(self):
        p4 = make_profile("quota4@test.com", Gender.FEMALE, "Sokhna")
        p4.photo_url = "https://example.com/photo.webp"
        p4.onboarding_completed = True
        p4.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
        swipe_controller.record_swipe(self.p2, self.free.id, "like")
        swipe_controller.record_swipe(self.p3, self.free.id, "like")
        swipe_controller.record_swipe(p4, self.free.id, "like")
        self.client.force_login(self.free.user)
        page = self.client.get("/likes/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "is-locked")
        html = page.content.decode()
        visible_names = sum(1 for name in ("Awa", "Fatou", "Sokhna") if name in html)
        self.assertGreaterEqual(visible_names, 2)

    def test_disabled_message_quota_is_unlimited(self):
        from core.controllers import quota_controller

        site_settings_controller.set_value("quota_messages_enabled", False)
        site_settings_controller.set_value("free_messages_limit", 1)
        self._match(self.free, self.p2)
        ok1, _, _ = message_controller.send_text(self.free, self.p2.id, "Un")
        ok2, _, _ = message_controller.send_text(self.free, self.p2.id, "Deux")
        self.assertTrue(ok1 and ok2)
        self.assertIsNone(quota_controller.messages_remaining(self.free))

    def test_likes_received_cap_can_be_disabled(self):
        site_settings_controller.set_value("quota_likes_visible_enabled", False)
        extra = make_profile("lockvis@test.com", Gender.FEMALE, "Sokhna")
        extra.photo_url = "https://example.com/photo.webp"
        extra.onboarding_completed = True
        extra.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
        swipe_controller.record_swipe(self.p2, self.free.id, "like")
        swipe_controller.record_swipe(self.p3, self.free.id, "like")
        swipe_controller.record_swipe(extra, self.free.id, "like")
        self.client.force_login(self.free.user)
        page = self.client.get("/likes/")
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "is-locked")

    def test_quota_period_month_and_save_from_post(self):
        from core.controllers import quota_controller

        saved = quota_controller.save_limits_from_post(
            {
                "quota_period": "month",
                "free_messages_limit": "8",
                "free_likes_per_day": "12",
                "free_swipes_per_day": "15",
                "free_likes_visible": "3",
                "free_history_visible": "6",
                "quota_messages_enabled": "on",
                "quota_likes_enabled": "on",
                "quota_swipes_enabled": "on",
                "quota_likes_visible_enabled": "on",
                "quota_history_visible_enabled": "on",
                "freemium_limits_enabled": "on",
            }
        )
        self.assertEqual(saved["period"], "month")
        self.assertEqual(saved["messages_limit"], 8)
        self.assertEqual(saved["likes_limit"], 12)
        self.assertEqual(saved["swipes_limit"], 15)
        self.assertEqual(saved["likes_visible"], 3)
        self.assertTrue(saved["enabled"])
        start = quota_controller.period_start()
        self.assertEqual(start.day, 1)

    def test_subscription_entitlements(self):
        from core.controllers import subscription_controller
        from core.models.choices import SubscriptionStatus, SubscriptionTier

        self.free.subscription_tier = SubscriptionTier.PREMIUM_1M
        self.free.subscription_status = SubscriptionStatus.ACTIVE
        self.free.save(update_fields=["subscription_tier", "subscription_status", "updated_at"])
        self.assertEqual(subscription_controller.visibility_multiplier(self.free), 5)
        self.free.subscription_tier = SubscriptionTier.VIP_1M
        self.free.save(update_fields=["subscription_tier", "updated_at"])
        self.assertEqual(subscription_controller.visibility_multiplier(self.free), 10)
        self.assertTrue(subscription_controller.can_bypass_gender_filter(self.free))
        femme = make_profile("plans-femme@test.com", Gender.FEMALE, "Awa")
        ids = subscription_controller.plans_catalog_for(femme)
        self.assertEqual(ids, ["pass_femme"])
        homme_ids = subscription_controller.plans_catalog_for(self.free)
        self.assertIn("premium_1m", homme_ids)
        self.assertIn("vip_1m", homme_ids)
        self.assertNotIn("pass_femme", homme_ids)

    def test_auto_ban_after_reports(self):
        from core.controllers import moderation_controller
        from core.models.choices import ReportReason

        target = make_profile("bad@test.com", Gender.MALE, "Bad")
        r1 = make_profile("r1@test.com", Gender.FEMALE, "R1")
        r2 = make_profile("r2@test.com", Gender.FEMALE, "R2")
        for rep in (r1, r2):
            moderation_controller.create_report(
                rep,
                {
                    "reported_profile_id": str(target.id),
                    "reason": ReportReason.HARASSMENT,
                    "message": "Comportement inacceptable répété.",
                },
            )
        target.refresh_from_db()
        self.assertIsNotNone(target.banned_at)
        self.assertTrue(Profile.objects.filter(pk=target.pk).exists())


class SearchFeatureFlagsTests(TestCase):
    def test_search_bars_enabled_by_default(self):
        from core.controllers import app_config_controller

        flags = app_config_controller.feature_flags()
        self.assertTrue(flags["explorer_search_enabled"])
        self.assertTrue(flags["history_search_enabled"])
        self.assertTrue(flags["messages_search_enabled"])

    def test_admin_can_disable_search_bars(self):
        from core.controllers import app_config_controller

        app_config_controller.save_features_from_post({})
        flags = app_config_controller.feature_flags()
        self.assertFalse(flags["explorer_search_enabled"])
        self.assertFalse(flags["history_search_enabled"])
        self.assertFalse(flags["messages_search_enabled"])

        app_config_controller.save_features_from_post(
            {
                "text_messages_enabled": "on",
                "voice_messages_enabled": "on",
                "image_messages_enabled": "on",
                "explorer_search_enabled": "on",
                "history_search_enabled": "on",
                "messages_search_enabled": "on",
            }
        )
        flags = app_config_controller.feature_flags()
        self.assertTrue(flags["explorer_search_enabled"])
        self.assertTrue(flags["history_search_enabled"])
        self.assertTrue(flags["messages_search_enabled"])

    def test_explorer_renders_search_bar(self):
        profile = make_profile("searchbar@test.com", Gender.FEMALE, "Aicha")
        profile.onboarding_completed = True
        profile.save(update_fields=["onboarding_completed"])
        self.client.force_login(profile.user)
        r = self.client.get("/explorer/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "data-explorer-search")
        self.assertContains(r, "Rechercher un profil")

