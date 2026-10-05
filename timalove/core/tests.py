from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db.models import Q
from django.test import Client, TestCase, override_settings
from django.utils import timezone
from datetime import date
import json
from unittest.mock import patch

from core.controllers import (
    auth_controller,
    message_controller,
    payment_controller,
    profile_controller,
    signup_controller,
    swipe_controller,
)
from core.models import Profile
from core.models.choices import Gender, RegistrationStatus, Religion, UserRole
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
        from core.controllers import app_config_controller

        cfg = app_config_controller.get_app_config()
        cfg["guided_messages_enabled"] = False
        app_config_controller.save_app_config(cfg)
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
    def test_plan_prices_override_stale_subscription_prices(self):
        site_settings_controller.set_value(
            "subscription_prices",
            {"vip_1m": 20000, "premium_1m": 9000, "premium_10d": 6000},
        )
        prices = site_settings_controller.get("subscription_prices")
        self.assertEqual(prices["vip_1m"], 8000)
        self.assertEqual(prices["premium_1m"], 2990)
        self.assertEqual(prices["premium_10d"], 6000)
        self.assertEqual(prices["journee_amoureuse"], 1000)
        profile = make_profile("prix@test.com", Gender.MALE, "Prix")
        plans = {item["id"]: item for item in profile_controller.subscription_plans_for(profile)}
        self.assertEqual(plans["premium_1m"]["price"], 2990)
        self.assertEqual(plans["vip_1m"]["price"], 8000)
        self.assertEqual(payment_controller.price_for_tier("premium_1m"), 2990)

    def test_seed_defaults_syncs_plan_prices(self):
        site_settings_controller.set_value("subscription_prices", {"vip_1m": 20000})
        site_settings_controller.seed_defaults()
        from core.models import SiteSetting

        stored = SiteSetting.objects.get(key="subscription_prices").value
        self.assertEqual(stored["vip_1m"], 8000)
        self.assertEqual(stored["journee_amoureuse"], 1000)


class SubscriptionBadgeTests(TestCase):
    def _activate(self, profile, tier):
        from datetime import timedelta

        from django.utils import timezone

        from core.models.choices import SubscriptionStatus

        profile.subscription_tier = tier
        profile.subscription_status = SubscriptionStatus.ACTIVE
        profile.subscription_end_date = timezone.now() + timedelta(days=15)
        profile.save(update_fields=["subscription_tier", "subscription_status", "subscription_end_date", "updated_at"])

    def test_badge_premium_vip_and_pass_femme(self):
        from core.controllers import subscription_controller
        from core.models.choices import SubscriptionTier

        free = make_profile("free-badge@test.com", Gender.MALE, "Free")
        self.assertEqual(subscription_controller.badge_for(free), "")

        premium = make_profile("prem-badge@test.com", Gender.MALE, "Prem")
        self._activate(premium, SubscriptionTier.PREMIUM_1M)
        self.assertEqual(subscription_controller.badge_for(premium), "premium")

        vip = make_profile("vip-badge@test.com", Gender.MALE, "Vip")
        self._activate(vip, SubscriptionTier.VIP_1M)
        self.assertEqual(subscription_controller.badge_for(vip), "vip")

        femme = make_profile("pass-badge@test.com", Gender.FEMALE, "Pass")
        self._activate(femme, SubscriptionTier.PASS_FEMME)
        self.assertEqual(subscription_controller.badge_for(femme), "vip")


