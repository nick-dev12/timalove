"""TOTP 2FA pour l'équipe admin."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time

from django.utils import timezone

from core.models import AdminTwoFactor, Profile

DEFAULT_ADMIN_SECURITY = {
    "require_2fa": False,
}


def get_admin_security_settings() -> dict:
    from core.controllers import site_settings_controller

    stored = site_settings_controller.get("admin_security") or {}
    merged = dict(DEFAULT_ADMIN_SECURITY)
    if isinstance(stored, dict):
        merged.update(stored)
    merged["require_2fa"] = bool(merged.get("require_2fa", True))
    return merged


def save_admin_security_settings(data: dict) -> dict:
    from core.controllers import site_settings_controller

    current = get_admin_security_settings()
    if "require_2fa" in data:
        current["require_2fa"] = bool(data["require_2fa"])
    site_settings_controller.set_value("admin_security", current)
    return current


def _generate_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    padded = secret.upper() + "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(padded)


def totp_at(secret: str, for_time: int | None = None) -> str:
    counter = int((for_time if for_time is not None else time.time()) // 30)
    key = _decode_secret(secret)
    digest = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % 1_000_000).zfill(6)


def verify_totp(secret: str, code: str, *, window: int = 1) -> bool:
    code = (code or "").strip().replace(" ", "")
    if not code.isdigit() or len(code) != 6:
        return False
    now = int(time.time())
    for offset in range(-window, window + 1):
        if totp_at(secret, now + offset * 30) == code:
            return True
    return False


def get_or_create_two_factor(profile: Profile) -> AdminTwoFactor:
    record, created = AdminTwoFactor.objects.get_or_create(
        profile=profile,
        defaults={"secret": _generate_secret()},
    )
    if created or not record.secret:
        record.secret = _generate_secret()
        record.save(update_fields=["secret", "updated_at"])
    return record


def provisioning_uri(profile: Profile, secret: str) -> str:
    label = (profile.email or profile.user.email or "admin").replace(":", "")
    issuer = "TimaLove Admin"
    return f"otpauth://totp/{issuer}:{label}?secret={secret}&issuer={issuer}&digits=6"


def enable_two_factor(profile: Profile, code: str) -> AdminTwoFactor:
    record = get_or_create_two_factor(profile)
    if not verify_totp(record.secret, code):
        raise ValueError("Code 2FA invalide.")
    record.is_enabled = True
    record.enabled_at = timezone.now()
    if not record.backup_codes:
        record.backup_codes = [secrets.token_hex(4) for _ in range(8)]
    record.save(update_fields=["is_enabled", "enabled_at", "backup_codes", "updated_at"])
    return record


def verify_login_code(profile: Profile, code: str) -> bool:
    record = AdminTwoFactor.objects.filter(profile=profile, is_enabled=True).first()
    if not record:
        return False
    code = (code or "").strip().replace(" ", "")
    if code in (record.backup_codes or []):
        record.backup_codes = [c for c in record.backup_codes if c != code]
        record.save(update_fields=["backup_codes", "updated_at"])
        return True
    return verify_totp(record.secret, code)


def two_factor_status(profile: Profile) -> dict:
    record = AdminTwoFactor.objects.filter(profile=profile).first()
    settings = get_admin_security_settings()
    return {
        "required": settings.get("require_2fa", True),
        "enabled": bool(record and record.is_enabled),
        "has_pending_setup": bool(record and not record.is_enabled),
        "backup_codes_remaining": len(record.backup_codes) if record else 0,
    }


def must_verify_2fa(profile: Profile, session: dict) -> bool:
    if not profile.is_staff_member:
        return False
    if session.get("admin_2fa_verified"):
        return False
    settings = get_admin_security_settings()
    if not settings.get("require_2fa", True):
        return False
    status = two_factor_status(profile)
    return status["enabled"]


def must_setup_2fa(profile: Profile, session: dict) -> bool:
    if not profile.is_staff_member:
        return False
    if session.get("admin_2fa_verified"):
        return False
    settings = get_admin_security_settings()
    if not settings.get("require_2fa", True):
        return False
    status = two_factor_status(profile)
    return not status["enabled"]
