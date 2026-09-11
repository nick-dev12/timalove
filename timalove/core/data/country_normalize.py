"""Normalisation des libellés pays pour stats admin et cohérence profils."""

from __future__ import annotations

import unicodedata

from core.data.countries import COUNTRIES_FR

OTHER_LABEL = "Autre"


def fold_country(value: str) -> str:
    text = (value or "").strip().lower()
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    folded = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return " ".join(folded.split())


CANONICAL_BY_FOLD: dict[str, str] = {fold_country(name): name for name in COUNTRIES_FR}

# Variantes fréquentes en base (imports, saisie libre, géolocalisation).
ALIASES: dict[str, str] = {
    "senegal": "Sénégal",
    "senegalais": "Sénégal",
    "senegalaise": "Sénégal",
    "snegal": "Sénégal",
    "sn": "Sénégal",
    "gambia": "Gambie",
    "the gambia": "Gambie",
    "espana": "Espagne",
    "spain": "Espagne",
    "italia": "Italie",
    "italy": "Italie",
    "maroc": "Maroc",
    "morocco": "Maroc",
    "mali": "Mali",
    "guinee": "Guinée",
    "guinea": "Guinée",
    "guinee bissau": "Guinée-Bissau",
    "cote divoire": "Côte d'Ivoire",
    "cote d ivoire": "Côte d'Ivoire",
    "ivory coast": "Côte d'Ivoire",
    "cameroun": "Cameroun",
    "cameroon": "Cameroun",
    "usa": "États-Unis",
    "etats unis": "États-Unis",
    "united states": "États-Unis",
    "u s a": "États-Unis",
    "uk": "Royaume-Uni",
    "united kingdom": "Royaume-Uni",
    "allemagne": "Allemagne",
    "germany": "Allemagne",
    "belgique": "Belgique",
    "belgium": "Belgique",
    "canada": "Canada",
    "france": "France",
    "tunisie": "Tunisie",
    "tunisia": "Tunisie",
    "algerie": "Algérie",
    "algeria": "Algérie",
    "mauritanie": "Mauritanie",
    "mauritania": "Mauritanie",
    "benin": "Bénin",
    "burkina": "Burkina Faso",
    "burkina faso": "Burkina Faso",
    "nigeria": "Nigeria",
    "niger": "Niger",
    "togo": "Togo",
    "ghana": "Ghana",
    "liban": "Liban",
    "lebanon": "Liban",
    "turquie": "Turquie",
    "turkey": "Turquie",
    "chine": "Chine",
    "china": "Chine",
    "japon": "Japon",
    "japan": "Japon",
    "portugal": "Portugal",
    "pays bas": "Pays-Bas",
    "netherlands": "Pays-Bas",
    "suisse": "Suisse",
    "switzerland": "Suisse",
    "autre": OTHER_LABEL,
    "other": OTHER_LABEL,
    "unknown": OTHER_LABEL,
    "inconnu": OTHER_LABEL,
}

# Communes / villes sénégalaises souvent saisies à la place du pays.
SENEGAL_CITIES: frozenset[str] = frozenset(
    {
        "dakar",
        "thies",
        "mbour",
        "touba",
        "diourbol",
        "diourbel",
        "kaolack",
        "saint louis",
        "saint-louis",
        "ziguinchor",
        "pikine",
        "rufisque",
        "tambacounda",
        "louga",
        "fatick",
        "kaffrine",
        "matam",
        "sedhiou",
        "kedougou",
        "kolda",
        "bambey",
        "keur massar",
        "guediawaye",
        "guediawaye",
        "mbacké",
        "mbacke",
        "joal fadiouth",
        "joal",
        "podor",
        "bignona",
        "kédougou",
        "tivaouane",
        "bargny",
        "diamniadio",
        "ngaparou",
        "saly",
        "popenguine",
        "parcelles assainies",
        "grand yoff",
        "medina",
        "médina",
        "hlm",
        "ouakam",
        "almadies",
        "yoff",
        "keur massar",
    }
)


def normalize_country_label(raw: str | None) -> str | None:
    """
    Retourne un pays canonique (COUNTRIES_FR) ou « Autre ».
    None si valeur vide / invalide.
    """
    text = (raw or "").strip()
    if not text or len(text) < 2:
        return None

    fold = fold_country(text)
    if not fold:
        return None

    if fold in CANONICAL_BY_FOLD:
        return CANONICAL_BY_FOLD[fold]

    if fold in ALIASES:
        return ALIASES[fold]

    if fold in SENEGAL_CITIES or fold.startswith("seneg"):
        return "Sénégal"

    # Correspondance partielle prudente (ex. « republique du senegal »).
    if "senegal" in fold:
        return "Sénégal"

    for alias, canonical in ALIASES.items():
        if len(alias) >= 5 and alias in fold:
            return canonical

    for country_fold, canonical in CANONICAL_BY_FOLD.items():
        if len(country_fold) >= 5 and country_fold in fold:
            return canonical

    return OTHER_LABEL


def member_country_for_stats(country: str | None, residence_country: str | None) -> str | None:
    """Pays d'origine prioritaire, puis pays de résidence — normalisés."""
    for raw in (country, residence_country):
        label = normalize_country_label(raw)
        if label:
            return label
    return None


def member_residence_for_stats(residence_country: str | None, country: str | None = None) -> str | None:
    """Pays de résidence (wizard géo « Pays »), repli sur origine si absent."""
    label = normalize_country_label(residence_country)
    if label:
        return label
    return normalize_country_label(country)


def normalize_country_for_storage(raw: str | None) -> str | None:
    """Pour nettoyage en base : ne remplace pas par « Autre »."""
    label = normalize_country_label(raw)
    if not label or label == OTHER_LABEL:
        return None
    return label
