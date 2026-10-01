"""Questions guidées — une intention vocale avant la discussion."""

from __future__ import annotations

import hashlib

GUIDED_INTRO_POOL: tuple[str, ...] = (
    "Qu’est-ce qui, chez {name}, vous donne envie d’un vrai projet de couple ?",
)

DAILY_SUGGESTION_POOL: tuple[str, ...] = (
    "Suggestion du jour : demandez comment votre interlocuteur célèbre les grandes fêtes familiales.",
    "Suggestion du jour : échangez sur le rôle des aînés dans votre famille.",
    "Suggestion du jour : partagez un plat ou une tradition qui compte pour vous.",
    "Suggestion du jour : parlez de ce qui vous semble essentiel avant un mariage.",
    "Suggestion du jour : demandez comment la personne envisage l'équilibre couple et famille élargie.",
)

GUIDED_STEPS = 1


def _display_name(name: str | None) -> str:
    cleaned = " ".join((name or "").split()).strip()
    return cleaned or "cette personne"


def format_prompt(template: str, name: str | None = None) -> str:
    return template.format(name=_display_name(name))


def prompts_for_match(match_id, name: str | None = None) -> tuple[str, ...]:
    del match_id
    return (format_prompt(GUIDED_INTRO_POOL[0], name),)


def daily_suggestion(profile_id) -> str:
    from datetime import date

    today = date.today().isoformat()
    pool = DAILY_SUGGESTION_POOL
    digest = hashlib.sha256(f"daily:{profile_id}:{today}".encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(pool)
    return pool[index]
