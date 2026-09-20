"""Questions guidées — mariage, culture, famille (Lot C)."""

from __future__ import annotations

import hashlib
from datetime import date

GUIDED_INTRO_POOL: tuple[str, ...] = (
    "Bonjour, je cherche une relation sérieuse orientée mariage. Quel est votre projet de vie ?",
    "Bonjour, votre profil m'a interpellé. Quelle place accordez-vous à la famille dans votre projet ?",
    "Bonjour, ravi de cette mise en relation. Quand envisagez-vous une union stable ?",
    "Bonjour, comment la culture sénégalaise influence-t-elle votre vision du couple et du mariage ?",
    "Bonjour, quelle importance accordez-vous aux repas en famille dans votre quotidien ?",
    "Bonjour, quels loisirs partagez-vous volontiers avec une personne de confiance ?",
    "Bonjour, comment imaginez-vous l'accueil de la belle-famille dans votre projet d'union ?",
    "Bonjour, quelles valeurs familiales souhaitez-vous transmettre à vos enfants ?",
    "Bonjour, comment conciliez-vous foi, respect et projet de couple ?",
    "Bonjour, qu'est-ce qui vous rassure dans une démarche matrimoniale sérieuse ?",
    "Bonjour, comment décririez-vous un week-end idéal en couple orienté long terme ?",
    "Bonjour, quelle place la sincérité occupe-t-elle dans vos échanges ?",
)

DAILY_SUGGESTION_POOL: tuple[str, ...] = (
    "Suggestion du jour : demandez comment votre interlocuteur célèbre les grandes fêtes familiales.",
    "Suggestion du jour : échangez sur le rôle des aînés dans votre famille.",
    "Suggestion du jour : partagez un plat ou une tradition qui compte pour vous.",
    "Suggestion du jour : parlez de ce qui vous semble essentiel avant un mariage.",
    "Suggestion du jour : demandez comment la personne envisage l'équilibre couple et famille élargie.",
)


def _pick_three(pool: tuple[str, ...], seed: str) -> tuple[str, ...]:
    if len(pool) <= 3:
        return pool
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    order = list(range(len(pool)))
    for i in range(len(order) - 1, 0, -1):
        chunk = digest[(len(order) - 1 - i) * 2 : (len(order) - i) * 2]
        j = int(chunk or "0", 16) % (i + 1)
        order[i], order[j] = order[j], order[i]
    return tuple(pool[order[i]] for i in range(3))


def prompts_for_match(match_id) -> tuple[str, ...]:
    today = date.today().isoformat()
    return _pick_three(GUIDED_INTRO_POOL, f"match:{match_id}:{today}")


def daily_suggestion(profile_id) -> str:
    today = date.today().isoformat()
    pool = DAILY_SUGGESTION_POOL
    digest = hashlib.sha256(f"daily:{profile_id}:{today}".encode("utf-8")).hexdigest()
    index = int(digest[:8], 16) % len(pool)
    return pool[index]
