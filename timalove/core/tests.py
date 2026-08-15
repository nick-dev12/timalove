from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from datetime import date

from core.controllers import swipe_controller, message_controller, payment_controller
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


class PaymentFulfillTests(TestCase):
    def setUp(self):
        site_settings_controller.seed_defaults()
        self.a = make_profile("pay@test.com", Gender.MALE, "Pay")

    def test_checkout_and_fulfill(self):
        out = payment_controller.create_checkout(self.a, "premium_10d")
        self.assertTrue(out["ok"])
        ok, _ = payment_controller.fulfill_order(out["order_id"])
        self.assertTrue(ok)
        self.a.refresh_from_db()
        self.assertTrue(self.a.has_active_subscription)


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
