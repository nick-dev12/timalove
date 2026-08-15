"""Initialisation unique du SDK Firebase Admin."""

from __future__ import annotations

import logging

from django.conf import settings

logger = logging.getLogger(__name__)

_app = None


def get_firebase_app():
    global _app
    if _app is not None:
        return _app

    import firebase_admin
    from firebase_admin import credentials

    try:
        _app = firebase_admin.get_app()
        return _app
    except ValueError:
        pass

    cred_path = settings.FIREBASE_CREDENTIALS_PATH
    if not cred_path.exists():
        logger.error("[firebase] Fichier credentials introuvable : %s", cred_path)
        return None

    _app = firebase_admin.initialize_app(credentials.Certificate(str(cred_path)))
    return _app
