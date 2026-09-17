"""Reset super admin VPS — mot de passe + rôle + suppression 2FA bloquante."""
import os
import sys

import django

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TIMALOVE = os.path.join(BASE, "timalove")
sys.path.insert(0, TIMALOVE)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
os.chdir(TIMALOVE)
django.setup()

from django.contrib.auth import authenticate, get_user_model

from core.controllers import two_factor_controller
from core.models.choices import UserRole

User = get_user_model()
EMAIL = "admin@timalove.local"
PASSWORD = "AdminTimaLove2026!"


def main() -> None:
    two_factor_controller.disable_admin_2fa_globally()
    user = User.objects.filter(email__iexact=EMAIL).select_related("profile").first()
    if not user:
        print("MISSING_USER")
        return

    profile = getattr(user, "profile", None)
    print("email", user.email)
    print("username", user.username)
    print("active_before", user.is_active)
    print("role_before", getattr(profile, "role", None))

    user.is_active = True
    user.is_staff = True
    user.is_superuser = True
    user.set_password(PASSWORD)
    user.save(update_fields=["password", "is_active", "is_staff", "is_superuser"])

    if profile:
        profile.role = UserRole.SUPER_ADMIN
        profile.registration_status = "approved"
        profile.banned_at = None
        profile.save(update_fields=["role", "registration_status", "banned_at", "updated_at"])
    auth = authenticate(username=user.username, password=PASSWORD)
    if auth is None:
        auth = authenticate(username=user.email, password=PASSWORD)
    print("auth_ok", bool(auth))
    print("done")


if __name__ == "__main__":
    main()