class LikesMessagingFlowTests(TestCase):
    """Like, super like, match et messagerie entre deux comptes."""

    def setUp(self):
        site_settings_controller.seed_defaults()
        site_settings_controller.set_value("free_messages_limit", 10)
        from core.controllers import app_config_controller

        cfg = app_config_controller.get_app_config()
        cfg["guided_messages_enabled"] = False
        app_config_controller.save_app_config(cfg)
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

    def test_open_conversation_after_super_like_only(self):
        """Priorité seule : ouverture de conversation autorisée."""
        from core.controllers import message_controller, swipe_controller

        result = swipe_controller.record_swipe(self.p1, self.p2.id, "super_like")
        self.assertTrue(result["ok"], result)
        self.assertTrue(result["is_super_like"])
        self.assertTrue(result["is_like"])

        ok, msg, match = message_controller.ensure_conversation(self.p1, self.p2.id)
        self.assertTrue(ok, msg)
        self.assertIsNotNone(match)

        from core.controllers import likes_controller

        self.assertTrue(likes_controller.has_liked(self.p1, self.p2.id))
        self.assertTrue(likes_controller.has_super_liked(self.p1, self.p2.id))

    def test_send_compressed_chat_image(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        from core.models import Match, Message
        from core.models.choices import ConversationStatus, MatchStatus, MessageType

        Match.objects.create(
            user_1=self.p1,
            user_2=self.p2,
            status=MatchStatus.ACTIVE,
            conversation_status=ConversationStatus.ACCEPTED,
        )
        canvas = Image.new("RGB", (1600, 900), (232, 99, 122))
        buf = BytesIO()
        canvas.save(buf, format="JPEG", quality=95)
        upload = SimpleUploadedFile("photo.jpg", buf.getvalue(), content_type="image/jpeg")

        self._login(self.u1)
        with patch("core.controllers.subscription_controller.can_send_media", return_value=True):
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


class CuratedExplorerTests(TestCase):
    """Like / super like sur le Parcours curated : enregistrement + remplacement."""

    def setUp(self):
        site_settings_controller.seed_defaults()
        self.client = Client(enforce_csrf_checks=False)
        self.viewer = make_profile("curated.viewer@gmail.com", Gender.MALE, "Karim")
        self.a = make_profile("curated.a@gmail.com", Gender.FEMALE, "Awa")
        self.b = make_profile("curated.b@gmail.com", Gender.FEMALE, "Penda")
        self.c = make_profile("curated.c@gmail.com", Gender.FEMALE, "Fatou")
        for profile in (self.viewer, self.a, self.b, self.c):
            profile.photo_url = "https://example.com/photo.webp"
            profile.onboarding_completed = True
            profile.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
        self.viewer.user.set_password("Ludvanne12")
        self.viewer.user.save()

    def test_explorer_loads_swipe_script_in_curated_mode(self):
        self.assertTrue(self.client.login(username=self.viewer.user.username, password="Ludvanne12"))
        page = self.client.get("/explorer/")
        self.assertEqual(page.status_code, 200)
        html = page.content.decode()
        self.assertIn("explorer-swipe.js", html)
        self.assertIn("explorer-curated.js", html)

    def test_explorer_card_shows_reasons_not_pass_or_star(self):
        from core.models.choices import RelationshipIntent, Religion

        self.viewer.religion = Religion.MUSULMANE
        self.viewer.relationship_intent = RelationshipIntent.MARIAGE
        self.viewer.save(update_fields=["religion", "relationship_intent", "updated_at"])
        self.a.religion = Religion.MUSULMANE
        self.a.relationship_intent = RelationshipIntent.MARIAGE
        self.a.save(update_fields=["religion", "relationship_intent", "updated_at"])
        self.assertTrue(self.client.login(username=self.viewer.user.username, password="Ludvanne12"))
        page = self.client.get("/explorer/")
        self.assertEqual(page.status_code, 200)
        html = page.content.decode()
        self.assertIn("Pourquoi ce profil", html)
        self.assertIn("Exprimer mon intérêt", html)
        self.assertNotIn("data-swipe=\"pass\"", html)
        self.assertNotIn("data-swipe=\"super_like\"", html)
        self.assertNotIn("attentions", html)

    def test_online_label_shown_on_curated_card(self):
        from core.controllers import explore_controller, presence_controller

        presence_controller.mark_socket_connected(self.a.id)
        self.assertTrue(self.client.login(username=self.viewer.user.username, password="Ludvanne12"))
        session = self.client.session
        session[explore_controller.SESSION_CURATED_IDS_KEY] = [str(self.a.id)]
        session[explore_controller.SESSION_CURATED_TARGET_KEY] = 1
        session.save()
        page = self.client.get("/explorer/")
        html = page.content.decode()
        self.assertIn("curated-card__live", html)
        self.assertIn("En ligne", html)
        self.assertIn("curated-card__online", html)

    def test_explorer_card_shows_listen_when_voice_intro(self):
        self.a.voice_intro_url = "/media/voice-intros/awa-demo.wav"
        self.a.voice_intro_duration_seconds = 8
        self.a.save(update_fields=["voice_intro_url", "voice_intro_duration_seconds", "updated_at"])
        self.assertTrue(self.client.login(username=self.viewer.user.username, password="Ludvanne12"))
        page = self.client.get("/explorer/")
        self.assertEqual(page.status_code, 200)
        html = page.content.decode()
        self.assertIn("Écouter", html)
        self.assertIn("data-voice-intro", html)
        self.assertIn("/media/voice-intros/awa-demo.wav", html)

    def test_like_then_replace_removes_liked_profile(self):
        from core.controllers import explore_controller, swipe_controller

        session = self.client.session
        session[explore_controller.SESSION_CURATED_IDS_KEY] = [str(self.a.id)]
        session[explore_controller.SESSION_CURATED_TARGET_KEY] = 1
        session.save()

        result = swipe_controller.record_swipe(self.viewer, self.a.id, "like")
        self.assertTrue(result["ok"], result)

        replacements, meta = explore_controller.consume_curated_profile(
            self.viewer, session, self.a.id
        )
        stored = [str(pk) for pk in session.get(explore_controller.SESSION_CURATED_IDS_KEY) or []]
        self.assertNotIn(str(self.a.id), stored)
        self.assertTrue(meta["replaced"])
        self.assertEqual(len(replacements), 1)
        self.assertIn(replacements[0]["id"], {str(self.b.id), str(self.c.id)})
        self.assertNotIn(str(self.a.id), {card["id"] for card in replacements})

    def test_curated_replace_endpoint_returns_new_card(self):
        self.assertTrue(self.client.login(username=self.viewer.user.username, password="Ludvanne12"))
        session = self.client.session
        from core.controllers import explore_controller

        session[explore_controller.SESSION_CURATED_IDS_KEY] = [str(self.a.id)]
        session[explore_controller.SESSION_CURATED_TARGET_KEY] = 1
        session.save()
        swipe = self.client.post(
            "/api/swipes/",
            data='{"swiped_id": "%s", "action": "super_like"}' % self.a.id,
            content_type="application/json",
        )
        self.assertEqual(swipe.status_code, 200)
        self.assertTrue(swipe.json()["ok"])

        replaced = self.client.post(
            "/explorer/curated-replace/",
            data='{"profile_id": "%s"}' % self.a.id,
            content_type="application/json",
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(replaced.status_code, 200)
        html = replaced.content.decode()
        self.assertNotIn(str(self.a.id), html)
        self.assertTrue(str(self.b.id) in html or str(self.c.id) in html)

    def test_online_dot_only_for_live_presence(self):
        from datetime import timedelta

        from core.controllers import explore_controller, presence_controller

        self.a.is_online = True
        self.a.last_active_at = timezone.now() - timedelta(days=2)
        self.a.save(update_fields=["is_online", "last_active_at"])
        self.assertFalse(presence_controller.is_present(self.a))
        stale = explore_controller.online_status_for_ids([self.a.id])
        self.assertFalse(stale[str(self.a.id)])

        became = presence_controller.mark_socket_connected(self.a.id)
        self.assertTrue(became)
        self.a.refresh_from_db()
        self.assertTrue(presence_controller.is_present(self.a))
        live = explore_controller.online_status_for_ids([self.a.id])
        self.assertTrue(live[str(self.a.id)])

        left = presence_controller.mark_socket_disconnected(self.a.id)
        self.assertTrue(left)
        self.a.refresh_from_db()
        self.assertFalse(self.a.is_online)
        self.assertFalse(presence_controller.is_present(self.a))

        self.assertTrue(self.client.login(username=self.viewer.user.username, password="Ludvanne12"))
        api = self.client.get("/api/profiles/online/?ids=%s" % self.a.id)
        self.assertEqual(api.status_code, 200)
        self.assertFalse(api.json()["online"].get(str(self.a.id)))


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
        from core.controllers import app_config_controller

        site_settings_controller.seed_defaults()
        cfg = app_config_controller.get_app_config()
        cfg["guided_messages_enabled"] = False
        app_config_controller.save_app_config(cfg)
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

    def test_message_created_at_is_utc_iso(self):
        ok, _, msg = message_controller.send_text(self.p1, self.p2.id, "Heure test")
        self.assertTrue(ok)
        item = message_controller._serialize_message(msg, self.p1)
        self.assertIn("created_at", item)
        self.assertTrue(item["created_at"].endswith("Z"))
        self.assertNotIn("time", item)

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

    def test_api_compatibility_requires_login(self):
        from django.test import Client

        client = Client(enforce_csrf_checks=False)
        r = client.get("/api/compatibility/%s/" % self.candidate.id)
        self.assertEqual(r.status_code, 401)
        self.assertFalse(r.json()["ok"])

    def test_origin_country_boosts_score(self):
        from core.controllers.matching_controller import compatibility_percent

        self.viewer.country = "Sénégal"
        self.viewer.save()
        self.candidate.country = "Sénégal"
        self.candidate.save()
        with_origin = compatibility_percent(self.viewer, self.candidate)
        self.candidate.country = "France"
        self.candidate.save()
        without_origin = compatibility_percent(self.viewer, self.candidate)
        self.assertGreater(with_origin, without_origin)

    def test_origin_country_matches_without_accents(self):
        from core.controllers.matching_controller import compatibility_percent

        self.viewer.country = "Sénégal"
        self.viewer.save()
        self.candidate.country = "senegal"
        self.candidate.save()
        score = compatibility_percent(self.viewer, self.candidate)
        self.assertGreaterEqual(score, 70)

    def test_sparse_viewer_still_gets_varied_scores(self):
        from core.controllers.matching_controller import compatibility_percent

        self.viewer.interests = []
        self.viewer.life_values = []
        self.viewer.personality_traits = []
        self.viewer.looking_for = ""
        self.viewer.religion = "chretienne"
        self.viewer.save()

        self.candidate.relationship_intent = "mariage"
        self.candidate.religion = "musulmane"
        self.candidate.interests = []
        self.candidate.save()
        low = compatibility_percent(self.viewer, self.candidate)

        self.candidate.religion = "chretienne"
        self.candidate.interests = ["voyage", "foi", "lecture"]
        self.candidate.save()
        high = compatibility_percent(self.viewer, self.candidate)

        self.assertGreater(high, low)
        self.assertGreaterEqual(low, 52)
        self.assertLessEqual(high, 99)

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
        for url in [
            "/",
            "/qui-suis-je/",
            "/coaching/",
            "/cgv/",
            "/conditions-d-utilisation/",
            "/mentions-legales/",
            "/politique-de-confidentialite/",
            "/suppression-de-compte/",
            "/securite-des-enfants/",
            "/connexion/",
            "/inscription/",
        ]:
            resp = self.client.get(url)
            self.assertIn(resp.status_code, (200, 302), url)

    def test_connexion_shows_cgu_consent(self):
        resp = self.client.get("/connexion/")
        self.assertEqual(resp.status_code, 200)
        body = resp.content.decode("utf-8")
        self.assertIn("Conditions d'utilisation", body)
        self.assertIn("/conditions-d-utilisation/", body)
        self.assertIn("Politique de confidentialité", body)

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
        from core.controllers import app_config_controller

        cfg = app_config_controller.get_app_config()
        cfg["guided_messages_enabled"] = False
        app_config_controller.save_app_config(cfg)
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

    def test_daily_swipe_limit_blocks_new_profiles(self):
        site_settings_controller.set_value("free_swipes_per_day", 2)
        site_settings_controller.set_value("free_likes_per_day", 20)
        p4 = make_profile("swipe4@test.com", Gender.FEMALE, "Mariama")
        p4.photo_url = "https://example.com/photo.webp"
        p4.onboarding_completed = True
        p4.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])

        self.assertTrue(swipe_controller.record_swipe(self.free, self.p2.id, "pass")["ok"])
        self.assertTrue(swipe_controller.record_swipe(self.free, self.p3.id, "pass")["ok"])
        blocked = swipe_controller.record_swipe(self.free, p4.id, "pass")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked.get("code"), "swipe_limit")

    def test_freemium_active_when_rows_enabled_without_master_switch(self):
        from core.controllers import app_config_controller, quota_controller

        cfg = app_config_controller.get_app_config()
        cfg["freemium_limits_enabled"] = False
        app_config_controller.save_app_config(cfg)
        site_settings_controller.set_value("quota_messages_enabled", True)
        site_settings_controller.set_value("free_messages_limit", 1)
        self._match(self.free, self.p2)

        self.assertTrue(app_config_controller.freemium_enabled())
        self.assertTrue(quota_controller.is_freemium(self.free))
        ok1, _, _ = message_controller.send_text(self.free, self.p2.id, "Un")
        ok2, msg, _ = message_controller.send_text(self.free, self.p2.id, "Deux")
        self.assertTrue(ok1)
        self.assertFalse(ok2)
        self.assertIn("limite", msg.lower())

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
        self.assertContains(page, "data-subscription-upgrade")
        self.assertContains(page, "Voir plus")

    def test_female_unlimited_freemium(self):
        from core.controllers import quota_controller

        femme = make_profile("femme@test.com", Gender.FEMALE, "Awa")
        self.assertFalse(quota_controller.is_freemium(femme))

    @override_settings(QUOTA_EXEMPT_EMAILS=["gooteste@gmail.com"])
    def test_store_reviewer_exempt_from_all_quotas(self):
        from core.controllers import quota_controller

        reviewer = make_profile("gooteste@gmail.com", Gender.MALE, "StoreTest")
        reviewer.photo_url = "https://example.com/photo.webp"
        reviewer.onboarding_completed = True
        reviewer.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
        self.assertTrue(quota_controller.is_quota_exempt(reviewer))
        self.assertFalse(quota_controller.is_freemium(reviewer))
        self.assertFalse(quota_controller.is_male_freemium(reviewer))
        self.assertIsNone(quota_controller.messages_remaining(reviewer))
        self.assertIsNone(quota_controller.history_limit_for(reviewer))
        self.assertIsNone(quota_controller.likes_visible_cap(reviewer))
        self._match(reviewer, self.p2)
        for i in range(8):
            ok, msg, _ = message_controller.send_text(reviewer, self.p2.id, f"Test {i}")
            self.assertTrue(ok, msg)
        ok_swipe, _, code = quota_controller.check_swipe(reviewer, self.p3.id, "like")
        self.assertTrue(ok_swipe)
        self.assertEqual(code, "")

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
        self.assertFalse(subscription_controller.can_bypass_gender_filter(self.free))
        femme = make_profile("plans-femme@test.com", Gender.FEMALE, "Awa")
        ids = subscription_controller.plans_catalog_for(femme)
        self.assertEqual(ids, ["pass_femme"])
        homme_ids = subscription_controller.plans_catalog_for(self.free)
        self.assertIn("premium_1m", homme_ids)
        self.assertIn("vip_1m", homme_ids)
        self.assertNotIn("pass_femme", homme_ids)

    def test_freemium_male_conversation_cap_blocks_new_open(self):
        from core.controllers import message_controller, swipe_controller

        partners = [self.p2, self.p3]
        for i in range(3, 8):
            partners.append(make_profile(f"conv{i}@test.com", Gender.FEMALE, f"P{i}"))
        for partner in partners[:5]:
            partner.photo_url = "https://example.com/photo.webp"
            partner.onboarding_completed = True
            partner.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
            result = swipe_controller.record_swipe(self.free, partner.id, "like")
            self.assertTrue(result["ok"], result)
            self.assertIsNotNone(result.get("match_id"))

        extra = partners[5]
        extra.photo_url = "https://example.com/photo.webp"
        extra.onboarding_completed = True
        extra.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
        swipe_controller.record_swipe(self.free, extra.id, "like")
        self.client.force_login(self.free.user)
        blocked = self.client.post(
            "/api/messages/open/",
            data='{"partner_id": "%s"}' % extra.id,
            content_type="application/json",
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertFalse(blocked.json()["ok"])
        self.assertEqual(blocked.json()["code"], message_controller.CONVERSATION_LIMIT_CODE)

    def test_premium_male_no_conversation_cap(self):
        from core.controllers import message_controller, swipe_controller
        from core.models.choices import SubscriptionStatus, SubscriptionTier

        self.free.subscription_tier = SubscriptionTier.PREMIUM_1M
        self.free.subscription_status = SubscriptionStatus.ACTIVE
        self.free.save(update_fields=["subscription_tier", "subscription_status", "updated_at"])
        partners = [self.p2, self.p3]
        for i in range(3, 8):
            partners.append(make_profile(f"prem{i}@test.com", Gender.FEMALE, f"Q{i}"))
        for partner in partners[:6]:
            partner.photo_url = "https://example.com/photo.webp"
            partner.onboarding_completed = True
            partner.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
            swipe_controller.record_swipe(self.free, partner.id, "like")
            ok, msg, _ = message_controller.ensure_conversation(self.free, partner.id)
            self.assertTrue(ok, msg)

    def test_thread_shows_subscription_modal_when_message_limit_reached(self):
        from core.controllers import app_config_controller

        cfg = app_config_controller.get_app_config()
        cfg["guided_messages_enabled"] = False
        app_config_controller.save_app_config(cfg)
        site_settings_controller.set_value("free_messages_limit", 1)
        self._match(self.free, self.p2)
        self._match(self.free, self.p3)
        ok, msg, _ = message_controller.send_text(self.free, self.p2.id, "Premier")
        self.assertTrue(ok, msg)
        self.client.force_login(self.free.user)

        inbox = self.client.get("/messages/")
        self.assertEqual(inbox.status_code, 200)
        self.assertContains(inbox, "settings-modal-subscription")

        other = self.client.get(f"/discussions/{self.p3.id}/")
        self.assertEqual(other.status_code, 200)
        self.assertContains(other, "settings-modal-subscription")
        self.assertContains(other, "subscription-modal.js")
        self.assertContains(other, 'data-msg-input')
        self.assertContains(other, "Écrire un message")
        self.assertNotContains(other, "msg__composer--disabled")
        self.assertNotContains(other, 'data-quota-locked="1"')

        blocked = self.client.post(
            "/api/messages/",
            data='{"partner_id": "%s", "content": "Encore"}' % self.p3.id,
            content_type="application/json",
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertFalse(blocked.json()["ok"])
        self.assertEqual(blocked.json()["code"], "message_limit")

    def test_api_like_limit_returns_code(self):
        site_settings_controller.set_value("free_likes_per_day", 1)
        self.client.force_login(self.free.user)
        first = self.client.post(
            "/api/swipes/",
            data='{"swiped_id": "%s", "action": "like"}' % self.p2.id,
            content_type="application/json",
        )
        self.assertEqual(first.status_code, 200)
        self.assertTrue(first.json()["ok"])
        extra = make_profile("likeapi@test.com", Gender.FEMALE, "Khadija")
        extra.photo_url = "https://example.com/photo.webp"
        extra.onboarding_completed = True
        extra.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
        blocked = self.client.post(
            "/api/swipes/",
            data='{"swiped_id": "%s", "action": "super_like"}' % extra.id,
            content_type="application/json",
        )
        self.assertEqual(blocked.status_code, 400)
        self.assertFalse(blocked.json()["ok"])
        self.assertEqual(blocked.json()["code"], "like_limit")

    def test_prod_aligned_two_messages_ten_likes_per_month(self):
        """Aligné prod : 2 messages / 10 likes (like + super like) par mois."""
        from core.controllers import app_config_controller

        cfg = app_config_controller.get_app_config()
        cfg["guided_messages_enabled"] = False
        app_config_controller.save_app_config(cfg)
        site_settings_controller.set_value("free_messages_limit", 2)
        site_settings_controller.set_value("free_likes_per_day", 10)
        site_settings_controller.set_value("quota_period", "month")
        self._match(self.free, self.p2)
        self._match(self.free, self.p3)
        ok1, _, _ = message_controller.send_text(self.free, self.p2.id, "A")
        ok2, _, _ = message_controller.send_text(self.free, self.p3.id, "B")
        ok3, msg, _ = message_controller.send_text(self.free, self.p2.id, "C")
        self.assertTrue(ok1 and ok2)
        self.assertFalse(ok3)
        self.assertIn("2 messages", msg)

        targets = []
        for i in range(11):
            p = make_profile(f"likeprod{i}@test.com", Gender.FEMALE, f"L{i}")
            p.photo_url = "https://example.com/photo.webp"
            p.onboarding_completed = True
            p.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
            targets.append(p)
        for p in targets[:8]:
            r = swipe_controller.record_swipe(self.free, p.id, "like")
            self.assertTrue(r["ok"], r)
        blocked = swipe_controller.record_swipe(self.free, targets[8].id, "super_like")
        self.assertFalse(blocked["ok"])
        self.assertEqual(blocked.get("code"), "like_limit")

    def test_historique_like_blocked_at_quota_returns_htmx_trigger(self):
        site_settings_controller.set_value("free_likes_per_day", 1)
        p4 = make_profile("histblock@test.com", Gender.FEMALE, "Bloc")
        p4.photo_url = "https://example.com/photo.webp"
        p4.onboarding_completed = True
        p4.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])
        self.assertTrue(swipe_controller.record_swipe(self.free, self.p2.id, "like")["ok"])
        self.client.force_login(self.free.user)
        resp = self.client.post(
            f"/historique/{p4.id}/like/",
            HTTP_HX_REQUEST="true",
        )
        self.assertEqual(resp.status_code, 403)
        trigger = json.loads(resp["HX-Trigger"])
        self.assertIn("timalove-quota", trigger)
        self.assertEqual(trigger["timalove-quota"]["code"], "like_limit")

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
        self.assertTrue(flags["explorer_curated_mode"])
        self.assertFalse(flags["explorer_search_enabled"])
        self.assertFalse(flags["history_search_enabled"])
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
        self.assertFalse(flags["explorer_search_enabled"])
        self.assertFalse(flags["history_search_enabled"])
        self.assertTrue(flags["messages_search_enabled"])

    def test_explorer_hides_search_and_pass_in_curated_mode(self):
        profile = make_profile("searchbar@test.com", Gender.FEMALE, "Aicha")
        profile.onboarding_completed = True
        profile.save(update_fields=["onboarding_completed"])
        self.client.force_login(profile.user)
        r = self.client.get("/explorer/", HTTP_USER_AGENT="Mozilla/5.0")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "curated-list")
        self.assertNotContains(r, "data-explorer-search")
        self.assertNotContains(r, "Passer ce profil")


class LoginRedirectTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.member = make_profile("login.redirect@test.com", Gender.MALE, "Login")
        self.member.onboarding_completed = True
        self.member.save(update_fields=["onboarding_completed"])

    def test_decouvrir_redirects_to_explorer(self):
        self.client.force_login(self.member.user)
        resp = self.client.get("/decouvrir/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/explorer/", resp.url)

    def test_login_with_legacy_next_decouvrir_goes_to_explorer(self):
        resp = self.client.post(
            "/connexion/",
            {
                "email": "login.redirect@test.com",
                "password": "pass12345",
                "login_mode": "email",
                "next": "/decouvrir/",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/explorer/", resp.url)
        self.assertNotIn("/decouvrir/", resp.url)

    def test_guest_decouvrir_login_next_is_explorer(self):
        resp = self.client.get("/decouvrir/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/connexion/", resp.url)
        self.assertIn("/explorer/", resp.url)
        self.assertNotIn("/decouvrir/", resp.url)


def make_staff(email: str, role: str, name: str = "Staff"):
    user = User.objects.create_user(
        username=email,
        email=email,
        password="StaffPass123!",
        is_staff=True,
        is_superuser=role == UserRole.SUPER_ADMIN,
    )
    return Profile.objects.create(
        user=user,
        first_name=name,
        last_name="TimaLove",
        email=email,
        date_of_birth=date(1990, 1, 1),
        gender=Gender.MALE,
        city="Dakar",
        registration_status=RegistrationStatus.APPROVED,
        role=role,
        is_verified=True,
        onboarding_completed=True,
    )


class AdminRbacAccessTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        site_settings_controller.set_value("admin_security", {"require_2fa": False})
        self.super = make_staff("super.rbac@test.com", UserRole.SUPER_ADMIN, "Super")
        self.admin = make_staff("admin.rbac@test.com", UserRole.ADMIN, "Admin")
        self.mod = make_staff("mod.rbac@test.com", UserRole.MODERATOR, "Mod")

    def _assert_access(self, profile, url: str, allowed: bool):
        client = Client()
        client.force_login(profile.user)
        resp = client.get(url)
        if allowed:
            self.assertEqual(resp.status_code, 200, f"{profile.role} devrait accéder à {url}")
        else:
            self.assertEqual(resp.status_code, 302, f"{profile.role} ne devrait pas accéder à {url}")
            self.assertIn("/espace-prive/dashboard/", resp.url)

    def test_super_admin_all_sections(self):
        for url in [
            "/espace-prive/dashboard/",
            "/espace-prive/membres/",
            "/espace-prive/signalements/",
            "/espace-prive/paiements/",
            "/espace-prive/monetisation/",
            "/espace-prive/communications/",
            "/espace-prive/configuration/",
            "/espace-prive/monitoring/",
            "/espace-prive/equipe/",
            "/espace-prive/profil/",
        ]:
            self._assert_access(self.super, url, True)

    def test_admin_matrix(self):
        allowed = {
            "/espace-prive/dashboard/",
            "/espace-prive/membres/",
            "/espace-prive/monetisation/",
            "/espace-prive/communications/",
            "/espace-prive/profil/",
        }
        denied = {
            "/espace-prive/signalements/",
            "/espace-prive/paiements/",
            "/espace-prive/configuration/",
            "/espace-prive/monitoring/",
            "/espace-prive/equipe/",
        }
        for url in allowed:
            self._assert_access(self.admin, url, True)
        for url in denied:
            self._assert_access(self.admin, url, False)

    def test_moderator_matrix(self):
        allowed = {
            "/espace-prive/dashboard/",
            "/espace-prive/membres/",
            "/espace-prive/signalements/",
            "/espace-prive/communications/",
            "/espace-prive/configuration/",
            "/espace-prive/monitoring/",
            "/espace-prive/profil/",
        }
        denied = {
            "/espace-prive/monetisation/",
            "/espace-prive/paiements/",
            "/espace-prive/equipe/",
        }
        for url in allowed:
            self._assert_access(self.mod, url, True)
        for url in denied:
            self._assert_access(self.mod, url, False)

    def test_nav_links_filtered(self):
        from core.controllers import rbac_controller

        admin_keys = {
            link["key"]
            for section in rbac_controller.nav_links_for(self.admin)
            for link in section["links"]
        }
        mod_keys = {
            link["key"]
            for section in rbac_controller.nav_links_for(self.mod)
            for link in section["links"]
        }
        self.assertEqual(
            admin_keys,
            {"dashboard", "profil", "membres", "monetisation", "communications"},
        )
        self.assertEqual(
            mod_keys,
            {
                "dashboard",
                "profil",
                "membres",
                "signalements",
                "communications",
                "configuration",
                "monitoring",
            },
        )
        self.assertIn("monitoring", mod_keys)
        self.assertNotIn("monitoring", admin_keys)

    def test_forged_superadmin_role_without_staff_flag_is_denied(self):
        member = make_profile("forged.role@test.com", Gender.MALE, "Forged")
        member.role = UserRole.SUPER_ADMIN
        member.save(update_fields=["role"])
        member.user.is_staff = False
        member.user.save(update_fields=["is_staff"])
        member.refresh_from_db()
        self.assertFalse(member.is_admin)
        self.assertFalse(member.is_super_admin)
        client = Client()
        client.force_login(member.user)
        resp = client.get("/espace-prive/dashboard/")
        self.assertEqual(resp.status_code, 302)
        self.assertNotIn("/espace-prive/dashboard/", resp.url)

    def test_cannot_deactivate_protected_superadmin(self):
        from core.controllers import rbac_controller

        protected = make_staff("admin@timalove.local", UserRole.SUPER_ADMIN, "Canonical")
        attacker = make_staff("attacker.rbac@test.com", UserRole.SUPER_ADMIN, "Attacker")
        with self.assertRaises(PermissionError):
            rbac_controller.deactivate_staff(attacker, protected.id)
        with self.assertRaises(PermissionError):
            rbac_controller.update_staff_role(attacker, protected.id, UserRole.SUPPORT)
        with self.assertRaises(PermissionError):
            rbac_controller.delete_staff(attacker, protected.id)
        protected.refresh_from_db()
        self.assertEqual(protected.role, UserRole.SUPER_ADMIN)
        self.assertTrue(protected.user.is_active)
        self.assertTrue(protected.user.is_staff)


class PublicAdminLoginTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.admin = make_staff("admin@timalove.local", UserRole.SUPER_ADMIN, "Super")

    def test_superadmin_logs_in_via_public_email_form(self):
        resp = self.client.post(
            "/connexion/",
            {
                "email": "admin@timalove.local",
                "password": "StaffPass123!",
                "login_mode": "email",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["ok"])
        self.assertIn("/espace-prive/dashboard/", data["redirect"])

    def test_superadmin_login_ignores_member_next(self):
        resp = self.client.post(
            "/connexion/",
            {
                "email": "admin@timalove.local",
                "password": "StaffPass123!",
                "login_mode": "email",
                "next": "/explorer/",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertTrue(resp.json()["ok"])
        self.assertIn("/espace-prive/dashboard/", resp.json()["redirect"])

    def test_logout_returns_to_public_login(self):
        self.client.force_login(self.admin.user)
        resp = self.client.get("/deconnexion/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/connexion/", resp.url)
        self.assertIn("signup=1", resp.url)
        self.assertNotIn("tab=email", resp.url)

    def test_login_page_does_not_auto_open_email_modal(self):
        resp = self.client.get("/connexion/?signup=1&tab=email")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'data-login-mode=""')
        self.assertContains(resp, 'id="auth-login-modal" hidden')
        resp = self.client.get("/espace-prive/connexion/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/connexion/", resp.url)
        self.assertIn("signup=1", resp.url)

    def test_espace_prive_connexion_post_does_not_authenticate(self):
        resp = self.client.post(
            "/espace-prive/connexion/",
            {"email": "admin@timalove.local", "password": "StaffPass123!"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/connexion/", resp.url)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_espace_prive_dashboard_guest_redirects_to_public_login(self):
        resp = self.client.get("/espace-prive/dashboard/")
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/connexion/", resp.url)
        self.assertIn("signup=1", resp.url)

    def test_oversized_message_is_rejected(self):
        from core.controllers import message_controller

        partner = make_profile("msg.limit@test.com", Gender.FEMALE, "Awa")
        partner.onboarding_completed = True
        partner.save(update_fields=["onboarding_completed"])
        ok, msg, created = message_controller.send_text(
            self.admin, partner.id, "x" * 3000
        )
        self.assertFalse(ok)
        self.assertIn("trop long", msg.lower())
        self.assertIsNone(created)


class AdminStaffProfileTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        site_settings_controller.set_value("admin_security", {"require_2fa": False})
        self.admin = make_staff("staff.profil@test.com", UserRole.SUPER_ADMIN, "Awa")
        self.client = Client()
        self.client.force_login(self.admin.user)

    def test_profile_page_shows_staff_info(self):
        resp = self.client.get("/espace-prive/profil/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "staff.profil@test.com")
        self.assertContains(resp, "Awa")
        self.assertContains(resp, "Mon profil")

    def test_update_identity(self):
        resp = self.client.post(
            "/espace-prive/profil/",
            {
                "action": "save_identity",
                "first_name": "Awa Fatou",
                "last_name": "Diop",
                "phone": "77 123 45 67",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.first_name, "Awa Fatou")
        self.assertEqual(self.admin.last_name, "Diop")
        self.assertIn("77", self.admin.phone or "")

    def test_change_email_with_password(self):
        resp = self.client.post(
            "/espace-prive/profil/",
            {
                "action": "change_email",
                "email": "awa.staff@test.com",
                "current_password": "StaffPass123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.admin.refresh_from_db()
        self.admin.user.refresh_from_db()
        self.assertEqual(self.admin.email, "awa.staff@test.com")
        self.assertEqual(self.admin.user.email, "awa.staff@test.com")

    def test_protected_canonical_email_cannot_change(self):
        protected = make_staff("admin@timalove.local", UserRole.SUPER_ADMIN, "Canon")
        client = Client()
        client.force_login(protected.user)
        resp = client.post(
            "/espace-prive/profil/",
            {
                "action": "change_email",
                "email": "autre.admin@test.com",
                "current_password": "StaffPass123!",
            },
            follow=True,
        )
        protected.refresh_from_db()
        self.assertEqual((protected.email or "").lower(), "admin@timalove.local")
        self.assertContains(resp, "ne peut pas être modifié")

    def test_change_password_then_login(self):
        resp = self.client.post(
            "/espace-prive/profil/",
            {
                "action": "change_password",
                "current_password": "StaffPass123!",
                "new_password": "NouveauPass123!",
                "confirm_password": "NouveauPass123!",
            },
        )
        self.assertEqual(resp.status_code, 302)
        self.client.logout()
        login = self.client.post(
            "/connexion/",
            {
                "email": "staff.profil@test.com",
                "password": "NouveauPass123!",
                "login_mode": "email",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json()["ok"])
        self.assertIn("/espace-prive/dashboard/", login.json()["redirect"])


class StaffPasswordResetTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.admin = make_staff("reset.staff@test.com", UserRole.ADMIN, "Reset")

    def test_forgot_password_page_is_public(self):
        resp = self.client.get("/mot-de-passe-oublie/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "équipe TimaLove")

    def test_request_reset_sends_mail_for_staff(self):
        with patch(
            "core.views.auth.views.email_controller.password_reset_email",
            return_value=True,
        ) as mocked:
            resp = self.client.post(
                "/mot-de-passe-oublie/",
                {"email": "reset.staff@test.com"},
            )
        self.assertEqual(resp.status_code, 302)
        mocked.assert_called_once()
        self.assertEqual(mocked.call_args[0][0], "reset.staff@test.com")
        self.assertTrue(mocked.call_args[0][1])

    def test_confirm_reset_allows_staff_login(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        uid = urlsafe_base64_encode(force_bytes(self.admin.user.pk))
        token = default_token_generator.make_token(self.admin.user)
        resp = self.client.post(
            f"/reinitialiser-mot-de-passe/{uid}/{token}/",
            {"password": "ResetPass123!", "password_confirm": "ResetPass123!"},
        )
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/connexion/", resp.url)
        self.assertIn("signup=1", resp.url)
        login = self.client.post(
            "/connexion/",
            {
                "email": "reset.staff@test.com",
                "password": "ResetPass123!",
                "login_mode": "email",
            },
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )
        self.assertEqual(login.status_code, 200)
        self.assertTrue(login.json()["ok"])


class MonitoringSystemEventTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        site_settings_controller.set_value("admin_security", {"require_2fa": False})
        self.mod = make_staff("mod.monitor@test.com", UserRole.MODERATOR, "Mod")

    def test_record_exception_appears_on_monitoring(self):
        from django.test import RequestFactory

        from core.controllers import monitoring_controller
        from core.models import SystemEvent

        rf = RequestFactory()
        req = rf.post("/api/messages/send/")
        try:
            raise RuntimeError("Echec envoi message test")
        except RuntimeError as exc:
            monitoring_controller.record_exception(req, exc)

        event = SystemEvent.objects.order_by("-last_seen_at").first()
        self.assertIsNotNone(event)
        self.assertEqual(event.level, "error")
        self.assertEqual(event.source, "exception")
        self.assertIn("/api/messages/send/", event.path)
        self.assertTrue(event.location or event.traceback)

        client = Client()
        client.force_login(self.mod.user)
        resp = client.get("/espace-prive/monitoring/")
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "Echec envoi message test")
        self.assertContains(resp, "Journal des erreurs")

    def test_journal_excludes_warnings_and_slow_requests(self):
        from django.test import RequestFactory

        from core.controllers import monitoring_controller
        from core.models import SystemEvent

        rf = RequestFactory()
        req = rf.get("/api/likes/count/")

        monitoring_controller.record_slow_request(req, 2500.0)
        monitoring_controller.record_http_error(req, 404)
        monitoring_controller.record_http_error(req, 500)
        monitoring_controller.record_exception(req, RuntimeError("Erreur reelle"))

        listed = monitoring_controller.list_events()
        levels = {e.level for e in listed}
        sources = {e.source for e in listed}
        titles = " ".join(e.title for e in listed)

        self.assertNotIn("warning", levels)
        self.assertNotIn(SystemEvent.Source.SLOW, sources)
        self.assertIn("Erreur reelle", titles)
        self.assertNotIn("HTTP 500", titles)
        self.assertNotIn("HTTP 404", titles)
        self.assertNotIn("Requête lente", titles)

    def test_http404_not_recorded(self):
        from django.http import Http404
        from django.test import RequestFactory

        from core.controllers import monitoring_controller
        from core.models import SystemEvent

        rf = RequestFactory()
        req = rf.get("/profil/inconnu/")
        monitoring_controller.record_exception(req, Http404("Profil introuvable"))

        self.assertFalse(SystemEvent.objects.filter(exception_type="Http404").exists())

    def test_duplicate_http500_skipped_when_exception_logged(self):
        from django.test import RequestFactory

        from core.controllers import monitoring_controller
        from core.models import SystemEvent

        rf = RequestFactory()
        req = rf.get("/espace-prive/paiements/")
        monitoring_controller.record_exception(req, RuntimeError("Erreur unique test"))
        monitoring_controller.record_http_error(req, 500)

        http_events = SystemEvent.objects.filter(source="http", path="/espace-prive/paiements/")
        self.assertEqual(http_events.count(), 0)


class StrictGenderDiscoveryTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.man = make_profile("man-gender@test.com", Gender.MALE, "Man")
        self.man.photo_url = "https://example.com/man.jpg"
        self.man.save(update_fields=["photo_url", "updated_at"])
        self.woman = make_profile("woman-gender@test.com", Gender.FEMALE, "Woman")
        self.woman.photo_url = "https://example.com/woman.jpg"
        self.woman.save(update_fields=["photo_url", "updated_at"])
        self.man2 = make_profile("man2-gender@test.com", Gender.MALE, "Man2")
        self.man2.photo_url = "https://example.com/man2.jpg"
        self.man2.save(update_fields=["photo_url", "updated_at"])

    def test_male_feed_only_shows_females(self):
        from core.controllers.profile_controller import apply_opposite_gender_filter

        qs = Profile.objects.filter(role=UserRole.MEMBER)
        filtered = apply_opposite_gender_filter(qs, self.man)
        self.assertEqual(set(filtered.values_list("gender", flat=True)), {Gender.FEMALE})
        self.assertIn(self.woman.pk, filtered.values_list("pk", flat=True))
        self.assertNotIn(self.man2.pk, filtered.values_list("pk", flat=True))

    def test_female_feed_only_shows_males(self):
        from core.controllers.profile_controller import apply_opposite_gender_filter

        qs = Profile.objects.filter(role=UserRole.MEMBER)
        filtered = apply_opposite_gender_filter(qs, self.woman)
        self.assertEqual(set(filtered.values_list("gender", flat=True)), {Gender.MALE})

    def test_vip_cannot_bypass_gender_filter(self):
        from core.controllers import subscription_controller
        from core.models.choices import SubscriptionStatus, SubscriptionTier

        self.man.subscription_tier = SubscriptionTier.VIP_1M
        self.man.subscription_status = SubscriptionStatus.ACTIVE
        self.man.save(update_fields=["subscription_tier", "subscription_status", "updated_at"])
        self.assertFalse(subscription_controller.can_bypass_gender_filter(self.man))

    def test_swipe_same_gender_rejected(self):
        result = swipe_controller.record_swipe(self.man, self.man2.id, "like")
        self.assertFalse(result["ok"])

    def test_explore_profile_blocks_same_gender(self):
        from core.controllers import explore_controller

        data = explore_controller.get_public_profile(self.man2.id, viewer=self.man)
        self.assertIsNone(data)

    def test_explore_feed_excludes_same_gender(self):
        from core.controllers import explore_controller

        ids = explore_controller._eligible_ids(self.man)
        self.assertIn(self.woman.pk, ids)
        self.assertNotIn(self.man2.pk, ids)

    def test_feed_session_avoids_immediate_repeat_on_refresh(self):
        from django.contrib.sessions.backends.db import SessionStore
        from core.controllers import explore_controller

        w2 = make_profile("w2-gender@test.com", Gender.FEMALE, "W2")
        w2.photo_url = "https://example.com/w2.jpg"
        w2.onboarding_completed = True
        w2.save(update_fields=["photo_url", "onboarding_completed", "updated_at"])

        session = SessionStore()
        session.save()
        first, _ = explore_controller.public_feed(limit=1, viewer=self.man, session=session, seed="seed-a")
        second, _ = explore_controller.public_feed(limit=1, viewer=self.man, session=session, seed="seed-b")
        self.assertTrue(first and second)
        self.assertNotEqual(first[0]["id"], second[0]["id"])

    def test_sync_feed_session_resets_on_gender_change(self):
        from django.contrib.sessions.backends.db import SessionStore
        from core.controllers.explore_controller import SESSION_ELIGIBILITY_KEY, SESSION_QUEUE_KEY, sync_feed_session

        session = SessionStore()
        session[SESSION_QUEUE_KEY] = ["fake-id"]
        session[SESSION_ELIGIBILITY_KEY] = Gender.MALE
        session.save()

        sync_feed_session(session, self.woman)
        self.assertEqual(session.get(SESSION_ELIGIBILITY_KEY), Gender.FEMALE)
        self.assertNotIn(SESSION_QUEUE_KEY, session)

    def test_no_gender_viewer_sees_all_profiles(self):
        from core.controllers import explore_controller
        from core.controllers.profile_controller import apply_opposite_gender_filter

        neutral = make_profile("neutral-gender@test.com", Gender.MALE, "Neutral")
        neutral.gender = ""
        neutral.photo_url = "https://example.com/neutral.jpg"
        neutral.save(update_fields=["gender", "photo_url", "updated_at"])

        qs = Profile.objects.filter(role=UserRole.MEMBER)
        filtered = apply_opposite_gender_filter(qs, neutral)
        self.assertIn(self.man.pk, filtered.values_list("pk", flat=True))
        self.assertIn(self.woman.pk, filtered.values_list("pk", flat=True))

        ids = explore_controller._eligible_ids(neutral)
        self.assertIn(self.man.pk, ids)
        self.assertIn(self.woman.pk, ids)


class ApiPaymentsConfirmTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.profile = make_profile("confirm@test.com", Gender.MALE, "Confirm")

    @patch("core.views.api.views.payment_controller.confirm_order")
    def test_payments_confirm_redirects_with_message(self, confirm_mock):
        confirm_mock.return_value = (True, "Paiement confirmé.")
        client = Client()
        client.force_login(self.profile.user)
        resp = client.get("/api/payments/confirm/?order_id=test-order&simulate=1", follow=False)
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/profil", resp["Location"])


class CoachingAmountTests(TestCase):
    def test_eur_price_converts_to_fcfa(self):
        from core.controllers.coaching_controller import coaching_amount_fcfa

        self.assertEqual(coaching_amount_fcfa(40), 26000)

    def test_large_fcfa_value_not_multiplied(self):
        from core.controllers.coaching_controller import coaching_amount_fcfa

        self.assertEqual(coaching_amount_fcfa(26000), 26000)

    def test_overflow_price_is_capped(self):
        from core.controllers.coaching_controller import coaching_amount_fcfa

        self.assertEqual(coaching_amount_fcfa(5000), 2_000_000)


class PaginationUtilsTests(TestCase):
    def test_safe_page_returns_last_page_when_out_of_range(self):
        from django.core.paginator import Paginator

        from core.controllers.pagination_utils import safe_page

        paginator = Paginator([1, 2, 3], 2)
        page = safe_page(paginator, 99)
        self.assertEqual(page.number, 2)


class ProfilePhotoPrimaryTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.profile = make_profile("photo@test.com", Gender.FEMALE, "Photo")
        self.profile.photo_url = "https://example.com/main.jpg"
        self.profile.save(update_fields=["photo_url", "updated_at"])

    def test_invalid_photo_id_returns_400_not_500(self):
        client = Client()
        client.force_login(self.profile.user)
        resp = client.post(
            "/api/profile/photo/primary/",
            data='{"id":"not-a-uuid"}',
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.json()["ok"])


class NabooPayFinanceTests(TestCase):
    def test_naboo_product_bucket(self):
        from core.controllers.finance_controller import _naboo_product_bucket

        self.assertEqual(_naboo_product_bucket("TimaLove — Premium 1 mois"), "subscription")
        self.assertEqual(_naboo_product_bucket("TimaLove — Boost 24h"), "one_shot")

    def test_naboopay_row_maps_pending_transaction(self):
        from core.controllers.finance_controller import naboopay_transaction_row

        row = naboopay_transaction_row(
            {
                "order_id": "dad31fe4-6b71-4c9e-aa24-007e35863bad",
                "amount": 2990,
                "currency": "XOF",
                "transaction_status": "pending",
                "customer": {"first_name": "Saloum", "last_name": "Ndiaye", "phone": "+221776744575"},
                "products": [{"name": "TimaLove — Premium 1 mois", "price": 2990, "quantity": 1}],
                "created_at": "2026-09-11T00:13:26.06Z",
                "paid_at": "0001-01-01T00:00:00Z",
                "selected_payment_method": "",
            }
        )
        self.assertEqual(row["user_name"], "Saloum Ndiaye")
        self.assertEqual(row["status"], "pending")
        self.assertEqual(row["amount"], 2990)
        self.assertEqual(row["product"], "TimaLove — Premium 1 mois")
        self.assertEqual(row["provider"], "NabooPay")

    def test_naboopay_sync_incremental_merges_only_new_rows(self):
        from unittest.mock import patch

        from django.core.cache import cache

        from core.controllers import naboopay_sync_controller
        from core.controllers.finance_controller import naboopay_transaction_row

        cache.clear()
        existing = naboopay_transaction_row(
            {
                "order_id": "11111111-1111-1111-1111-111111111111",
                "amount": 1000,
                "currency": "XOF",
                "transaction_status": "paid",
                "customer": {"first_name": "A", "last_name": "B", "phone": "+221770000001"},
                "products": [{"name": "TimaLove — Premium 1 mois"}],
                "created_at": "2026-09-10T10:00:00Z",
                "paid_at": "2026-09-10T10:05:00Z",
                "selected_payment_method": "wave",
            }
        )
        naboopay_sync_controller._save_rows([existing], {"synced_at": "2026-09-10T12:00:00+00:00"})

        new_tx = {
            "order_id": "22222222-2222-2222-2222-222222222222",
            "amount": 2000,
            "currency": "XOF",
            "transaction_status": "paid",
            "customer": {"first_name": "C", "last_name": "D", "phone": "+221770000002"},
            "products": [{"name": "TimaLove — Boost 24h"}],
            "created_at": "2026-09-11T00:00:00Z",
            "paid_at": "2026-09-11T00:01:00Z",
            "selected_payment_method": "wave",
        }

        with patch("core.controllers.naboopay_sync_controller.naboopay_controller.list_transactions") as mocked:
            mocked.return_value = {
                "ok": True,
                "transactions": [new_tx],
                "pagination": {"page": 1, "total_pages": 1, "total_count": 2, "limit": 100},
            }
            rows, meta, error = naboopay_sync_controller.sync()

        self.assertIsNone(error)
        self.assertEqual(meta["sync_mode"], "incremental")
        self.assertEqual(meta["last_new_count"], 1)
        self.assertEqual(len(rows), 2)

    def test_naboopay_sync_serves_cache_without_api_when_fresh(self):
        from unittest.mock import patch

        from django.core.cache import cache
        from django.utils import timezone

        from core.controllers import naboopay_sync_controller
        from core.controllers.finance_controller import naboopay_transaction_row

        cache.clear()
        row = naboopay_transaction_row(
            {
                "order_id": "33333333-3333-3333-3333-333333333333",
                "amount": 500,
                "currency": "XOF",
                "transaction_status": "paid",
                "customer": {"first_name": "E", "last_name": "F", "phone": "+221770000003"},
                "products": [{"name": "TimaLove — Premium 1 mois"}],
                "created_at": "2026-09-11T00:00:00Z",
                "paid_at": "2026-09-11T00:01:00Z",
                "selected_payment_method": "wave",
            }
        )
        naboopay_sync_controller._save_rows(
            [row],
            {"synced_at": timezone.now().isoformat(), "row_count": 1},
        )

        with patch("core.controllers.naboopay_sync_controller.naboopay_controller.list_transactions") as mocked:
            rows, meta, error = naboopay_sync_controller.sync()
            mocked.assert_not_called()

        self.assertIsNone(error)
        self.assertTrue(meta["from_cache"])
        self.assertEqual(meta["sync_mode"], "cache")
        self.assertEqual(len(rows), 1)

    def test_naboopay_filter_rows_by_status(self):
        from core.controllers import naboopay_sync_controller
        from core.controllers.finance_controller import naboopay_transaction_row
        from core.models.choices import TransactionStatus

        paid = naboopay_transaction_row(
            {
                "order_id": "aaaa",
                "amount": 1000,
                "transaction_status": "paid",
                "customer": {},
                "products": [],
                "created_at": "2026-09-11T00:00:00Z",
                "paid_at": "2026-09-11T00:01:00Z",
            }
        )
        failed = naboopay_transaction_row(
            {
                "order_id": "bbbb",
                "amount": 500,
                "transaction_status": "failed",
                "customer": {},
                "products": [],
                "created_at": "2026-09-11T00:00:00Z",
                "paid_at": "0001-01-01T00:00:00Z",
            }
        )
        filtered = naboopay_sync_controller.filter_rows([paid, failed], status=TransactionStatus.PAID)
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]["order_id"], "aaaa")


class CountryNormalizeTests(TestCase):
    def test_merges_senegal_variants(self):
        from core.data.country_normalize import normalize_country_label

        self.assertEqual(normalize_country_label("Senegal"), "Sénégal")
        self.assertEqual(normalize_country_label("senegal"), "Sénégal")
        self.assertEqual(normalize_country_label("SENEGAL"), "Sénégal")
        self.assertEqual(normalize_country_label("Sénégalais"), "Sénégal")

    def test_maps_senegal_cities(self):
        from core.data.country_normalize import normalize_country_label

        self.assertEqual(normalize_country_label("Dakar"), "Sénégal")
        self.assertEqual(normalize_country_label("Thiès"), "Sénégal")

    def test_top_countries_aggregates_residence_normalized(self):
        from core.controllers.admin_controller import _top_countries

        make_profile("geo-a@test.com", Gender.MALE, "A")
        p1 = Profile.objects.get(email="geo-a@test.com")
        p1.country = "France"
        p1.residence_country = "Senegal"
        p1.save(update_fields=["country", "residence_country", "updated_at"])

        make_profile("geo-b@test.com", Gender.FEMALE, "B")
        p2 = Profile.objects.get(email="geo-b@test.com")
        p2.country = "France"
        p2.residence_country = "Dakar"
        p2.save(update_fields=["country", "residence_country", "updated_at"])

        data = _top_countries(limit=5)
        self.assertIn("Sénégal", data["labels"])
        senegal_count = data["values"][data["labels"].index("Sénégal")]
        self.assertGreaterEqual(senegal_count, 2)
        self.assertIn("all", data)
        self.assertGreaterEqual(len(data["all"]), 1)
        self.assertEqual(data["country_count"], len(data["all"]))


class GenderPromptTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()

    def test_needs_gender_prompt_when_empty(self):
        from core.controllers.profile_controller import needs_gender_prompt

        profile = make_profile("nogender@test.com", Gender.MALE, "No")
        profile.gender = ""
        profile.save(update_fields=["gender", "updated_at"])
        self.assertTrue(needs_gender_prompt(profile))

    def test_no_prompt_when_gender_set(self):
        from core.controllers.profile_controller import needs_gender_prompt

        profile = make_profile("hasgender@test.com", Gender.FEMALE, "Yes")
        self.assertFalse(needs_gender_prompt(profile))

    def test_profile_update_gender_via_api(self):
        from django.test import Client

        profile = make_profile("setgender@test.com", Gender.MALE, "Set")
        profile.gender = ""
        profile.save(update_fields=["gender", "updated_at"])
        user = profile.user
        user.set_password("Ludvanne12")
        user.save()
        client = Client(enforce_csrf_checks=False)
        client.login(username=user.username, password="Ludvanne12")
        r = client.post(
            "/api/profile/update/",
            data='{"gender":"female"}',
            content_type="application/json",
        )
        self.assertEqual(r.status_code, 200)
        profile.refresh_from_db()
        self.assertEqual(profile.gender, Gender.FEMALE)


class SignupSocioPersistTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()

    def _signup_draft(self, **overrides):
        from core.data.countries import COUNTRIES_FR

        base = {
            "channel": "email",
            "email": "socio-save@test.com",
            "password": "Secret123!",
            "first_name": "Socio",
            "last_name": "Save",
            "age": 26,
            "phone": "+221771112233",
            "gender": Gender.MALE,
            "religion": Religion.MUSULMANE,
            "country": COUNTRIES_FR[0],
            "photo_url": "https://example.com/photo.jpg",
            "terms_accepted": True,
        }
        base.update(overrides)
        return base

    def test_register_from_draft_persists_gender(self):
        ok, msg, profile, errors, step = signup_controller.register_from_draft(self._signup_draft())
        self.assertTrue(ok, msg)
        self.assertIsNone(step)
        self.assertEqual(profile.gender, Gender.MALE)
        profile.refresh_from_db()
        self.assertEqual(profile.gender, Gender.MALE)
        self.assertEqual(profile.religion, Religion.MUSULMANE)

    def test_complete_oauth_profile_persists_gender(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="oauth-socio@test.com",
            email="oauth-socio@test.com",
            password="unused123",
        )
        profile = Profile.objects.create(
            user=user,
            first_name="OAuth",
            last_name="Test",
            email="oauth-socio@test.com",
            google_uid="google-socio-uid",
            gender="",
            photo_url="https://example.com/existing.jpg",
        )
        ok, msg, errors, step = signup_controller.complete_oauth_profile(
            profile,
            self._signup_draft(
                channel="oauth",
                email="oauth-socio@test.com",
                gender=Gender.FEMALE,
                religion=Religion.CHRETIENNE,
            ),
        )
        self.assertTrue(ok, msg)
        self.assertIsNone(step)
        profile.refresh_from_db()
        self.assertEqual(profile.gender, Gender.FEMALE)
        self.assertEqual(profile.religion, Religion.CHRETIENNE)


class AccountDeletionReregistrationTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()

    def test_delete_account_allows_email_reregistration(self):
        profile = make_profile("rejoin@test.com", Gender.FEMALE, "Rejoin")
        profile.phone = "+221771234567"
        profile.google_uid = "google-uid-123"
        profile.save(update_fields=["phone", "google_uid", "updated_at"])

        profile_controller.delete_account(profile)

        self.assertFalse(User.objects.filter(email="rejoin@test.com").exists())
        self.assertFalse(Profile.objects.filter(email__iexact="rejoin@test.com").exists())

        ok, msg, new_profile = auth_controller.register_member(
            {
                "email": "rejoin@test.com",
                "phone": "+221771234567",
                "password": "secret123",
                "date_of_birth": "1995-01-01",
                "gender": Gender.FEMALE,
                "first_name": "Rejoin",
                "last_name": "Again",
            }
        )
        self.assertTrue(ok, msg)
        self.assertIsNotNone(new_profile)
        self.assertEqual(new_profile.email, "rejoin@test.com")

    def test_delete_account_clears_banned_identity_for_voluntary_delete(self):
        from core.models import BannedIdentity

        profile = make_profile("voluntary@test.com", Gender.MALE, "Vol")
        BannedIdentity.objects.create(
            profile=profile,
            email_normalized="voluntary@test.com",
            reason="legacy",
        )

        profile_controller.delete_account(profile)

        self.assertFalse(BannedIdentity.objects.filter(email_normalized="voluntary@test.com").exists())
        errors = signup_controller.check_identifier({"email": "voluntary@test.com"})
        self.assertNotIn("email", errors)

    def test_admin_delete_banned_member_keeps_ban_block(self):
        from core.models import BannedIdentity
        from core.controllers import admin_controller

        profile = make_profile("banned@test.com", Gender.MALE, "Banned")
        profile.banned_at = timezone.now()
        profile.save(update_fields=["banned_at", "updated_at"])
        BannedIdentity.objects.create(
            profile=profile,
            email_normalized="banned@test.com",
            reason="modération",
        )

        admin_controller.delete_member_account(profile.id)

        self.assertTrue(BannedIdentity.objects.filter(email_normalized="banned@test.com").exists())
        errors = signup_controller.check_identifier({"email": "banned@test.com"})
        self.assertIn("email", errors)

    def test_orphan_user_does_not_block_signup(self):
        User.objects.create_user(
            username="orphan@test.com",
            email="orphan@test.com",
            password="unused123",
        )
        self.assertFalse(Profile.objects.filter(email__iexact="orphan@test.com").exists())

        errors = signup_controller.check_identifier({"email": "orphan@test.com"})
        self.assertNotIn("email", errors)

        ok, msg, profile = auth_controller.register_member(
            {
                "email": "orphan@test.com",
                "password": "secret123",
                "date_of_birth": "1994-06-15",
                "gender": Gender.MALE,
                "first_name": "Orphan",
                "last_name": "Fix",
            }
        )
        self.assertTrue(ok, msg)
        self.assertIsNotNone(profile)


class VoiceIntroTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.client = Client()
        self.owner = make_profile("voice.owner@gmail.com", Gender.FEMALE, "Awa")
        self.viewer = make_profile("voice.viewer@gmail.com", Gender.MALE, "Amadou")
        self.owner.user.set_password("Ludvanne12")
        self.owner.user.save()
        self.viewer.user.set_password("Ludvanne12")
        self.viewer.user.save()

    def _wav(self, seconds=1):
        import io
        import wave

        from django.core.files.uploadedfile import SimpleUploadedFile

        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(8000)
            wf.writeframes(b"\x00\x00" * (8000 * seconds))
        return SimpleUploadedFile("intro.wav", buf.getvalue(), content_type="audio/wav")

    def test_save_and_delete_voice_intro(self):
        import tempfile
        from pathlib import Path

        from django.test import override_settings

        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
                self.assertTrue(self.client.login(username=self.owner.user.username, password="Ludvanne12"))
                posted = self.client.post(
                    "/api/profile/voice/",
                    {"duration": "8", "file": self._wav()},
                )
                self.assertEqual(posted.status_code, 200, posted.content)
                payload = posted.json()
                self.assertTrue(payload["ok"])
                self.assertTrue(payload["has_voice_intro"])
                self.assertEqual(payload["voice_intro_duration"], 8)
                self.owner.refresh_from_db()
                self.assertTrue(self.owner.voice_intro_url)
                stored = Path(tmp) / "voice-intros"
                self.assertTrue(any(stored.iterdir()))

                deleted = self.client.post("/api/profile/voice/delete/")
                self.assertEqual(deleted.status_code, 200)
                self.assertFalse(deleted.json()["has_voice_intro"])
                self.owner.refresh_from_db()
                self.assertFalse(self.owner.voice_intro_url)

    def test_rejects_voice_longer_than_30_seconds(self):
        import tempfile

        from django.test import override_settings

        with tempfile.TemporaryDirectory() as tmp:
            with override_settings(MEDIA_ROOT=tmp, MEDIA_URL="/media/"):
                self.assertTrue(self.client.login(username=self.owner.user.username, password="Ludvanne12"))
                posted = self.client.post(
                    "/api/profile/voice/",
                    {"duration": "31", "file": self._wav()},
                )
                self.assertEqual(posted.status_code, 400)
                self.assertIn("30", posted.json()["message"])
                self.owner.refresh_from_db()
                self.assertFalse(self.owner.voice_intro_url)

    def test_public_profile_and_report_include_voice(self):
        from core.controllers import explore_controller, moderation_controller
        from core.models import Report

        self.owner.voice_intro_url = "/media/voice-intros/awa-demo.wav"
        self.owner.voice_intro_duration_seconds = 8
        self.owner.photo_url = "https://example.com/awa.webp"
        self.owner.onboarding_completed = True
        self.owner.save(
            update_fields=[
                "voice_intro_url",
                "voice_intro_duration_seconds",
                "photo_url",
                "onboarding_completed",
                "updated_at",
            ]
        )
        card = explore_controller.serialize_card(self.owner, viewer=self.viewer)
        self.assertTrue(card["has_voice_intro"])
        self.assertEqual(card["voice_intro_duration"], 8)
        public = explore_controller.get_public_profile(self.owner.id, viewer=self.viewer)
        self.assertTrue(public["has_voice_intro"])

        report = moderation_controller.create_report(
            self.viewer,
            {
                "reported_profile_id": str(self.owner.id),
                "reason": "inappropriate_voice",
                "report_kind": "voice",
                "message": "Présentation vocale inappropriée pour TimaLove.",
            },
        )
        self.assertEqual(report.report_kind, "voice")
        self.assertEqual(Report.objects.filter(report_kind="voice").count(), 1)

    def test_apple_review_feed_pins_awa_voice(self):
        from core.controllers import explore_controller

        reviewer = make_profile("apple.review@timalove.local", Gender.MALE, "Amadou")
        awa = make_profile("awa.demo@timalove.local", Gender.FEMALE, "Awa")
        other = make_profile("other.demo@timalove.local", Gender.FEMALE, "Other")
        awa.voice_intro_url = "/media/voice-intros/awa-demo.wav"
        awa.voice_intro_duration_seconds = 8
        awa.save(update_fields=["voice_intro_url", "voice_intro_duration_seconds", "updated_at"])
        pinned = explore_controller._pin_review_voice_intro(reviewer, [other.pk])
        self.assertEqual(pinned[0], awa.pk)
        self.assertIn(other.pk, pinned)


class GuidedIntroTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        from core.controllers import app_config_controller

        cfg = app_config_controller.get_app_config()
        cfg["guided_messages_enabled"] = True
        app_config_controller.save_app_config(cfg)
        self.client = Client(enforce_csrf_checks=False)
        self.p1 = make_profile("guided1@gmail.com", Gender.MALE, "Amadou")
        self.p2 = make_profile("guided2@gmail.com", Gender.FEMALE, "Fatou")
        for profile in (self.p1, self.p2):
            profile.onboarding_completed = True
            profile.save(update_fields=["onboarding_completed", "updated_at"])
        self.p1.user.set_password("Ludvanne12")
        self.p1.user.save()
        self.p2.user.set_password("Ludvanne12")
        self.p2.user.save()
        swipe_controller.record_swipe(self.p1, self.p2.id, "like")
        swipe_controller.record_swipe(self.p2, self.p1.id, "like")

    def _voice_upload(self):
        data_size = 240
        payload = (
            b"RIFF"
            + (36 + data_size).to_bytes(4, "little")
            + b"WAVE"
            + b"fmt "
            + (16).to_bytes(4, "little")
            + (1).to_bytes(2, "little")
            + (1).to_bytes(2, "little")
            + (8000).to_bytes(4, "little")
            + (8000).to_bytes(4, "little")
            + (1).to_bytes(2, "little")
            + (8).to_bytes(2, "little")
            + b"data"
            + data_size.to_bytes(4, "little")
            + b"\x80" * data_size
        )
        return SimpleUploadedFile("guided.wav", payload, content_type="audio/wav")

    def _record_one(self, duration=8):
        from core.controllers import guided_intro_controller

        ok, msg, payload = guided_intro_controller.submit_clip(
            self.p1, self.p2.id, self._voice_upload(), duration
        )
        self.assertTrue(ok, msg)
        return payload

    def test_free_text_rejected_until_guided_prompt(self):
        ok, msg, _ = message_controller.send_text(self.p1, self.p2.id, "Salut ça va")
        self.assertFalse(ok)
        self.assertIn("questions", msg.lower())

    def test_one_voice_then_recipient_gate(self):
        from core.controllers import guided_intro_controller
        from core.models import Match, Swipe

        payload = self._record_one()
        self.assertTrue(payload.get("done"))
        match = message_controller.get_active_match(self.p1, self.p2.id)
        match.refresh_from_db()
        self.assertTrue(match.guided_intro_submitted)
        self.assertFalse(match.guided_intro_completed)
        self.assertEqual(message_controller.active_conversation_count(self.p1), 0)

        ok_wait, msg_wait, _ = message_controller.send_text(self.p1, self.p2.id, "Et toi ?")
        self.assertFalse(ok_wait)

        inbox_p2 = message_controller.list_conversations(self.p2)
        self.assertTrue(inbox_p2)
        self.assertTrue(inbox_p2[0]["guided_review_required"])
        self.assertIn("intention", inbox_p2[0]["preview"].lower())

        inbox_p1 = message_controller.list_conversations(self.p1)
        self.assertEqual(inbox_p1[0]["preview"], "En attente de décision")

        ok_accept, _ = guided_intro_controller.accept_intro(self.p2, self.p1.id)
        self.assertTrue(ok_accept)
        match.refresh_from_db()
        self.assertTrue(match.guided_intro_completed)
        self.assertEqual(message_controller.active_conversation_count(self.p1), 1)
        ok_free, _, _ = message_controller.send_text(self.p1, self.p2.id, "Merci pour votre sincérité.")
        self.assertTrue(ok_free)
        self.assertTrue(Match.objects.filter(pk=match.pk).exists())
        self.assertTrue(Swipe.objects.filter(swiper=self.p1, swiped=self.p2).exists())

    def test_text_fallback_opens_review(self):
        from core.controllers import guided_intro_controller

        ok, msg, payload = guided_intro_controller.submit_text(
            self.p1,
            self.p2.id,
            "Chez Fatou, c’est le sérieux du projet de couple et la clarté de ses valeurs.",
        )
        self.assertTrue(ok, msg)
        self.assertTrue(payload.get("done"))
        match = message_controller.get_active_match(self.p1, self.p2.id)
        self.assertTrue(match.guided_intro_submitted)
        clip = match.guided_clips.first()
        self.assertTrue(clip.answer_text)
        self.assertFalse(clip.voice_url)

    def test_reject_restores_discover(self):
        from core.controllers import guided_intro_controller
        from core.models import Match, Notification, Swipe

        self._record_one()
        ok, msg = guided_intro_controller.reject_intro(self.p2, self.p1.id)
        self.assertTrue(ok, msg)
        self.assertFalse(Match.objects.filter(user_1=self.p1, user_2=self.p2).exists())
        self.assertFalse(Match.objects.filter(user_1=self.p2, user_2=self.p1).exists())
        self.assertFalse(Swipe.objects.filter(swiper=self.p1, swiped=self.p2).exists())
        notice = Notification.objects.filter(user=self.p1, title="Discussion refusée").first()
        self.assertIsNotNone(notice)
        self.assertIn("retenter", notice.message.lower())
        hidden = swipe_controller.excluded_swiped_ids(self.p1)
        self.assertNotIn(self.p2.id, hidden)

    def test_withdraw_and_timeout_free_slot(self):
        from datetime import timedelta

        from django.utils import timezone

        from core.controllers import guided_intro_controller
        from core.models import Match, Swipe

        self._record_one()
        ok, msg = guided_intro_controller.withdraw_intro(self.p1, self.p2.id)
        self.assertTrue(ok, msg)
        self.assertFalse(Match.objects.filter(user_1=self.p1, user_2=self.p2).exists())
        self.assertTrue(Swipe.objects.filter(swiper=self.p1, swiped=self.p2).exists())

        self._record_one()
        match = message_controller.get_active_match(self.p1, self.p2.id)
        Match.objects.filter(pk=match.pk).update(updated_at=timezone.now() - timedelta(hours=49))
        expired = guided_intro_controller.expire_stale_intros()
        self.assertEqual(expired, 1)
        self.assertFalse(Match.objects.filter(pk=match.pk).exists())
        self.assertFalse(Swipe.objects.filter(swiper=self.p1, swiped=self.p2).exists())

    def test_skip_refused_and_ready_blocked(self):
        ok, msg = message_controller.skip_guided_intro(self.p1, self.p2.id)
        self.assertFalse(ok)
        self.assertIn("nécessaires", msg)
        ok_ready, ready_msg, _ = message_controller.mark_ready_to_meet(self.p1, self.p2.id)
        self.assertFalse(ok_ready)
        self.assertIn("questions de projet", ready_msg)

    def test_thread_shows_questions_not_skip_or_composer(self):
        self.assertTrue(self.client.login(username=self.p1.user.username, password="Ludvanne12"))
        page = self.client.get("/discussions/%s/" % self.p2.id)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "Pourquoi voulez-vous écrire")
        self.assertContains(page, "Enregistrer (15 s max)")
        self.assertContains(page, "Écrire un message à la place")
        self.assertNotContains(page, "Ignorer et écrire librement")
        self.assertNotContains(page, "Je suis prêt(e) à rencontrer cette personne")
        self.assertContains(page, "Un vocal de 15 s suffit")

    def test_recipient_modal_after_submit(self):
        self._record_one()
        self.assertTrue(self.client.login(username=self.p2.user.username, password="Ludvanne12"))
        page = self.client.get("/discussions/%s/" % self.p1.id)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "guided-review-modal")
        self.assertContains(page, "Continuer la discussion")
        self.assertContains(page, "Pas cette fois")
        self.assertContains(page, "Signaler")
        self.assertContains(page, "Bloquer")


class ProfileGuideCapsTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.profile = make_profile("guides@test.com", Gender.FEMALE, "Awa")

    def test_trim_excess_traits_values_looking(self):
        from core.controllers.profile_controller import trim_guide_fields
        from core.data.onboarding import looking_for_ids

        self.profile.personality_traits = ["bienveillant", "fidele", "spirituel", "ambitieux"]
        self.profile.life_values = ["famille", "foi", "sincerite", "respect"]
        self.profile.looking_for = json.dumps(
            ["serieux", "familial", "croyant", "calme", "ambitieux"]
        )
        self.profile.save()
        changed = trim_guide_fields(self.profile)
        self.assertIn("personality_traits", changed)
        self.assertIn("life_values", changed)
        self.assertIn("looking_for", changed)
        self.assertEqual(self.profile.personality_traits, ["bienveillant", "fidele", "spirituel"])
        self.assertEqual(self.profile.life_values, ["famille", "foi", "sincerite"])
        self.assertEqual(looking_for_ids(self.profile.looking_for), ["serieux", "familial", "croyant", "calme"])

    def test_update_rejects_empty_traits(self):
        from core.controllers.profile_controller import ProfileUpdateError, update_profile

        with self.assertRaises(ProfileUpdateError):
            update_profile(self.profile, {"personality_traits": []})

    def test_update_caps_looking_for_at_four(self):
        from core.controllers.profile_controller import update_profile
        from core.data.onboarding import looking_for_ids

        update_profile(
            self.profile,
            {"looking_for": ["serieux", "familial", "croyant", "calme", "ambitieux"]},
        )
        self.profile.refresh_from_db()
        self.assertEqual(looking_for_ids(self.profile.looking_for), ["serieux", "familial", "croyant", "calme"])


class MarriageProjectPromptTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.profile = make_profile("projet@test.com", Gender.MALE, "Omar")
        self.profile.user.set_password("Ludvanne12")
        self.profile.user.save()
        self.profile.onboarding_completed = True
        self.profile.photo_url = "https://example.com/p.jpg"
        self.profile.save(update_fields=["onboarding_completed", "photo_url", "updated_at"])

    def test_needs_prompt_when_empty(self):
        from core.controllers.profile_controller import needs_marriage_project

        self.assertTrue(needs_marriage_project(self.profile))

    def test_complete_when_all_fields_set(self):
        from core.controllers.profile_controller import needs_marriage_project, update_profile

        update_profile(
            self.profile,
            {
                "marriage_timeline": "under_1y",
                "union_type": "monogame",
                "children_wish": "yes",
                "partner_religion_importance": "same",
                "meet_place": "near",
            },
        )
        self.profile.refresh_from_db()
        self.assertFalse(needs_marriage_project(self.profile))

    def test_modal_on_explorer_when_incomplete(self):
        self.assertTrue(self.client.login(username=self.profile.user.username, password="Ludvanne12"))
        page = self.client.get("/explorer/")
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "projet-prompt-modal")
        self.assertContains(page, "Pour continuer, veuillez remplir votre projet")
        self.assertContains(page, "data-needs-projet")

    def test_profil_page_ok(self):
        self.assertTrue(self.client.login(username=self.profile.user.username, password="Ludvanne12"))
        page = self.client.get("/profil/")
        self.assertEqual(page.status_code, 200)

    def test_api_saves_marriage_project_as_json(self):
        self.assertTrue(self.client.login(username=self.profile.user.username, password="Ludvanne12"))
        response = self.client.post(
            "/api/profile/update/",
            data={
                "marriage_timeline": "under_1y",
                "union_type": "monogame",
                "children_wish": "yes",
                "partner_religion_importance": "some",
                "meet_place": "anywhere",
            },
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200, response.content)
        payload = response.json()
        self.assertTrue(payload["ok"])
        self.assertIn("member", payload)

    def test_no_modal_when_complete(self):
        from core.controllers.profile_controller import update_profile

        update_profile(
            self.profile,
            {
                "marriage_timeline": "1_2y",
                "union_type": "open",
                "children_wish": "maybe",
                "partner_religion_importance": "any",
                "meet_place": "anywhere",
            },
        )
        self.assertTrue(self.client.login(username=self.profile.user.username, password="Ludvanne12"))
        page = self.client.get("/explorer/")
        self.assertEqual(page.status_code, 200)
        self.assertNotContains(page, "projet-prompt-modal")

