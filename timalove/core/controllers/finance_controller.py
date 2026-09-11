"""Finances admin — transactions, remboursements, export comptable."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

from django.core.paginator import Paginator

from core.controllers.pagination_utils import safe_page
from django.db import transaction
from django.db.models import Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone

from core.controllers import naboopay_controller, naboopay_sync_controller
from core.models import Profile, Transaction
from core.models.choices import PaymentMethod, SubscriptionTier, TransactionStatus, TransactionType

ADMIN_STATUS_LABELS: dict[str, str] = {
    TransactionStatus.PENDING: "En attente",
    TransactionStatus.PAID: "Réussi",
    TransactionStatus.FAILED: "Échoué",
    TransactionStatus.REFUNDED: "Remboursé",
    TransactionStatus.DISPUTE: "Litige / Chargeback",
}

PRODUCT_TYPE_FILTERS: list[tuple[str, str]] = [
    ("subscription", "Abonnement"),
    ("boost", "Boost"),
    ("super_like", "Super-Like"),
    ("coaching", "Coaching"),
]

PERIOD_PRESETS: list[tuple[str, str]] = [
    ("7d", "7 derniers jours"),
    ("30d", "30 derniers jours"),
    ("90d", "90 derniers jours"),
    ("year", "Cette année"),
    ("all", "Toute la période"),
]

PROVIDER_LABELS: dict[str, str] = {
    PaymentMethod.STRIPE: "Stripe",
    PaymentMethod.APPLE_PAY: "Apple Pay",
    PaymentMethod.GOOGLE_PAY: "Google Pay",
    PaymentMethod.CB: "Stripe",
    PaymentMethod.WAVE: "Wave",
    PaymentMethod.ORANGE_MONEY: "Orange Money",
    "cinetpay": "CinetPay",
    "naboopay": "NabooPay",
    "mobile_money": "Mobile Money",
}


def _format_money(amount: int, currency: str = "XOF") -> str:
    formatted = f"{int(amount):,}".replace(",", "\u202f")
    if currency == "XOF":
        return f"{formatted} FCFA"
    return f"{formatted} {currency}"


def _parse_date(value: str | None):
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def _period_bounds(period: str | None, date_from: str | None, date_to: str | None):
    today = timezone.localdate()
    start = _parse_date(date_from)
    end = _parse_date(date_to)
    if start or end:
        return start, end
    if period == "7d":
        return today - timedelta(days=6), today
    if period == "30d":
        return today - timedelta(days=29), today
    if period == "90d":
        return today - timedelta(days=89), today
    if period == "year":
        return today.replace(month=1, day=1), today
    return None, None


def _apply_filters(qs, *, status=None, product_type=None, period=None, date_from=None, date_to=None, search=""):
    if status:
        qs = qs.filter(status=status)
    if product_type:
        qs = qs.filter(type=product_type)
    qs = qs.annotate(event_at=Coalesce("paid_at", "created_at"))
    start, end = _period_bounds(period, date_from, date_to)
    if start:
        qs = qs.filter(event_at__date__gte=start)
    if end:
        qs = qs.filter(event_at__date__lte=end)
    if search:
        qs = qs.filter(
            Q(order_id__icontains=search)
            | Q(naboo_transaction_id__icontains=search)
            | Q(user__first_name__icontains=search)
            | Q(user__last_name__icontains=search)
            | Q(user__email__icontains=search)
        )
    return qs


def anonymized_user_id(profile: Profile | None) -> str:
    if not profile:
        return "—"
    return f"#{str(profile.id).replace('-', '')[:8]}"


def transaction_provider_label(tx: Transaction) -> str:
    details = tx.payment_details or {}
    method = (details.get("payment_method") or tx.payment_method or "").strip().lower()
    provider = (details.get("provider") or "").strip().lower()

    if method in PROVIDER_LABELS:
        return PROVIDER_LABELS[method]
    if provider == "stripe":
        return "Stripe"
    if provider in {"apple", "apple_pay"}:
        return "Apple Pay"
    if provider in {"google", "google_pay"}:
        return "Google Pay"
    if provider in {"cinetpay", "naboopay"}:
        if method in {PaymentMethod.WAVE, "wave"}:
            return "Wave"
        if method in {PaymentMethod.ORANGE_MONEY, "orange_money"}:
            return "Orange Money"
        if method in {PaymentMethod.CB, "cb", "card"}:
            return "Stripe"
        return "NabooPay" if provider == "naboopay" else "CinetPay"
    if tx.payment_method:
        return tx.get_payment_method_display() or tx.payment_method
    return "—"


def transaction_product_label(tx: Transaction) -> str:
    if tx.type == TransactionType.SUBSCRIPTION:
        if tx.plan_tier:
            label = dict(SubscriptionTier.choices).get(tx.plan_tier, "")
            if label:
                return label
        return "Abonnement mensuel"
    if tx.type == TransactionType.BOOST:
        return "Boost"
    if tx.type == TransactionType.SUPER_LIKE:
        return "Super-Like"
    if tx.type == TransactionType.COACHING:
        return "Coaching"
    return tx.get_type_display() or tx.type


def transaction_status_admin_label(status: str) -> str:
    return ADMIN_STATUS_LABELS.get(status, status)


def transaction_row(tx: Transaction) -> dict:
    currency = tx.currency or "XOF"
    profile = tx.user
    user_name = "—"
    user_email = ""
    if profile:
        user_name = profile.display_name or f"{profile.first_name} {profile.last_name}".strip() or "Membre"
        user_email = profile.email or getattr(profile.user, "email", "") or ""
    return {
        "id": tx.id,
        "id_short": str(tx.id).replace("-", "")[:8],
        "order_id": tx.order_id,
        "user_ref": anonymized_user_id(tx.user),
        "user_name": user_name,
        "user_email": user_email,
        "provider": transaction_provider_label(tx),
        "amount": tx.amount,
        "amount_label": _format_money(tx.amount, currency),
        "currency": currency,
        "product": transaction_product_label(tx),
        "type": tx.type,
        "status": tx.status,
        "status_label": transaction_status_admin_label(tx.status),
        "created_at": tx.created_at,
        "paid_at": tx.paid_at,
        "refunded_at": tx.refunded_at,
        "can_refund": tx.status == TransactionStatus.PAID,
        "local_id": str(tx.id),
        "user_phone": profile.phone if profile else "",
        "source": "local",
    }


def finance_summary(*, status=None, product_type=None, period=None, date_from=None, date_to=None, search="") -> dict:
    base = _apply_filters(
        Transaction.objects.all(),
        status=status,
        product_type=product_type,
        period=period,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    paid_qs = base.filter(status=TransactionStatus.PAID)
    failed_qs = base.filter(status=TransactionStatus.FAILED)
    pending_qs = base.filter(status=TransactionStatus.PENDING)
    refunded_qs = base.filter(status=TransactionStatus.REFUNDED)
    dispute_qs = base.filter(status=TransactionStatus.DISPUTE)

    def _sum(qs):
        return int(qs.aggregate(total=Sum("amount"))["total"] or 0)

    total_amount = _sum(base)
    paid_amount = _sum(paid_qs)
    failed_amount = _sum(failed_qs)
    pending_amount = _sum(pending_qs)
    refunded_amount = _sum(refunded_qs)

    return {
        "total_amount": total_amount,
        "paid_amount": paid_amount,
        "failed_amount": failed_amount,
        "pending_amount": pending_amount,
        "refunded_amount": refunded_amount,
        "total_amount_label": _format_money(total_amount),
        "paid_amount_label": _format_money(paid_amount),
        "failed_amount_label": _format_money(failed_amount),
        "pending_amount_label": _format_money(pending_amount),
        "refunded_amount_label": _format_money(refunded_amount),
        "total_count": base.count(),
        "paid_count": paid_qs.count(),
        "failed_count": failed_qs.count(),
        "pending_count": pending_qs.count(),
        "refunded_count": refunded_qs.count(),
        "dispute_count": dispute_qs.count(),
        "channels": revenue_by_channel(
            status=status,
            product_type=product_type,
            period=period,
            date_from=date_from,
            date_to=date_to,
            search=search,
        ),
    }


def revenue_by_channel(**filters) -> dict:
    qs = _apply_filters(
        Transaction.objects.filter(status__in=[TransactionStatus.PAID, TransactionStatus.REFUNDED]),
        **filters,
    ).select_related("user")
    buckets: dict[str, int] = {}
    for tx in qs.iterator():
        label = transaction_provider_label(tx)
        buckets[label] = buckets.get(label, 0) + int(tx.amount or 0)
    if not buckets:
        return {"labels": [], "values": []}
    ordered = sorted(buckets.items(), key=lambda item: item[1], reverse=True)
    return {"labels": [label for label, _ in ordered], "values": [amount for _, amount in ordered]}


def list_transactions(
    *,
    status: str | None = None,
    product_type: str | None = None,
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str = "",
    page: int = 1,
    per_page: int = 30,
):
    qs = _apply_filters(
        Transaction.objects.select_related("user"),
        status=status,
        product_type=product_type,
        period=period,
        date_from=date_from,
        date_to=date_to,
        search=search,
    ).order_by("-event_at")
    paginator = Paginator(qs, per_page)
    return safe_page(paginator, page)


@transaction.atomic
def refund_transaction(transaction_id, admin: Profile | None, notes: str = "") -> Transaction:
    tx = Transaction.objects.select_for_update().get(pk=transaction_id)
    if tx.status != TransactionStatus.PAID:
        raise ValueError("Seuls les paiements réussis peuvent être remboursés.")
    tx.status = TransactionStatus.REFUNDED
    tx.refunded_at = timezone.now()
    details = dict(tx.payment_details or {})
    details["refund"] = {
        "at": tx.refunded_at.isoformat(),
        "by": str(admin.id) if admin else None,
        "notes": (notes or "").strip(),
    }
    tx.payment_details = details
    tx.save(update_fields=["status", "refunded_at", "payment_details", "updated_at"])
    return tx


def _export_queryset(params: dict):
    return _apply_filters(
        Transaction.objects.select_related("user"),
        status=params.get("status") or None,
        product_type=params.get("product_type") or None,
        period=params.get("period") or None,
        date_from=params.get("date_from") or None,
        date_to=params.get("date_to") or None,
        search=(params.get("q") or "").strip(),
    ).order_by("-event_at")


PRODUCT_TYPE_SEARCH: dict[str, str] = {
    "subscription": "TimaLove",
    "boost": "Boost",
    "super_like": "Super",
    "coaching": "Coaching",
}

ONE_SHOT_PRODUCT_KEYWORDS: tuple[str, ...] = ("boost", "coaching", "super-like", "super like")


class NabooPayFinancePage:
    """Pagination compatible templates admin (données NabooPay live)."""

    def __init__(self, rows: list[dict], *, page: int, per_page: int, total_count: int, total_pages: int):
        self.object_list = rows
        self.number = page
        self.paginator = type(
            "NabooPaginator",
            (),
            {"count": total_count, "num_pages": total_pages, "per_page": per_page},
        )()

    def __iter__(self):
        return iter(self.object_list)

    def __len__(self):
        return len(self.object_list)

    @property
    def has_next(self) -> bool:
        return self.number < self.paginator.num_pages

    @property
    def has_previous(self) -> bool:
        return self.number > 1

    def next_page_number(self) -> int:
        return self.number + 1

    def previous_page_number(self) -> int:
        return self.number - 1


def uses_naboopay_live() -> bool:
    return naboopay_controller.is_configured()


def _naboo_period_dates(period: str | None, date_from: str | None, date_to: str | None) -> tuple[str | None, str | None]:
    start, end = _period_bounds(period, date_from, date_to)
    start_iso = start.isoformat() if start else None
    end_iso = end.isoformat() if end else None
    return start_iso, end_iso


def _parse_naboo_datetime(value: str | None):
    if not value or value.startswith("0001-"):
        return None
    from django.utils.dateparse import parse_datetime

    parsed = parse_datetime(value)
    if not parsed:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.utc)
    return parsed


def _naboo_product_label(products: list | None) -> str:
    if not products:
        return "—"
    first = products[0] if isinstance(products[0], dict) else {}
    return (first.get("name") or first.get("description") or "—").strip() or "—"


def _naboo_provider_label(tx: dict) -> str:
    method = (tx.get("selected_payment_method") or "").strip().lower()
    if method in {PaymentMethod.WAVE, "wave"}:
        return "Wave"
    if method in {PaymentMethod.ORANGE_MONEY, "orange_money"}:
        return "Orange Money"
    if method in {PaymentMethod.CB, "cb", "card"}:
        return "Stripe"
    return "NabooPay"


def _map_naboo_status(raw: str | None) -> str:
    key = (raw or "").strip().lower()
    return naboopay_controller.NABOO_TO_ADMIN_STATUS.get(key, TransactionStatus.PENDING)


def _local_tx_ids_by_naboo_order(order_ids: list[str]) -> dict[str, str]:
    if not order_ids:
        return {}
    mapping: dict[str, str] = {}
    qs = Transaction.objects.filter(status=TransactionStatus.PAID).filter(
        Q(payment_details__naboo_order_id__in=order_ids) | Q(naboo_transaction_id__in=order_ids)
    ).only("id", "payment_details", "naboo_transaction_id")
    for tx in qs:
        details = tx.payment_details or {}
        for naboo_id in {str(details.get("naboo_order_id") or ""), str(tx.naboo_transaction_id or "")}:
            if naboo_id in order_ids:
                mapping[naboo_id] = str(tx.id)
    return mapping


def naboopay_transaction_row(tx: dict) -> dict:
    customer = tx.get("customer") or {}
    first = (customer.get("first_name") or "").strip()
    last = (customer.get("last_name") or "").strip()
    phone = (customer.get("phone") or "").strip()
    user_name = f"{first} {last}".strip() or "Client NabooPay"
    status = _map_naboo_status(tx.get("transaction_status"))
    paid_at = _parse_naboo_datetime(tx.get("paid_at"))
    created_at = _parse_naboo_datetime(tx.get("created_at")) or timezone.now()
    event_at = paid_at or created_at
    order_id = str(tx.get("order_id") or "")
    amount = int(tx.get("amount") or 0)
    currency = (tx.get("currency") or "XOF").upper()
    return {
        "id": order_id,
        "id_short": order_id.replace("-", "")[:8],
        "order_id": order_id,
        "user_ref": phone or "—",
        "user_name": user_name,
        "user_email": "",
        "user_phone": phone,
        "provider": _naboo_provider_label(tx),
        "amount": amount,
        "amount_label": _format_money(amount, currency),
        "currency": currency,
        "product": _naboo_product_label(tx.get("products")),
        "status": status,
        "status_label": transaction_status_admin_label(status),
        "created_at": created_at,
        "paid_at": paid_at,
        "event_at": event_at,
        "can_refund": status == TransactionStatus.PAID,
        "source": "naboopay",
    }


def _cached_naboopay_rows(
    *,
    status: str | None = None,
    product_type: str | None = None,
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str = "",
) -> tuple[list[dict], dict, str | None]:
    rows, meta, error = naboopay_sync_controller.get_rows()
    if error and not rows:
        return [], meta, error
    filtered = naboopay_sync_controller.filter_rows(
        rows,
        status=status,
        product_type=product_type,
        period=period,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    return filtered, meta, error


def _attach_local_refund_flags(rows: list[dict]) -> list[dict]:
    order_ids = [row["order_id"] for row in rows if row.get("order_id")]
    local_ids = _local_tx_ids_by_naboo_order(order_ids)
    enriched = []
    for row in rows:
        payload = dict(row)
        local_id = local_ids.get(payload["order_id"])
        payload["local_id"] = local_id
        payload["can_refund"] = bool(local_id)
        enriched.append(payload)
    return enriched


def list_naboopay_transactions(
    *,
    status: str | None = None,
    product_type: str | None = None,
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str = "",
    page: int = 1,
    per_page: int = 30,
) -> tuple[NabooPayFinancePage | None, str | None]:
    filtered, _meta, error = _cached_naboopay_rows(
        status=status,
        product_type=product_type,
        period=period,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    if error and not filtered:
        return None, error

    safe_page = max(int(page or 1), 1)
    safe_per_page = max(int(per_page or 30), 1)
    total_count = len(filtered)
    total_pages = max(1, (total_count + safe_per_page - 1) // safe_per_page)
    start = (safe_page - 1) * safe_per_page
    page_rows = _attach_local_refund_flags(filtered[start : start + safe_per_page])
    page_obj = NabooPayFinancePage(
        page_rows,
        page=safe_page,
        per_page=safe_per_page,
        total_count=total_count,
        total_pages=total_pages,
    )
    return page_obj, error


def naboopay_finance_summary(
    *,
    status: str | None = None,
    product_type: str | None = None,
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str = "",
) -> tuple[dict, str | None]:
    rows, _meta, error = _cached_naboopay_rows(
        status=status,
        product_type=product_type,
        period=period,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    if error and not rows:
        return {}, error

    def _sum_status(key: str) -> tuple[int, int]:
        subset = [row for row in rows if row["status"] == key]
        return len(subset), sum(int(row["amount"] or 0) for row in subset)

    paid_count, paid_amount = _sum_status(TransactionStatus.PAID)
    failed_count, failed_amount = _sum_status(TransactionStatus.FAILED)
    pending_count, pending_amount = _sum_status(TransactionStatus.PENDING)
    refunded_count, refunded_amount = _sum_status(TransactionStatus.REFUNDED)
    dispute_count, _ = _sum_status(TransactionStatus.DISPUTE)
    total_amount = sum(int(row["amount"] or 0) for row in rows)

    channels: dict[str, int] = {}
    for row in rows:
        if row["status"] not in {TransactionStatus.PAID, TransactionStatus.REFUNDED}:
            continue
        label = row["provider"]
        channels[label] = channels.get(label, 0) + int(row["amount"] or 0)
    channel_ordered = sorted(channels.items(), key=lambda item: item[1], reverse=True)

    summary = {
        "total_amount": total_amount,
        "paid_amount": paid_amount,
        "failed_amount": failed_amount,
        "pending_amount": pending_amount,
        "refunded_amount": refunded_amount,
        "total_amount_label": _format_money(total_amount),
        "paid_amount_label": _format_money(paid_amount),
        "failed_amount_label": _format_money(failed_amount),
        "pending_amount_label": _format_money(pending_amount),
        "refunded_amount_label": _format_money(refunded_amount),
        "total_count": len(rows),
        "paid_count": paid_count,
        "failed_count": failed_count,
        "pending_count": pending_count,
        "refunded_count": refunded_count,
        "dispute_count": dispute_count,
        "channels": {
            "labels": [label for label, _ in channel_ordered],
            "values": [amount for _, amount in channel_ordered],
        },
        "source": "naboopay",
    }
    return summary, error


def _naboo_product_bucket(product: str) -> str:
    lower = (product or "").lower()
    if any(keyword in lower for keyword in ONE_SHOT_PRODUCT_KEYWORDS):
        return "one_shot"
    return "subscription"


def _naboopay_paid_rows_between(start: datetime, end: datetime) -> list[dict]:
    rows, _meta, _error = naboopay_sync_controller.get_rows()
    paid_rows: list[dict] = []
    for row in rows:
        if row["status"] != TransactionStatus.PAID:
            continue
        event = row["paid_at"] or row["created_at"]
        if event and start <= event <= end:
            paid_rows.append(row)
    return paid_rows


def naboopay_sync_public_meta() -> dict:
    if not uses_naboopay_live():
        return {}
    return naboopay_sync_controller.public_meta(naboopay_sync_controller.last_meta())


def naboopay_revenue_sum(start: datetime, end: datetime) -> int:
    if not uses_naboopay_live():
        return 0
    return sum(int(row["amount"] or 0) for row in _naboopay_paid_rows_between(start, end))


def naboopay_daily_revenue_series(iso_labels: list[str]) -> dict[str, list[int]]:
    if not uses_naboopay_live() or not iso_labels:
        return {"subscription": [0] * len(iso_labels), "one_shot": [0] * len(iso_labels)}

    start_day = timezone.localdate() - timedelta(days=len(iso_labels) - 1)
    end_day = timezone.localdate()
    start_dt = timezone.make_aware(datetime.combine(start_day, datetime.min.time()))
    end_dt = timezone.make_aware(datetime.combine(end_day, datetime.max.time()))
    subscription_by_day = dict.fromkeys(iso_labels, 0)
    one_shot_by_day = dict.fromkeys(iso_labels, 0)

    for row in _naboopay_paid_rows_between(start_dt, end_dt):
        day_key = timezone.localtime(row["paid_at"] or row["created_at"]).date().isoformat()
        if day_key not in subscription_by_day:
            continue
        amount = int(row["amount"] or 0)
        if _naboo_product_bucket(row["product"]) == "one_shot":
            one_shot_by_day[day_key] += amount
        else:
            subscription_by_day[day_key] += amount

    return {
        "subscription": [subscription_by_day[label] for label in iso_labels],
        "one_shot": [one_shot_by_day[label] for label in iso_labels],
    }


def export_naboopay_csv_response(params: dict, *, excel: bool = False) -> HttpResponse | tuple[None, str]:
    rows, _meta, error = _cached_naboopay_rows(
        status=params.get("status") or None,
        product_type=params.get("product_type") or None,
        period=params.get("period") or None,
        date_from=params.get("date_from") or None,
        date_to=params.get("date_to") or None,
        search=(params.get("q") or "").strip(),
    )
    if error and not rows:
        return None, error

    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        [
            "ID transaction NabooPay",
            "Client",
            "Téléphone",
            "Prestataire",
            "Montant",
            "Devise",
            "Produit",
            "Statut",
            "Date création",
            "Date paiement",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["order_id"],
                row["user_name"],
                row.get("user_phone") or "",
                row["provider"],
                row["amount"],
                row["currency"],
                row["product"],
                row["status_label"],
                timezone.localtime(row["created_at"]).strftime("%Y-%m-%d %H:%M"),
                timezone.localtime(row["paid_at"]).strftime("%Y-%m-%d %H:%M") if row["paid_at"] else "",
            ]
        )

    content = "\ufeff" + buffer.getvalue()
    filename = f"timalove-naboopay-{timezone.localdate().isoformat()}.{'xls' if excel else 'csv'}"
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    if excel:
        response["Content-Type"] = "application/vnd.ms-excel; charset=utf-8"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response, None


def export_transactions_csv_response(params: dict, *, excel: bool = False) -> HttpResponse:
    if uses_naboopay_live():
        response, error = export_naboopay_csv_response(params, excel=excel)
        if response:
            return response
        raise ValueError(error or "Export NabooPay impossible.")

    qs = _export_queryset(params)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        [
            "ID transaction",
            "Référence commande",
            "Utilisateur",
            "Email",
            "Prestataire",
            "Montant",
            "Devise",
            "Produit",
            "Statut",
            "Date création",
            "Date paiement",
            "Date remboursement",
        ]
    )
    for tx in qs.iterator():
        profile = tx.user
        user_name = ""
        user_email = ""
        if profile:
            user_name = profile.display_name or f"{profile.first_name} {profile.last_name}".strip()
            user_email = profile.email or getattr(profile.user, "email", "") or ""
        paid_at = tx.paid_at or tx.created_at
        writer.writerow(
            [
                str(tx.id),
                tx.order_id,
                user_name,
                user_email,
                transaction_provider_label(tx),
                tx.amount,
                tx.currency or "XOF",
                transaction_product_label(tx),
                transaction_status_admin_label(tx.status),
                timezone.localtime(tx.created_at).strftime("%Y-%m-%d %H:%M"),
                timezone.localtime(paid_at).strftime("%Y-%m-%d %H:%M") if tx.paid_at else "",
                timezone.localtime(tx.refunded_at).strftime("%Y-%m-%d %H:%M") if tx.refunded_at else "",
            ]
        )

    content = "\ufeff" + buffer.getvalue()
    filename = f"timalove-finances-{timezone.localdate().isoformat()}.{'xls' if excel else 'csv'}"
    response = HttpResponse(content, content_type="text/csv; charset=utf-8")
    if excel:
        response["Content-Type"] = "application/vnd.ms-excel; charset=utf-8"
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
