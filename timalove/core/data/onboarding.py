"""Contenu onboarding — intérêts, caractère, copies."""

from __future__ import annotations

import json

INTERESTS = [
    {"id": "voyage", "label": "Voyage", "icon": "plane"},
    {"id": "lecture", "label": "Lecture", "icon": "book"},
    {"id": "musique", "label": "Musique", "icon": "music"},
    {"id": "photo", "label": "Photo", "icon": "camera"},
    {"id": "sport", "label": "Sport", "icon": "dumbbell"},
    {"id": "art", "label": "Art", "icon": "palette"},
    {"id": "cafe", "label": "Café", "icon": "coffee"},
    {"id": "cinema", "label": "Cinéma", "icon": "film"},
    {"id": "cuisine", "label": "Cuisine", "icon": "chef"},
    {"id": "jeux", "label": "Jeux", "icon": "game"},
    {"id": "nature", "label": "Nature", "icon": "leaf"},
    {"id": "foi", "label": "Foi", "icon": "heart"},
]

TRAITS = [
    {"id": "bienveillant", "label": "Bienveillant", "icon": "heart"},
    {"id": "fidele", "label": "Fidèle", "icon": "ring"},
    {"id": "spirituel", "label": "Spirituel", "icon": "spark"},
    {"id": "ambitieux", "label": "Ambitieux", "icon": "mountain"},
    {"id": "romantique", "label": "Romantique", "icon": "rose"},
    {"id": "calme", "label": "Calme", "icon": "wave"},
    {"id": "genereux", "label": "Généreux", "icon": "gift"},
    {"id": "drole", "label": "Enjoué", "icon": "smile"},
]

LIFE_VALUES = [
    {"id": "famille", "label": "Famille", "icon": "heart"},
    {"id": "foi", "label": "Foi", "icon": "spark"},
    {"id": "sincerite", "label": "Sincérité", "icon": "ring"},
    {"id": "respect", "label": "Respect", "icon": "wave"},
    {"id": "fidelite", "label": "Fidélité", "icon": "ring"},
    {"id": "humilite", "label": "Humilité", "icon": "leaf"},
    {"id": "travail", "label": "Travail", "icon": "mountain"},
    {"id": "education", "label": "Éducation", "icon": "book"},
    {"id": "entourage", "label": "Entourage", "icon": "gift"},
    {"id": "equilibre", "label": "Équilibre", "icon": "wave"},
]

LOOKING_FOR = [
    {"id": "serieux", "label": "Sincère", "icon": "heart"},
    {"id": "croyant", "label": "Croyant", "icon": "spark"},
    {"id": "familial", "label": "Familial", "icon": "gift"},
    {"id": "calme", "label": "Calme", "icon": "wave"},
    {"id": "ambitieux", "label": "Ambitieux", "icon": "mountain"},
    {"id": "sociable", "label": "Sociable", "icon": "smile"},
    {"id": "spirituel", "label": "Spirituel", "icon": "spark"},
    {"id": "projet_famille", "label": "Projet de famille", "icon": "heart"},
    {"id": "meme_culture", "label": "Même culture", "icon": "ring"},
    {"id": "international", "label": "International", "icon": "plane"},
]

_LOOKING_FOR_IDS = {item["id"] for item in LOOKING_FOR}
_LOOKING_FOR_LABELS = {item["id"]: item["label"] for item in LOOKING_FOR}
_LIFE_VALUE_LABELS = {item["id"]: item["label"] for item in LIFE_VALUES}


def looking_for_ids(raw) -> list[str]:
    items: list[str] = []
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
    else:
        text = str(raw or "").strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except (TypeError, ValueError):
            return []
        if isinstance(parsed, list):
            items = [str(x).strip() for x in parsed if str(x).strip()]
    return [item for item in items if item in _LOOKING_FOR_IDS]


def looking_for_labels(raw) -> list[str]:
    return [_LOOKING_FOR_LABELS[item] for item in looking_for_ids(raw)]


def looking_for_free_text(raw) -> str:
    if looking_for_ids(raw):
        return ""
    if isinstance(raw, list):
        return ""
    text = str(raw or "").strip()
    if not text:
        return ""
    try:
        json.loads(text)
        return ""
    except (TypeError, ValueError):
        return text


def encode_looking_for(value) -> str:
    ids = looking_for_ids(value)
    if ids:
        return json.dumps(ids, ensure_ascii=False)
    return looking_for_free_text(value)[:800]


