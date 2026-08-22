"""Adaptateur CinetPay Checkout v2 (sans SDK)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import urllib.error
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api-checkout.cinetpay.com/v2"

HMAC_FIELDS = (
    "cpm_site_id",
    "cpm_trans_id",
    "cpm_trans_date",
    "cpm_amount",
    "cpm_currency",
    "signature",
    "payment_method",
    "cel_phone_num",
    "cpm_phone_prefixe",
    "cpm_language",
    "cpm_version",
    "cpm_payment_config",
    "cpm_page_action",
    "cpm_custom",
    "cpm_designation",
    "cpm_error_message",
)

COUNTRY_ISO = {
    "sénégal": "SN",
    "senegal": "SN",
    "côte d'ivoire": "CI",
    "cote d'ivoire": "CI",
    "cote divoire": "CI",
    "ivory coast": "CI",
    "mali": "ML",
    "burkina faso": "BF",
    "togo": "TG",
    "bénin": "BJ",
    "benin": "BJ",
    "guinée": "GN",
    "guinee": "GN",
    "cameroun": "CM",
    "congo": "CG",
    "rdc": "CD",
    "france": "FR",
}


def is_configured() -> bool:
    return bool(getattr(settings, "CINETPAY_APIKEY", "") and getattr(settings, "CINETPAY_SITE_ID", ""))


def base_url() -> str:
    return (getattr(settings, "CINETPAY_BASE_URL", "") or DEFAULT_BASE_URL).rstrip("/")


def init_url() -> str:
    return f"{base_url()}/payment"


def check_url() -> str:
    return f"{base_url()}/payment/check"


def currency() -> str:
    return (getattr(settings, "CINETPAY_CURRENCY", "XOF") or "XOF").upper()


def channels() -> str:
    return getattr(settings, "CINETPAY_CHANNELS", "ALL") or "ALL"


def normalize_amount(amount: int) -> int:
    value = max(int(amount or 0), 0)
    if currency() in {"XOF", "XAF"}:
        rest = value % 5
        if rest:
            value += 5 - rest
    return value


def country_iso(name: str | None) -> str:
    key = (name or "").strip().lower()
    return COUNTRY_ISO.get(key, "SN")


def _digits(value: str | None) -> str:
    return re.sub(r"\D+", "", value or "")


NETWORK_USER_MESSAGE = (
    "Le service de paiement CinetPay est injoignable pour le moment. Réessayez dans quelques minutes."
)


def is_network_failure(data: dict | None) -> bool:
    payload = data or {}
    if str(payload.get("code") or "") == "network":
        return True
    blob = f"{payload.get('message', '')} {payload.get('error', '')} {payload.get('description', '')}".lower()
    tokens = ("getaddrinfo", "urlopen", "timed out", "timeout", "name or service not known", "failed to resolve")
    return any(token in blob for token in tokens)


def _post_json(url: str, payload: dict, timeout: int = 20) -> dict:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            data = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            data = {"message": raw or str(exc)}
        data.setdefault("code", str(exc.code))
        return data
    except Exception as exc:
        logger.warning("[cinetpay] réseau : %s", exc)
        return {"code": "network", "message": NETWORK_USER_MESSAGE, "detail": str(exc)}


def hmac_matches(payload: dict, x_token: str | None) -> bool:
    secret = (getattr(settings, "CINETPAY_SECRET_KEY", "") or "").strip()
    token = (x_token or "").strip()
    if not secret or not token:
        return False
    concatenated = "".join(str(payload.get(field, "") or "") for field in HMAC_FIELDS)
    expected = hmac.new(secret.encode("utf-8"), concatenated.encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, token)


def customer_payload(profile, extra: dict | None = None) -> dict:
    extra = extra or {}
    first = (getattr(profile, "first_name", None) or extra.get("first_name") or "Membre").strip()
    last = (getattr(profile, "last_name", None) or extra.get("last_name") or "TimaLove").strip()
    email = (getattr(profile, "email", None) or extra.get("email") or "").strip()
    phone = _digits(getattr(profile, "phone", None) or extra.get("phone") or "")
    city = (getattr(profile, "city", None) or extra.get("city") or "Dakar").strip() or "Dakar"
    country = country_iso(getattr(profile, "residence_country", None) or getattr(profile, "country", None))
    return {
        "customer_id": str(getattr(profile, "id", "") or extra.get("customer_id") or "guest"),
        "customer_name": last[:50],
        "customer_surname": first[:50],
        "customer_email": email or "paiement@mytimalove.com",
        "customer_phone_number": phone or "221000000000",
        "customer_address": city[:100],
        "customer_city": city[:50],
        "customer_country": country,
        "customer_state": country,
        "customer_zip_code": "00000",
    }


def initialize(*, transaction_id: str, amount: int, description: str, notify_url: str, return_url: str, profile=None, extra: dict | None = None) -> dict:
    if not is_configured():
        return {"ok": False, "error": "CinetPay n’est pas configuré."}
    charged = normalize_amount(amount)
    payload = {
        "apikey": settings.CINETPAY_APIKEY,
        "site_id": settings.CINETPAY_SITE_ID,
        "transaction_id": transaction_id,
        "amount": charged,
        "currency": currency(),
        "description": (description or "TimaLove")[:100],
        "notify_url": notify_url,
        "return_url": return_url,
        "channels": channels(),
        "lang": "fr",
        "metadata": transaction_id,
        **customer_payload(profile, extra),
    }
    data = _post_json(init_url(), payload)
    code = str(data.get("code") or "")
    inner = data.get("data") or {}
    payment_url = inner.get("payment_url") or ""
    payment_token = inner.get("payment_token") or ""
    if code == "201" and payment_url:
        return {
            "ok": True,
            "payment_url": payment_url,
            "payment_token": payment_token,
            "amount": charged,
            "raw": data,
        }
    if is_network_failure(data):
        logger.warning("[cinetpay] init injoignable : %s", data.get("detail") or data.get("message"))
        return {"ok": False, "error": NETWORK_USER_MESSAGE, "network": True, "raw": data}
    message = data.get("description") or data.get("message") or "Impossible d’ouvrir CinetPay."
    logger.warning("[cinetpay] init refusée (%s) : %s", code, message)
    return {"ok": False, "error": str(message), "raw": data}


def check(transaction_id: str) -> dict:
    if not is_configured():
        return {"ok": False, "accepted": False, "error": "CinetPay n’est pas configuré."}
    data = _post_json(
        check_url(),
        {
            "apikey": settings.CINETPAY_APIKEY,
            "site_id": settings.CINETPAY_SITE_ID,
            "transaction_id": transaction_id,
        },
    )
    code = str(data.get("code") or "")
    inner = data.get("data") or {}
    status = str(inner.get("status") or "").upper()
    accepted = code == "00" and status == "ACCEPTED"
    return {
        "ok": code == "00",
        "accepted": accepted,
        "status": status or code,
        "operator_id": inner.get("operator_id") or "",
        "payment_method": inner.get("payment_method") or "",
        "amount": inner.get("amount"),
        "raw": data,
        "error": None
        if accepted
        else (
            NETWORK_USER_MESSAGE
            if is_network_failure(data)
            else (data.get("description") or data.get("message") or status or "Paiement non confirmé.")
        ),
        "network": is_network_failure(data),
    }
