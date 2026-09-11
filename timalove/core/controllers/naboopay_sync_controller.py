"""Cache NabooPay admin — sync complète au cold start, incrémentale ensuite."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from django.core.cache import cache
from django.utils import timezone

from core.controllers import naboopay_controller

logger = logging.getLogger(__name__)

CACHE_ROWS_KEY = "naboopay:admin:rows:v1"
CACHE_META_KEY = "naboopay:admin:meta:v1"
CACHE_PENDING_KEY = "naboopay:admin:pending_sync:v1"

MIN_SYNC_INTERVAL_SEC = 45
INCREMENTAL_MAX_PAGES = 8
FULL_MAX_PAGES = 60
ROWS_TTL_SEC = 60 * 60 * 24 * 7


def _serialize_row(row: dict) -> dict:
    payload = dict(row)
    for key in ("created_at", "paid_at", "event_at"):
        value = payload.get(key)
        if isinstance(value, datetime):
            payload[key] = timezone.localtime(value).isoformat()
    return payload


def _deserialize_row(data: dict) -> dict:
    from core.controllers.finance_controller import _parse_naboo_datetime

    row = dict(data)
    for key in ("created_at", "paid_at", "event_at"):
        raw = row.get(key)
        if isinstance(raw, str):
            row[key] = _parse_naboo_datetime(raw)
        elif raw is None and key == "event_at":
            row[key] = row.get("paid_at") or row.get("created_at")
    if not row.get("event_at"):
        row["event_at"] = row.get("paid_at") or row.get("created_at")
    return row


def _row_fingerprint(row: dict) -> tuple:
    paid = row.get("paid_at")
    paid_iso = paid.isoformat() if isinstance(paid, datetime) else str(paid or "")
    return (row.get("status"), int(row.get("amount") or 0), paid_iso)


def _map_tx(raw: dict) -> dict:
    from core.controllers.finance_controller import naboopay_transaction_row

    return naboopay_transaction_row(raw)


def _load_rows() -> list[dict]:
    stored = cache.get(CACHE_ROWS_KEY)
    if not stored:
        return []
    return [_deserialize_row(item) for item in stored]


def _save_rows(rows: list[dict], meta: dict) -> None:
    cache.set(CACHE_ROWS_KEY, [_serialize_row(row) for row in rows], ROWS_TTL_SEC)
    cache.set(CACHE_META_KEY, meta, ROWS_TTL_SEC)


def _default_meta() -> dict:
    return {
        "synced_at": None,
        "last_full_sync_at": None,
        "row_count": 0,
        "last_new_count": 0,
        "last_updated_count": 0,
        "sync_mode": "none",
        "from_cache": False,
    }


def last_meta() -> dict:
    meta = cache.get(CACHE_META_KEY) or _default_meta()
    return {**_default_meta(), **meta}


def request_sync() -> None:
    """Signalé après webhook paiement — prochaine lecture fera un delta NabooPay."""
    cache.set(CACHE_PENDING_KEY, True, ROWS_TTL_SEC)


def _should_sync(meta: dict) -> tuple[bool, bool]:
    """Retourne (do_sync, force_full)."""
    if cache.get(CACHE_PENDING_KEY):
        return True, False
    synced_at = meta.get("synced_at")
    if not synced_at:
        return True, True
    try:
        parsed = datetime.fromisoformat(str(synced_at))
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.utc)
    except ValueError:
        return True, True
    age = (timezone.now() - parsed).total_seconds()
    if age >= MIN_SYNC_INTERVAL_SEC:
        return True, False
    return False, False


def _merge_index(index: dict[str, dict], incoming: list[dict]) -> tuple[int, int]:
    new_count = 0
    updated_count = 0
    for row in incoming:
        order_id = row.get("order_id") or row.get("id")
        if not order_id:
            continue
        if order_id not in index:
            index[order_id] = row
            new_count += 1
            continue
        if _row_fingerprint(index[order_id]) != _row_fingerprint(row):
            index[order_id] = row
            updated_count += 1
    return new_count, updated_count


def _fetch_pages(*, max_pages: int, stop_when_stable: bool, index: dict[str, dict]) -> tuple[int, int, str | None]:
    new_total = 0
    updated_total = 0
    page = 1
    total_pages = 1
    error: str | None = None

    while page <= total_pages and page <= max_pages:
        result = naboopay_controller.list_transactions(page=page, limit=100)
        if not result.get("ok"):
            error = result.get("error") or "NabooPay indisponible."
            break
        pagination = result.get("pagination") or {}
        total_pages = int(pagination.get("total_pages") or 1)
        raw_rows = result.get("transactions") or []
        if not raw_rows:
            break

        mapped = [_map_tx(tx) for tx in raw_rows]
        new_count, updated_count = _merge_index(index, mapped)
        new_total += new_count
        updated_total += updated_count

        if stop_when_stable and new_count == 0 and updated_count == 0:
            break
        page += 1

    return new_total, updated_total, error


def sync(*, force_full: bool = False) -> tuple[list[dict], dict, str | None]:
    meta = last_meta()
    rows = _load_rows()
    index = {row["order_id"]: row for row in rows if row.get("order_id")}

    do_sync, run_full = _should_sync(meta) if not force_full else (True, force_full or not index)
    if not do_sync:
        meta = {**meta, "from_cache": True, "sync_mode": "cache"}
        return rows, meta, None

    cache.delete(CACHE_PENDING_KEY)

    if run_full or not index:
        new_count, updated_count, error = _fetch_pages(
            max_pages=FULL_MAX_PAGES,
            stop_when_stable=False,
            index=index,
        )
        sync_mode = "full"
        meta["last_full_sync_at"] = timezone.now().isoformat()
    else:
        new_count, updated_count, error = _fetch_pages(
            max_pages=INCREMENTAL_MAX_PAGES,
            stop_when_stable=True,
            index=index,
        )
        sync_mode = "incremental"

    merged = sorted(
        index.values(),
        key=lambda row: row.get("event_at") or row.get("created_at") or timezone.now(),
        reverse=True,
    )
    now_iso = timezone.now().isoformat()
    meta = {
        **meta,
        "synced_at": now_iso,
        "row_count": len(merged),
        "last_new_count": new_count,
        "last_updated_count": updated_count,
        "sync_mode": sync_mode,
        "from_cache": new_count == 0 and updated_count == 0 and bool(rows),
    }
    _save_rows(merged, meta)

    if new_count or updated_count:
        logger.info(
            "[naboopay-sync] %s — %s nouvelle(s), %s mise(s) à jour (%s lignes)",
            sync_mode,
            new_count,
            updated_count,
            len(merged),
        )

    return merged, meta, error


def get_rows(*, force_full: bool = False) -> tuple[list[dict], dict, str | None]:
    if not naboopay_controller.is_configured():
        return [], _default_meta(), "NabooPay n'est pas configuré."
    return sync(force_full=force_full)


def filter_rows(
    rows: list[dict],
    *,
    status: str | None = None,
    product_type: str | None = None,
    period: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str = "",
) -> list[dict]:
    from core.controllers.finance_controller import PRODUCT_TYPE_SEARCH, _period_bounds

    filtered = list(rows)
    if status:
        filtered = [row for row in filtered if row.get("status") == status]

    if product_type and product_type in PRODUCT_TYPE_SEARCH:
        token = PRODUCT_TYPE_SEARCH[product_type].lower()
        filtered = [row for row in filtered if token in (row.get("product") or "").lower()]

    start, end = _period_bounds(period, date_from, date_to)
    if start or end:

        def _in_range(row: dict) -> bool:
            event = row.get("event_at") or row.get("paid_at") or row.get("created_at")
            if not event:
                return False
            day = timezone.localtime(event).date()
            if start and day < start:
                return False
            if end and day > end:
                return False
            return True

        filtered = [row for row in filtered if _in_range(row)]

    query = (search or "").strip().lower()
    if query:
        filtered = [
            row
            for row in filtered
            if query in (row.get("order_id") or "").lower()
            or query in (row.get("id") or "").lower()
            or query in (row.get("user_name") or "").lower()
            or query in (row.get("user_phone") or "").lower()
            or query in (row.get("product") or "").lower()
            or query in (row.get("provider") or "").lower()
        ]

    filtered.sort(
        key=lambda row: row.get("event_at") or row.get("created_at") or timezone.now(),
        reverse=True,
    )
    return filtered


def public_meta(meta: dict) -> dict:
    synced_at = meta.get("synced_at")
    synced_label = ""
    if synced_at:
        try:
            parsed = datetime.fromisoformat(str(synced_at))
            if timezone.is_naive(parsed):
                parsed = timezone.make_aware(parsed, timezone.utc)
            synced_label = timezone.localtime(parsed).strftime("%d/%m/%Y %H:%M")
        except ValueError:
            synced_label = str(synced_at)
    return {
        "sync_mode": meta.get("sync_mode") or "none",
        "from_cache": bool(meta.get("from_cache")),
        "row_count": int(meta.get("row_count") or 0),
        "new_count": int(meta.get("last_new_count") or 0),
        "updated_count": int(meta.get("last_updated_count") or 0),
        "synced_at": synced_at,
        "synced_label": synced_label,
    }
