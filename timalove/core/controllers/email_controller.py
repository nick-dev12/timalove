"""Emails (Resend ou console Django)."""

from __future__ import annotations

import json
import urllib.request

from django.conf import settings
from django.core.mail import send_mail


def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
    if settings.RESEND_API_KEY:
        payload = {
            "from": settings.RESEND_FROM_EMAIL,
            "to": [to],
            "subject": subject,
            "html": html,
        }
        if text:
            payload["text"] = text
        req = urllib.request.Request(
            "https://api.resend.com/emails",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {settings.RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return 200 <= resp.status < 300
        except Exception:
            return False
    send_mail(subject, text or html, settings.RESEND_FROM_EMAIL, [to], html_message=html)
    return True


def password_reset_email(to: str, reset_path: str) -> bool:
    link = f"{settings.SITE_URL}/reinitialiser-mot-de-passe/{reset_path}/"
    html = f"<p>Réinitialisez votre mot de passe TimaLove :</p><p><a href='{link}'>{link}</a></p>"
    return send_email(to, "Réinitialisation mot de passe — TimaLove", html)
