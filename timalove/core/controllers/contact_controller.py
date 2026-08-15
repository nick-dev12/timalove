"""Formulaire de contact public."""

from __future__ import annotations

import re

from core.controllers import email_controller, site_settings_controller

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def submit(data: dict) -> tuple[bool, str]:
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip()
    message = (data.get("message") or "").strip()

    if len(name) < 2:
        return False, "Indiquez votre nom complet."
    if not _EMAIL_RE.match(email):
        return False, "Indiquez une adresse email valide."
    if len(message) < 8:
        return False, "Écrivez un message un peu plus détaillé."

    to = site_settings_controller.get("contact_email", "timaloveagence@gmail.com")
    safe_name = name.replace("<", "").replace(">", "")
    safe_message = message.replace("<", "").replace(">", "")
    html = (
        f"<p><strong>Nom :</strong> {safe_name}</p>"
        f"<p><strong>Email :</strong> {email}</p>"
        f"<p><strong>Message :</strong></p><p>{safe_message.replace(chr(10), '<br>')}</p>"
    )
    text = f"Nom : {name}\nEmail : {email}\n\n{message}"
    try:
        sent = email_controller.send_email(
            to,
            f"Message TimaLove — {safe_name}",
            html,
            text,
        )
    except Exception:
        return False, "L'envoi a échoué. Réessayez ou écrivez-nous par WhatsApp."
    if not sent:
        return False, "L'envoi a échoué. Réessayez ou écrivez-nous par WhatsApp."
    return True, "Votre message a bien été envoyé. Nous vous répondons sous 24 h."
