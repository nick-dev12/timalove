"""Finances admin — transactions, remboursements, export comptable."""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.http import HttpResponse
from django.utils import timezone

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
    start, end = _period_bounds(period, date_from, date_to)
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)
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
    return {
        "id": tx.id,
        "id_short": str(tx.id).replace("-", "")[:8],
        "order_id": tx.order_id,
        "user_ref": anonymized_user_id(tx.user),
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
        Transaction.objects.select_related("user").order_by("-created_at"),
        status=status,
        product_type=product_type,
        period=period,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )
    paginator = Paginator(qs, per_page)
    return paginator.get_page(page)


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
        Transaction.objects.select_related("user").order_by("-created_at"),
        status=params.get("status") or None,
        product_type=params.get("product_type") or None,
        period=params.get("period") or None,
        date_from=params.get("date_from") or None,
        date_to=params.get("date_to") or None,
        search=(params.get("q") or "").strip(),
    )


def export_transactions_csv_response(params: dict, *, excel: bool = False) -> HttpResponse:
    qs = _export_queryset(params)
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";")
    writer.writerow(
        [
            "ID transaction",
            "Référence commande",
            "ID utilisateur",
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
        writer.writerow(
            [
                str(tx.id),
                tx.order_id,
                anonymized_user_id(tx.user),
                transaction_provider_label(tx),
                tx.amount,
                tx.currency or "XOF",
                transaction_product_label(tx),
                transaction_status_admin_label(tx.status),
                timezone.localtime(tx.created_at).strftime("%Y-%m-%d %H:%M"),
                timezone.localtime(tx.paid_at).strftime("%Y-%m-%d %H:%M") if tx.paid_at else "",
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
