"""Adaptateur NabooPay Checkout v2 (https://platform.naboopay.com)."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings

logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "https://api.naboopay.com"

ACCEPTED_STATUSES = frozenset({"paid", "completed", "paid_and_blocked"})

NETWORK_USER_MESSAGE = (
    "Le service de paiement NabooPay est injoignable pour le moment. Réessayez dans quelques minutes."
)


def is_configured() -> bool:
    return bool((getattr(settings, "NABOOPAY_API_KEY", "") or "").strip())


def webhook_secret_configured() -> bool:
    return bool((getattr(settings, "NABOOPAY_WEBHOOK_SECRET", "") or "").strip())


def base_url() -> str:
    return (getattr(settings, "NABOOPAY_BASE_URL", "") or DEFAULT_BASE_URL).rstrip("/")


def currency() -> str:
    return (getattr(settings, "NABOOPAY_CURRENCY", "XOF") or "XOF").upper()


def methods() -> list[str]:
    raw = getattr(settings, "NABOOPAY_METHODS", "wave,orange_money") or "wave,orange_money"
    items = [part.strip().lower() for part in str(raw).split(",") if part.strip()]
    return items or ["wave", "orange_money"]


def fees_customer_side() -> bool:
    return bool(getattr(settings, "NABOOPAY_FEES_CUSTOMER_SIDE", False))


def normalize_amount(amount: int) -> int:
    return max(int(amount or 0), 0)


def _digits(value: str | None) -> str:
    return re.sub(r"\D+", "", value or "")


def format_phone(phone: str | None) -> str:
    digits = _digits(phone)
    if digits.startswith("221") and len(digits) >= 12:
        return f"+{digits}"
    if len(digits) == 9:
        return f"+221{digits}"
    if digits.startswith("0") and len(digits) == 10:
        return f"+221{digits[1:]}"
    if digits:
        return f"+{digits}" if not str(phone or "").startswith("+") else f"+{digits}"
    return "+221000000000"


def is_network_failure(data: dict | None) -> bool:
    payload = data or {}
    if str(payload.get("code") or "") == "network":
        return True
    blob = f"{payload.get('message', '')} {payload.get('error', '')}".lower()
    tokens = ("getaddrinfo", "urlopen", "timed out", "timeout", "name or service not known", "failed to resolve")
    return any(token in blob for token in tokens)


def _api_key() -> str:
    return (getattr(settings, "NABOOPAY_API_KEY", "") or "").strip()


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {_api_key()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _request(method: str, path: str, payload: dict | None = None, *, timeout: int = 25) -> dict:
    url = f"{base_url()}{path}"
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=_headers(), method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else {}
        except json.JSONDecodeError:
            parsed = {"error": raw or str(exc)}
        if isinstance(parsed, dict):
            parsed.setdefault("http_status", exc.code)
        return parsed if isinstance(parsed, dict) else {"error": raw or str(exc), "http_status": exc.code}
    except Exception as exc:
        logger.warning("[naboopay] réseau : %s", exc)
        return {"code": "network", "error": NETWORK_USER_MESSAGE, "detail": str(exc)}


def customer_payload(profile, extra: dict | None = None) -> dict:
    extra = extra or {}
    first = (getattr(profile, "first_name", None) or extra.get("first_name") or "Membre").strip()
    last = (getattr(profile, "last_name", None) or extra.get("last_name") or "TimaLove").strip()
    phone = format_phone(getattr(profile, "phone", None) or extra.get("phone"))
    return {
        "first_name": first[:50],
        "last_name": last[:50],
        "phone": phone,
    }


def verify_signature_raw(raw_body: bytes, signature: str | None) -> bool:
    secret = (getattr(settings, "NABOOPAY_WEBHOOK_SECRET", "") or "").strip()
    token = (signature or "").strip()
    if not secret or not token or not raw_body:
        return False
    expected = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, token)


def verify_signature_payload(payload: dict, signature: str | None) -> bool:
    compact = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return verify_signature_raw(compact, signature)


def initialize(
    *,
    amount: int,
    description: str,
    success_url: str,
    error_url: str,
    profile=None,
    extra: dict | None = None,
) -> dict:
    if not is_configured():
        return {"ok": False, "error": "NabooPay n’est pas configuré."}

    charged = normalize_amount(amount)
    if charged <= 0:
        return {"ok": False, "error": "Montant invalide."}

    payload = {
        "method_of_payment": methods(),
        "products": [
            {
                "name": (description or "TimaLove")[:100],
                "price": charged,
                "quantity": 1,
                "description": (description or "TimaLove")[:200],
            }
        ],
        "customer": customer_payload(profile, extra),
        "success_url": success_url,
        "error_url": error_url,
        "fees_customer_side": fees_customer_side(),
        "is_escrow": False,
        "is_merchant": False,
    }
    data = _request("POST", "/api/v2/transactions", payload)
    if is_network_failure(data):
        logger.warning("[naboopay] init injoignable : %s", data.get("detail") or data.get("error"))
        return {"ok": False, "error": NETWORK_USER_MESSAGE, "network": True, "raw": data}

    checkout_url = data.get("checkout_url") or ""
    order_id = data.get("order_id") or ""
    if checkout_url and order_id:
        return {
            "ok": True,
            "checkout_url": checkout_url,
            "payment_url": checkout_url,
            "order_id": order_id,
            "amount": int(data.get("amount") or charged),
            "transaction_status": data.get("transaction_status") or "pending",
            "raw": data,
        }

    message = data.get("error") or data.get("message") or "Impossible d’ouvrir NabooPay."
    logger.warning("[naboopay] init refusée : %s", message)
    return {"ok": False, "error": str(message), "raw": data}


def check(naboo_order_id: str) -> dict:
    if not is_configured():
        return {"ok": False, "accepted": False, "error": "NabooPay n’est pas configuré."}
    if not naboo_order_id:
        return {"ok": False, "accepted": False, "error": "Identifiant NabooPay manquant."}

    data = _request("GET", f"/api/v2/transactions/{urllib.parse.quote(naboo_order_id, safe='')}")
    if is_network_failure(data):
        return {
            "ok": False,
            "accepted": False,
            "error": NETWORK_USER_MESSAGE,
            "network": True,
            "raw": data,
        }

    status = str(data.get("transaction_status") or "").lower()
    accepted = status in ACCEPTED_STATUSES
    payment_method = data.get("selected_payment_method") or ""
    if not payment_method and isinstance(data.get("method_of_payment"), list) and data["method_of_payment"]:
        payment_method = data["method_of_payment"][0]

    if data.get("error") and not status:
        return {
            "ok": False,
            "accepted": False,
            "status": status,
            "error": data.get("error"),
            "raw": data,
        }

    return {
        "ok": True,
        "accepted": accepted,
        "status": status,
        "operator_id": naboo_order_id,
        "payment_method": payment_method,
        "amount": data.get("amount"),
        "raw": data,
        "error": None if accepted else (data.get("error") or status or "Paiement non confirmé."),
        "network": False,
    }
