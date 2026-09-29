"""Contenu métier — page Conseils Tima (liste, filtres, détails)."""

from __future__ import annotations

from typing import Any

Topic = dict[str, Any]

_COACHING: dict[str, Any] = {
    "id": "coaching",
    "title": "Coaching TimaLove",
    "summary": "Besoin d'un accompagnement ? Prenez rendez-vous avec un coach.",
    "image": "images/conseils/coaching-assistant.svg",
    "cta_label": "Prendre rendez-vous",
    "cta_url_name": "public:coaching",
}


def _topic(
    *,
    id: str,
    cat: str,
    title: str,
    summary: str,
    image: str,
    intro: str,
    bullets: list[str],
    cta_label: str | None = None,
    cta_url_name: str | None = None,
    cta_href: str | None = None,
) -> Topic:
    return {
        "id": id,
        "cat": cat,
        "title": title,
        "summary": summary,
        "image": image,
        "detail": {
            "intro": intro,
            "bullets": bullets,
            "cta_label": cta_label,
            "cta_url_name": cta_url_name,
            "cta_href": cta_href,
        },
    }


def list_topics() -> list[Topic]:
    img = "images/conseils"
    return [
        _topic(
            id="premier-rendez-vous",
            cat="rencontre",
            title="Premier rendez-vous",
            summary="Privilégiez un lieu public, informez un proche et prenez votre propre moyen de transport.",
            image=f"{img}/icon-premier-rdv.svg",
            intro="Un premier rendez-vous doit vous mettre à l'aise tout en protégeant votre sécurité.",
            bullets=[
                "Choisissez un café, un restaurant ou un lieu animé — évitez les endroits isolés.",
                "Prévenez un proche de l'heure, du lieu et du prénom de la personne rencontrée.",
                "Gardez le contrôle de votre retour : votre propre transport ou une course que vous commandez.",
                "Restez sobre et attentif·ve à votre ressenti ; vous pouvez partir à tout moment.",
                "Ne partagez pas votre adresse personnelle tant que la confiance n'est pas établie.",
            ],
            cta_label="Préparer ma rencontre",
            cta_url_name="public:connexions",
        ),
        _topic(
            id="faire-connaissance",
            cat="rencontre",
            title="Apprendre à se connaître",
            summary="Prenez le temps d'échanger dans l'application avant de partager vos coordonnées.",
            image=f"{img}/icon-faire-connaissance.svg",
            intro="Une relation sérieuse se construit pas à pas. TimaLove vous aide à avancer sans brûler les étapes.",
            bullets=[
                "Utilisez la messagerie pour poser des questions sur les valeurs, le projet de vie et la famille.",
                "Attendez une connexion acceptée avant d'engager un échange approfondi.",
                "Évitez de basculer trop vite sur WhatsApp ou les réseaux : gardez une trace sereine ici.",
                "Si une réponse vous met mal à l'aise, faites une pause — le respect prime sur la vitesse.",
                "Quand vous vous sentez prêt·e, proposez un premier rendez-vous en lieu public.",
            ],
            cta_label="Voir mes connexions",
            cta_url_name="public:connexions",
        ),
        _topic(
            id="couple",
            cat="relation",
            title="Construire une relation durable",
            summary="Compromis, pardon, acceptation, partage et respect mutuel sont essentiels.",
            image=f"{img}/icon-relation.svg",
            intro="Une relation qui dure repose sur des fondations communes, pas sur l'idéalisation.",
            bullets=[
                "Clarifiez vos attentes sur le couple, la famille et le mariage tôt dans le parcours.",
                "Accueillez les différences : elles enrichissent si elles restent respectées.",
                "Cultivez la gratitude et les gestes concrets plutôt que les promesses vagues.",
                "Parcourez nos thèmes dédiés (communication, compromis, pardon…) pour approfondir.",
                "En cas de doute persistant, un coaching TimaLove peut vous aider à y voir clair.",
            ],
            cta_label="Explorer le coaching",
            cta_url_name="public:coaching",
        ),
        _topic(
            id="securite",
            cat="rencontre",
            title="Sécurité sur TimaLove",
            summary="Protégez vos informations personnelles et signalez tout comportement inapproprié.",
            image=f"{img}/securite.svg",
            intro="Votre sécurité est prioritaire. Nous modérons la plateforme et comptons sur votre vigilance.",
            bullets=[
                "Ne communiquez jamais votre mot de passe, code OTP ou coordonnées bancaires.",
                "Méfiez-vous des demandes d'argent, même avec un prétexte urgent ou émotionnel.",
                "Signalez depuis une discussion (menu ⋯ → Signaler) tout profil ou message abusif.",
                "Bloquez ou clôturez une connexion qui ne vous convient plus — sans justification publique.",
                "Consultez notre politique de confidentialité pour savoir comment vos données sont protégées.",
            ],
            cta_label="Politique de confidentialité",
            cta_url_name="public:confidentialite",
        ),
        _topic(
            id="mariage",
            cat="mariage",
            title="Mariage",
            summary="Le projet de mariage se précise par des conversations concrètes, pas par la précipitation.",
            image=f"{img}/icon-mariage.svg",
            intro="« On se marie quand au juste ? » — la réponse se construit à deux, avec lucidité.",
            bullets=[
                "Parlez calendrier, budget, famille et lieu sans tabou, mais sans pression.",
                "Alignez-vous sur la foi, les traditions et le rôle de chacun dans le couple.",
                "Un engagement annoncé trop tôt peut masquer des incompatibilités : avancez par étapes.",
                "Faites valider votre projet par des proches de confiance si cela vous aide.",
                "TimaLove favorise les rencontres orientées mariage : servez-vous de votre profil pour le montrer.",
            ],
            cta_label="Compléter mon profil",
            cta_url_name="app:profil",
        ),
        _topic(
            id="communication",
            cat="relation",
            title="Communication",
            summary="Dites ce que vous attendez, et écoutez ce que l'autre peut offrir.",
            image=f"{img}/icon-communication.svg",
            intro="Parler vrai, sans agressivité, évite les malentendus qui freinent un projet de mariage.",
            bullets=[
                "Utilisez des phrases en « je » : « je ressens », « j'aimerais » plutôt que « tu ne fais jamais ».",
                "Reformulez ce que vous avez entendu avant de répondre — l'autre se sent écouté.",
                "Fixez un moment calme pour les sujets sensibles, pas en pleine dispute.",
                "Dans l'app, prenez le temps d'écrire ; relisez avant d'envoyer un message tendu.",
                "Si la communication bloque, un tiers bienveillant (coach, proche) peut débloquer la situation.",
            ],
            cta_label="Reprendre la conversation",
            cta_url_name="public:messages",
        ),
        _topic(
            id="compromis",
            cat="relation",
            title="Compromis",
            summary="Un compromis protège les deux projets, il n'efface pas le vôtre.",
            image=f"{img}/icon-relation.svg",
            intro="Compromettre ne signifie pas renoncer à vos valeurs essentielles.",
            bullets=[
                "Distinguez ce qui est négociable (horaires, loisirs) de ce qui ne l'est pas (respect, fidélité).",
                "Cherchez une solution où chacun gagne quelque chose, pas où l'un cède tout.",
                "Documentez les accords oralisés : « nous avons convenu que… » pour éviter les retours en arrière.",
                "Revoyez les compromis avec le temps : un couple évolue.",
            ],
            cta_label="Continuer le dialogue",
            cta_url_name="public:messages",
        ),
        _topic(
            id="pardon",
            cat="relation",
            title="Pardon",
            summary="Le pardon se décide, il ne s'exige pas.",
            image=f"{img}/icon-faire-connaissance.svg",
            intro="Pardonner est un choix personnel ; il ne dispense pas toujours de poser des limites.",
            bullets=[
                "Nommez la blessure clairement avant de décider de pardonner ou non.",
                "Le pardon authentique va de pair avec un changement de comportement observable.",
                "Vous n'êtes pas obligé·e de rester en contact si la confiance est rompue.",
                "Un coach peut vous aider à distinguer pardon, réconciliation et sécurité.",
            ],
            cta_label="En parler en coaching",
            cta_url_name="public:coaching",
        ),
        _topic(
            id="acceptation",
            cat="relation",
            title="Acceptation",
            summary="Accepter l'autre, c'est voir la personne réelle, pas seulement l'idée qu'on s'en fait.",
            image=f"{img}/icon-faire-connaissance.svg",
            intro="L'acceptation n'est pas de tout tolerer : c'est regarder l'autre avec lucidité.",
            bullets=[
                "Notez ce que vous admirez chez l'autre — et ce qui vous questionne, sans juger.",
                "Évitez de vouloir « former » votre partenaire à votre image.",
                "Les différences de tempérament peuvent se compléter si le respect est là.",
                "Si un trait fondamental ne vous convient pas, l'acceptation passera par un choix de séparation.",
            ],
            cta_label="Affiner mes critères",
            cta_url_name="public:explorer",
        ),
        _topic(
            id="partage",
            cat="relation",
            title="Partage",
            summary="Le partage du quotidien se prépare avant de vivre sous le même toit.",
            image=f"{img}/icon-relation.svg",
            intro="Tester le quotidien partagé réduit les surprises après le mariage.",
            bullets=[
                "Parlez finances, tâches domestiques et temps libre avant d'eménager.",
                "Organisez des activités communes simples : courses, cuisine, sorties — observez le ressenti.",
                "Respectez des espaces personnels même en couple.",
                "Le partage des responsabilités doit rester équitable et discuté.",
            ],
            cta_label="Planifier un rendez-vous",
            cta_url_name="public:connexions",
        ),
        _topic(
            id="respect",
            cat="relation",
            title="Respect mutuel",
            summary="Le respect se voit dans les mots, les silences et les limites.",
            image=f"{img}/icon-relation.svg",
            intro="Sans respect, aucun projet de mariage ne tient dans la durée.",
            bullets=[
                "Pas d'insultes, de moqueries ni de chantage affectif — en ligne comme en personne.",
                "Les « non » doivent être entendus sans pression ni culpabilisation.",
                "Signalez tout comportement dégradant via TimaLove ou bloquez la personne.",
                "Choisissez des partenaires qui honorent déjà votre dignité dans les premiers échanges.",
            ],
            cta_label="Mes messages",
            cta_url_name="public:messages",
        ),
    ]


def coaching_block() -> dict[str, Any]:
    return dict(_COACHING)


def topic_by_id(topic_id: str) -> Topic | None:
    for item in list_topics():
        if item["id"] == topic_id:
            return item
    return None