def life_value_labels(values) -> list[str]:
    out: list[str] = []
    for item in values or []:
        key = str(item).strip()
        if key:
            out.append(_LIFE_VALUE_LABELS.get(key, key))
    return out


STEP_COPY = {
    "1": {
        "title": "Faisons connaissance.",
        "lead": "Quelques mots sincères suffisent. Les profils vrais trouvent les cœurs vrais.",
        "hint": "Chaque détail nous aide à vous présenter aux bonnes personnes.",
        "cta": "Continuer",
        "footer": "Vous êtes au bon endroit.",
    },
    "2": {
        "title": "Ce qui vous anime.",
        "lead": "Choisissez au moins une option parmi les intérêts, et au moins une parmi le caractère. Les valeurs sont optionnelles.",
        "hint": "Une sélection minimum par liste proposée — les valeurs, vous les ajoutez si vous le souhaitez, une par une.",
        "cta": "Continuer",
        "footer": "On apprend à vous connaître…",
    },
    "3": {
        "title": "Votre histoire.",
        "lead": "Vous pouvez raconter qui vous êtes, et qui vous espérez rencontrer. Cette étape est optionnelle.",
        "hint": "",
        "cta": "Continuer",
        "footer": "Les mots justes ouvrent les belles portes.",
    },
    "4": {
        "title": "Le vrai vous.",
        "lead": "Une photo de profil, puis un instant face caméra. Ainsi chacun avance en confiance.",
        "hint": "Lumière naturelle, visage bien visible, sourire sincère.",
        "cta": "Rejoindre TimaLove",
        "footer": "Dernière étape — vous y êtes presque.",
    },
}

MIN_INTERESTS = 1
MIN_TRAITS = 1
MAX_VALUES = 12
MIN_BIO = 40
MIN_LOOKING_FOR = 20
FACE_MATCH_THRESHOLD = 0.52

SIGNUP_COPY = {
    "email": {
        "kicker": "Votre entrée",
        "title": "Votre email, pour commencer.",
        "lead": "Une adresse sincère, et le chemin s’ouvre. Nous vous y attendons déjà.",
        "cta": "Continuer",
    },
    "phone": {
        "kicker": "Votre entrée",
        "title": "Votre numéro, tout simplement.",
        "lead": "C’est le fil le plus direct. Un numéro vrai, et nous avançons ensemble.",
        "cta": "Continuer",
    },
    "password": {
        "kicker": "Sécurité",
        "title": "Un mot de passe rien qu’à vous.",
        "lead": "Huit caractères au moins. Gardez-le précieux : il protège vos rencontres.",
        "cta": "Continuer",
    },
    "identity": {
        "kicker": "Vous",
        "title": "Disons qui vous êtes.",
        "lead": "Un prénom, un âge, un numéro. Les profils vrais trouvent les cœurs vrais.",
        "cta": "Continuer",
    },
    "socio": {
        "kicker": "Origines",
        "title": "Ce qui vous ancre.",
        "lead": "Sexe, foi, pays d’origine : des repères pour des rencontres alignées.",
        "cta": "Continuer",
    },
    "interests": {
        "kicker": "Passions",
        "title": "Ce qui vous anime.",
        "lead": "Choisissez ce qui vous ressemble — ou passez, vous pourrez y revenir.",
        "cta": "Continuer",
    },
    "bios": {
        "kicker": "Paroles",
        "title": "Deux mots sur vous.",
        "lead": "Qui vous êtes, et qui vous espérez rencontrer. Rien n’est obligatoire ici.",
        "cta": "Continuer",
    },
    "projet": {
        "kicker": "Projet",
        "title": "Ce que vous construisez.",
        "lead": "Famille, foi, installation : dites-le si vous le sentez. Cette étape reste libre.",
        "cta": "Continuer",
    },
    "photos": {
        "kicker": "Visage",
        "title": "Montrez le vrai vous.",
        "lead": "Une photo nette, éventuellement une deuxième. Lumière naturelle, sourire sincère.",
        "cta": "Continuer",
    },
    "geo": {
        "kicker": "Présence",
        "title": "Où vous êtes.",
        "lead": "Autorisez la localisation : ville, pays et commune s’affichent, rien de plus.",
        "cta": "Continuer",
    },
    "notif": {
        "kicker": "Dernière étape",
        "title": "Restez dans le fil.",
        "lead": "Un like, un message, une rencontre : les notifications vous le murmurent. Vous y êtes presque.",
        "cta": "Rejoindre TimaLove",
    },
}
