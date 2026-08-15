"""Landing content helpers."""

from __future__ import annotations

HERO_FEATURES = [
    {"icon": "✓", "title": "Profils vérifiés", "subtitle": "Validation manuelle"},
    {"icon": "👥", "title": "Accompagnement", "subtitle": "100% personnalisé"},
    {"icon": "❤️", "title": "Objectif mariage", "subtitle": "Relations sérieuses"},
]

STEPS = [
    {
        "number": "01",
        "title": "Inscription",
        "description": "Remplissez notre formulaire détaillé. Chaque profil est examiné personnellement par notre équipe.",
    },
    {
        "number": "02",
        "title": "Validation",
        "description": "Nous vérifions l'authenticité et le sérieux de votre démarche. Seuls les profils sincères sont acceptés.",
    },
    {
        "number": "03",
        "title": "Mise en relation",
        "description": "Découvrez des profils compatibles et swipez pour trouver votre match.",
    },
    {
        "number": "04",
        "title": "Accompagnement",
        "description": "Nous vous guidons à chaque étape jusqu'à la rencontre. Un suivi humain et bienveillant.",
    },
]

COACHING_THEMES = [
    "Confiance en soi",
    "Cicatrices du passé",
    "Communication de couple",
    "Préparation au mariage",
    "Spiritualité & relations",
    "Reconstruction post-rupture",
    "Choix du bon partenaire",
]

COACHING_FEATURES = [
    {
        "icon": "sparkle",
        "title": "Séance sur-mesure",
        "description": "Un accompagnement pensé pour votre histoire, vos blocages et vos espoirs.",
    },
    {
        "icon": "shield",
        "title": "Espace confidentiel",
        "description": "Tout ce qui se dit reste entre nous. Votre intimité est sacrée.",
    },
    {
        "icon": "heart",
        "title": "Écoute bienveillante",
        "description": "Sans jugement, sans étiquette. Juste de l'écoute, vraie et profonde.",
    },
    {
        "icon": "check",
        "title": "Résultats concrets",
        "description": "Des actions claires à mettre en place dès la fin de la séance.",
    },
]

COACHING_STEPS = [
    {"number": "01", "title": "Réservez votre créneau"},
    {"number": "02", "title": "Recevez le lien visio"},
    {"number": "03", "title": "Vivez votre séance"},
    {"number": "04", "title": "Repartez avec un plan"},
]

COACHING_QUOTE = {
    "text": "Une séance qui m'a permis de reprendre confiance et d'y voir plus clair dans mes attentes.",
    "author": "Fatou D.",
}

FALLBACK_TEMOIGNAGES = [
    {
        "name": "Oumar",
        "age": 28,
        "initial": "O",
        "quote": "Excellent excellent excellent excellent",
        "rating": 5,
    },
    {
        "name": "Diallo",
        "age": 25,
        "initial": "D",
        "quote": "Woww c'est énorme vous êtes trop forts je t donne une note 10/10",
        "rating": 5,
    },
    {
        "name": "Amadou",
        "age": 33,
        "initial": "A",
        "quote": "Je viens de m'inscrire sur TimaLove. Le site a l'air sérieux et propre. J'espère trouver une relation sincère ici.",
        "rating": 5,
    },
    {
        "name": "Cheikh",
        "age": 19,
        "initial": "C",
        "quote": "Vraiment c'est un site que j'admire beaucoup",
        "rating": 5,
    },
    {
        "name": "Amelia",
        "age": 28,
        "initial": "A",
        "quote": "J'ai jamais vu une personne si gentille et compréhensible. TimaLove t'écoute et fait tout pour que tu trouves quelqu'un qui te faut.",
        "rating": 5,
    },
    {
        "name": "Saly",
        "age": 20,
        "initial": "S",
        "quote": "Le concept est différent de tous les autres sites de rencontre. Que des personnes sérieuses, je ne regrette pas.",
        "rating": 5,
    },
]

PLACEHOLDER_MEMBERS = [
    {
        "first_name": "Profil à venir",
        "age": None,
        "city": "TimaLove",
        "bio": bio,
        "badge": "BIENTÔT",
        "is_placeholder": True,
        "photo_url": None,
    }
    for bio in [
        "Soyez parmi les premiers profils vérifiés de la communauté TimaLove.",
        "Une place vous attend parmi des membres sérieux, validés un par un.",
        "Rejoignez une communauté qui privilégie le respect et les projets de mariage.",
        "Votre profil pourra apparaître ici après validation par notre équipe.",
        "Des rencontres authentiques commencent par une inscription sincère.",
        "Faites partie des fondateurs de cette belle aventure collective.",
    ]
]

ORIGINE_OPTIONS = [
    ("senegal", "Sénégal"),
    ("mali", "Mali"),
    ("guinee", "Guinée"),
    ("cote-ivoire", "Côte d'Ivoire"),
    ("cameroun", "Cameroun"),
    ("france", "France"),
    ("belgique", "Belgique"),
    ("autre", "Autre"),
]


def home_context() -> dict:
    from core.controllers import moderation_controller, profile_controller, site_settings_controller

    members = profile_controller.landing_members(6)
    member_cards = [
        {
            "first_name": m.first_name,
            "age": None if m.hide_age else m.age,
            "city": m.city,
            "bio": m.bio or "",
            "badge": "PREMIUM" if m.has_active_subscription else "MEMBRE",
            "is_placeholder": False,
            "photo_url": m.primary_photo,
            "show_verified": m.is_verified,
        }
        for m in members
    ]
    while len(member_cards) < 6:
        member_cards.append(PLACEHOLDER_MEMBERS[len(member_cards)])

    testimonials = moderation_controller.published_testimonials(3)
    if testimonials:
        temoignages = [
            {
                "name": t.author_name,
                "age": t.author_age,
                "initial": (t.author_name or "?")[:1].upper(),
                "quote": t.content,
                "rating": t.rating or 5,
            }
            for t in testimonials
        ]
    else:
        temoignages = FALLBACK_TEMOIGNAGES

    return {
        "brand": "TimaLove",
        "tagline": "Mise en relation sérieuse vers le mariage",
        "hero_features": HERO_FEATURES,
        "steps": STEPS,
        "coaching_themes": COACHING_THEMES,
        "coaching_features": COACHING_FEATURES,
        "members": member_cards,
        "temoignages": temoignages,
        "site_config": site_settings_controller.public_config(),
    }


def _serialize_testimonial(item) -> dict:
    if isinstance(item, dict):
        return item
    name = item.author_name or "Membre"
    return {
        "name": name,
        "age": item.author_age,
        "initial": name[:1].upper(),
        "quote": item.content,
        "rating": item.rating or 5,
    }


def testimonials_page_context() -> dict:
    from core.controllers import moderation_controller

    published = moderation_controller.published_testimonials(12)
    temoignages = [_serialize_testimonial(t) for t in published] if published else FALLBACK_TEMOIGNAGES
    return {
        "title": "Témoignages",
        "temoignages": temoignages,
    }


def coaching_page_context() -> dict:
    from core.controllers import site_settings_controller
    from core.models.choices import CoachingTheme, TimeSlot

    return {
        "title": "Coaching individuel",
        "themes": COACHING_THEMES,
        "features": COACHING_FEATURES,
        "steps": COACHING_STEPS,
        "quote": COACHING_QUOTE,
        "theme_choices": CoachingTheme.choices,
        "slot_choices": TimeSlot.choices,
        "site_config": site_settings_controller.public_config(),
    }
