"""Pagination sécurisée — évite EmptyPage sur pages admin hors limites."""

from __future__ import annotations

from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator


def safe_page(paginator: Paginator, page: int | str | None):
    """Retourne une page valide même si l'index demandé est hors bornes."""
    try:
        number = int(page or 1)
    except (TypeError, ValueError):
        number = 1
    if number < 1:
        number = 1
    try:
        return paginator.page(number)
    except PageNotAnInteger:
        return paginator.page(1)
    except EmptyPage:
        last = paginator.num_pages or 1
        return paginator.page(last)
