"""Contenu statique Stories (aperçu UI avant système stories)."""

from __future__ import annotations

from core.controllers import explore_controller


STATIC_STORY_BUBBLES = [
    {"name": "Votre story", "ring": "self", "is_self": True},
    {"name": "Aïcha", "ring": "rose", "is_self": False},
    {"name": "Omar", "ring": "online", "is_self": False},
    {"name": "Fatou", "ring": "bordeaux", "is_self": False},
    {"name": "Ibrahim", "ring": "rose", "is_self": False},
    {"name": "Mariam", "ring": "online", "is_self": False},
    {"name": "Khadija", "ring": "bordeaux", "is_self": False},
]


def page_context() -> dict:
    cards, _ = explore_controller.public_feed(offset=0, limit=6, seed="stories-preview")
    bubbles = []
    for i, bubble in enumerate(STATIC_STORY_BUBBLES):
        photo = None
        if not bubble["is_self"] and i - 1 < len(cards):
            photo = cards[i - 1].get("photo_url")
        elif bubble["is_self"] and cards:
            photo = None
        bubbles.append({**bubble, "photo_url": photo})

    preview_cards = []
    statuses = ["En ligne", "Actif aujourd'hui", "Récemment", "En ligne", "Actif aujourd'hui", "Récemment"]
    for i, card in enumerate(cards):
        preview_cards.append(
            {
                **card,
                "status": statuses[i % len(statuses)],
                "status_tone": "online" if i % 2 == 0 else "idle",
                "distance": f"{(i % 5) + 1} km",
            }
        )

    return {
        "title": "Stories",
        "bubbles": bubbles,
        "preview_cards": preview_cards,
    }
