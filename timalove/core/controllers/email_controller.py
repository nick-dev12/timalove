"""Emails transactionnels (SMTP Django ou Resend)."""

from __future__ import annotations

import json
import logging
import urllib.request

from django.conf import settings
from django.core.mail import send_mail

logger = logging.getLogger(__name__)


def _from_email() -> str:
    return getattr(settings, "DEFAULT_FROM_EMAIL", None) or settings.RESEND_FROM_EMAIL


def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
    text_body = text or "Voir la version HTML de ce message."
    if settings.RESEND_API_KEY:
        payload = {
            "from": _from_email(),
            "to": [to],
            "subject": subject,
            "html": html,
            "text": text_body,
        }
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
            with urllib.request.urlopen(req, timeout=20) as resp:
                ok = 200 <= resp.status < 300
                if not ok:
                    logger.warning("[email] Resend status=%s to=%s", resp.status, to)
                return ok
        except Exception as exc:
            logger.exception("[email] Resend échec to=%s: %s", to, exc)
            return False
    try:
        send_mail(
            subject,
            text_body,
            _from_email(),
            [to],
            html_message=html,
            fail_silently=False,
        )
        return True
    except Exception as exc:
        logger.exception("[email] SMTP échec to=%s: %s", to, exc)
        return False


def password_reset_email(to: str, reset_path: str) -> bool:
    base = (settings.SITE_URL or "").rstrip("/")
    link = f"{base}/reinitialiser-mot-de-passe/{reset_path}/"
    subject = "Réinitialisation de votre mot de passe — TimaLove"
    text = (
        "Bonjour,\n\n"
        "Vous avez demandé à réinitialiser votre mot de passe TimaLove.\n"
        f"Ouvrez ce lien (valide pour une durée limitée) :\n{link}\n\n"
        "Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.\n\n"
        "— L'équipe TimaLove"
    )
    html = f"""
    <div style="font-family:Arial,Helvetica,sans-serif;max-width:560px;margin:0 auto;color:#3D2024;">
      <h1 style="font-size:22px;color:#3D2024;">TimaLove</h1>
      <p>Bonjour,</p>
      <p>Vous avez demandé à réinitialiser votre mot de passe.</p>
      <p style="margin:28px 0;">
        <a href="{link}"
           style="display:inline-block;background:#E8637A;color:#fff;text-decoration:none;
                  padding:12px 22px;border-radius:999px;font-weight:600;">
          Choisir un nouveau mot de passe
        </a>
      </p>
      <p style="font-size:13px;color:#6B5A5E;">Ou copiez ce lien :<br>{link}</p>
      <p style="font-size:13px;color:#9B8A8E;">Si vous n'êtes pas à l'origine de cette demande, ignorez cet email.</p>
      <p style="margin-top:24px;">— L'équipe TimaLove</p>
    </div>
    """
    return send_email(to, subject, html, text=text)
