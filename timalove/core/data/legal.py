"""Contenu légal TimaLove — CGV, mentions, confidentialité, suppression de compte.

Aligné sur les exigences Google Play / App Store (transparence, suppression de compte,
données d'app mobile) et inspiré de la structure juridique COLObanes (poid_lourd).
"""

CONTACT_EMAIL = "timaloveagence@gmail.com"
SITE_URL = "https://mytimalove.com"
EDITOR = "Problem Solving Agency"
BRAND = "TimaLove"
UPDATED = "7 septembre 2026"

CGV_SECTIONS = [
    {
        "id": "article-1",
        "title": "Article 1 — Objet",
        "paragraphs": [
            f"Les présentes Conditions Générales de Vente et d'Utilisation (ci-après « CGV ») encadrent l'accès et l'utilisation de la plateforme {BRAND}, éditée par {EDITOR}, au Sénégal.",
            f"{BRAND} est une plateforme de mise en relation sérieuse orientée vers le mariage, accessible via le site {SITE_URL} et les applications mobiles iOS et Android.",
        ],
        "list": [
            "Création et gestion de profil membre",
            "Validation manuelle des inscriptions",
            "Mise en relation entre profils compatibles",
            "Messagerie (texte, photos, messages vocaux)",
            "Stories, likes, matchs et fonctionnalités associées",
            "Abonnements et offres premium",
            "Coaching individuel en relations",
        ],
    },
    {
        "id": "article-2",
        "title": "Article 2 — Formation du contrat",
        "paragraphs": [
            f"Le contrat entre l'utilisateur et {EDITOR} est réputé formé notamment lors de l'inscription, de l'acceptation des présentes CGV, du paiement d'un abonnement ou de la réservation d'un coaching.",
        ],
    },
    {
        "id": "article-3",
        "title": "Article 3 — Conditions de paiement",
        "paragraphs": [
            "Les abonnements sont payables selon les modalités affichées au moment de la commande. Le coaching est payable d'avance. Les paiements sont traités via des prestataires de paiement (notamment NabooPay : Wave, Orange Money, carte).",
            "Les montants sont indiqués en FCFA sauf mention contraire. Aucun remboursement automatique n'est dû pour une période d'abonnement déjà entamée, sauf disposition légale impérative ou décision commerciale écrite de TimaLove.",
        ],
    },
    {
        "id": "article-4",
        "title": "Article 4 — Inscription, profils et validation",
        "paragraphs": [
            "L'inscription sur TimaLove est réservée aux personnes majeures (18 ans révolus) et soumise à validation manuelle. Seuls les profils sincères et conformes sont acceptés.",
            "L'utilisateur s'engage à fournir des informations exactes, des photos réellement représentatives, et à ne pas usurper l'identité d'autrui.",
        ],
    },
    {
        "id": "article-5",
        "title": "Article 5 — Conduite et contenus",
        "paragraphs": [
            "Sont interdits notamment : harcèlement, menaces, contenus illicites ou pornographiques, discréditation d'autrui, spam, tentative de fraude, et toute utilisation détournée de la plateforme.",
            "TimaLove peut modérer, masquer ou supprimer un contenu, suspendre ou supprimer un compte en cas de manquement, sans préjudice d'éventuelles poursuites.",
        ],
    },
    {
        "id": "article-6",
        "title": "Article 6 — Application mobile",
        "paragraphs": [
            "L'application mobile peut demander, avec votre consentement système, l'accès à la caméra, au microphone, à la galerie photos, à la localisation (pendant l'utilisation) et aux notifications push. Ces accès sont décrits dans la Politique de confidentialité.",
            "Vous pouvez refuser ou révoquer ces autorisations dans les réglages de votre appareil ; certaines fonctionnalités seront alors indisponibles.",
        ],
    },
    {
        "id": "article-7",
        "title": "Article 7 — Droit applicable",
        "paragraphs": [
            "Les présentes CGV sont régies par le droit en vigueur en République du Sénégal. Les litiges sont soumis aux tribunaux de Dakar après tentative amiable.",
        ],
    },
]

MENTIONS_SECTIONS = [
    {
        "id": "editeur",
        "title": "1 — Éditeur du site et des applications",
        "paragraphs": [
            f"Le site {SITE_URL} et les applications mobiles {BRAND} (iOS et Android) sont édités par {EDITOR} (marque {BRAND}).",
            f"Contact : {CONTACT_EMAIL} — Dakar, République du Sénégal.",
        ],
    },
    {
        "id": "hebergement",
        "title": "2 — Hébergement",
        "paragraphs": [
            "Le service est hébergé sur une infrastructure serveur dédiée (VPS) opérée pour le compte de l'éditeur, avec base de données PostgreSQL et stockage des médias associés au service.",
            "Adresse technique d'accès public : mytimalove.com (et www.mytimalove.com).",
        ],
    },
    {
        "id": "apps",
        "title": "3 — Applications mobiles",
        "paragraphs": [
            "Android : identifiant applicatif com.timalove.app — distribution via Google Play.",
            "iOS : identifiant applicatif com.mytimalove.app — distribution via l'App Store Apple.",
        ],
    },
    {
        "id": "pi",
        "title": "4 — Propriété intellectuelle",
        "paragraphs": [
            f"L'ensemble des éléments composant le site et les applications {BRAND} (textes, visuels, logo, code, charte) est protégé et demeure la propriété de {EDITOR}, sauf contenus fournis par les utilisateurs sous leur responsabilité.",
        ],
    },
    {
        "id": "contact-legal",
        "title": "5 — Contact juridique / données personnelles",
        "paragraphs": [
            f"Pour toute question relative aux mentions légales ou aux données personnelles : {CONTACT_EMAIL} (objet recommandé : « Mentions légales » ou « Données personnelles »).",
        ],
    },
]

PRIVACY_SECTIONS = [
    {
        "id": "intro",
        "title": "1 — Introduction",
        "paragraphs": [
            f"La présente politique décrit comment {EDITOR} (« nous »), éditeur de la marque {BRAND}, collecte, utilise, conserve, partage et protège les données personnelles des personnes qui utilisent le site {SITE_URL} et les applications mobiles associées.",
            f"{BRAND} est une plateforme de mise en relation sérieuse vers le mariage. Nous traitons les données de manière loyale, transparente et sécurisée, et limitons la collecte au strict nécessaire.",
            "Nous ne commercialisons pas vos données personnelles et ne les vendons pas à des tiers.",
            f"L'utilisation du Service implique la prise de connaissance de cette politique et des Conditions générales. Pour la suppression de compte, consultez aussi la page dédiée « Suppression de compte ».",
        ],
        "note": f"Dernière mise à jour : {UPDATED}",
    },
    {
        "id": "responsable",
        "title": "2 — Responsable du traitement et contact",
        "paragraphs": [
            f"Le responsable du traitement est {EDITOR}, opérant sous la marque {BRAND}.",
        ],
        "list": [
            "Siège / zone d'activité : Dakar, République du Sénégal",
            f"Courriel dédié (vie privée / support) : {CONTACT_EMAIL} — précisez « Données personnelles » dans l'objet",
            f"Site : {SITE_URL}",
        ],
    },
    {
        "id": "principes",
        "title": "3 — Principes et engagements",
        "paragraphs": [
            "Nous appliquons notamment les principes suivants :",
        ],
        "list": [
            "Licéité, loyauté et transparence",
            "Minimisation des données",
            "Exactitude (mise à jour possible depuis votre compte)",
            "Limitation de la conservation",
            "Intégrité et confidentialité",
            "Responsabilisation (contrôles d'accès, clauses prestataires, sensibilisation des équipes)",
        ],
    },
    {
        "id": "non-vente",
        "title": "4 — Non-commercialisation et exigences Apple / Google",
        "paragraphs": [
            f"{BRAND} ne vend pas, ne loue pas et ne cède pas vos données personnelles à des fins de marketing, de profilage publicitaire ou de monétisation de dossiers utilisateurs.",
            "Nous ne partageons pas vos coordonnées, messages ou photos avec des courtiers en données ou des réseaux publicitaires tiers indépendants de TimaLove.",
            "Les seuls partages autorisés sont ceux nécessaires à l'exécution du Service (prestataires techniques contractuels) ou imposés par la loi.",
            "Cette section répond aux exigences de transparence des plateformes Apple App Store et Google Play en matière de confidentialité.",
        ],
        "subsections": [
            {
                "title": "Vos données restent sous votre contrôle",
                "paragraphs": [
                    "Vous pouvez modifier vos informations, refuser certaines autorisations appareil (caméra, micro, localisation, notifications), et demander la suppression de votre compte.",
                    "L'accès au Service n'est pas conditionné à l'acceptation de traitements non essentiels (publicité ciblée tierce, revente de données) — de tels traitements ne sont pas pratiqués.",
                ],
            }
        ],
    },
    {
        "id": "donnees",
        "title": "5 — Données collectées",
        "subsections": [
            {
                "title": "5.1 Compte et profil",
                "list": [
                    "Identité : prénom, nom, e-mail, téléphone, date de naissance, genre",
                    "Informations de profil : ville, pays, religion, profession, bio, critères de recherche",
                    "Photos de profil et galerie (fournies par vous)",
                    "Mot de passe : stocké sous forme hachée (jamais en clair)",
                    "Statut d'inscription / vérification (selfie de vérification le cas échéant)",
                ],
            },
            {
                "title": "5.2 Usage de la plateforme",
                "list": [
                    "Likes, swipes, matchs, blocages, signalements",
                    "Messages (texte, images, messages vocaux)",
                    "Stories et interactions associées",
                    "Historique d'activité pertinente au service (dernière connexion, présence)",
                ],
            },
            {
                "title": "5.3 Paiement et abonnements",
                "paragraphs": [
                    "Métadonnées de transaction (montant, devise, statut, identifiant fourni par le prestataire, moyen générique). Les données de carte complètes sont traitées par le prestataire de paiement ; nous ne stockons pas les numéros de carte complets ni les cryptogrammes.",
                ],
            },
            {
                "title": "5.4 Données techniques et application mobile",
                "list": [
                    "Adresse IP, horodatage, User-Agent, journaux serveur",
                    "Identifiant de session / jetons d'authentification",
                    "Jetons de notification push (FCM / APNs) lorsque vous autorisez les notifications",
                    "Modèle d'appareil et version OS (Android / iOS) utiles au support et à la sécurité",
                    "Localisation approximative ou précise uniquement si vous l'autorisez (explorer / ville) — jamais en arrière-plan",
                ],
            },
            {
                "title": "5.5 Données reçues de tiers",
                "paragraphs": [
                    "Si vous vous connectez via un prestataire d'authentification (ex. Google / Apple / Firebase), nous pouvons recevoir un identifiant technique et des informations de profil que vous avez autorisées côté ce tiers.",
                ],
            },
        ],
    },
    {
        "id": "finalites",
        "title": "6 — Finalités et bases légales",
        "paragraphs": [
            "Synthèse des principaux traitements :",
        ],
        "table": {
            "headers": ["Finalité", "Exemples de données", "Base légale (synthèse)"],
            "rows": [
                [
                    "Création et gestion du compte",
                    "Identité, e-mail, mot de passe haché, profil",
                    "Contrat / mesures précontractuelles ; intérêt légitime (fraude à l'inscription)",
                ],
                [
                    "Mise en relation et messagerie",
                    "Profil, photos, likes, matchs, messages",
                    "Exécution du contrat",
                ],
                [
                    "Validation et sécurité des profils",
                    "Photos, signalements, logs",
                    "Intérêt légitime ; obligation légale le cas échéant",
                ],
                [
                    "Abonnements et paiements",
                    "Métadonnées de transaction",
                    "Contrat ; obligation légale comptable",
                ],
                [
                    "Notifications push",
                    "Jeton FCM/APNs, préférences",
                    "Consentement (réglages système / in-app)",
                ],
                [
                    "Localisation (si autorisée)",
                    "Position / ville",
                    "Consentement ; exécution du service demandé",
                ],
                [
                    "Support et amélioration du service",
                    "Tickets, stats agrégées",
                    "Intérêt légitime ; consentement pour analytics non essentiels",
                ],
            ],
        },
    },
    {
        "id": "profilage",
        "title": "7 — Décisions automatisées et matching",
        "paragraphs": [
            "TimaLove peut utiliser des règles ou scores pour proposer des profils compatibles, détecter des abus ou classer des contenus. Ces traitements n'ont pas pour objet de produire des effets juridiques significatifs sans possibilité d'intervention humaine.",
            f"Vous pouvez contester une décision vous concernant en écrivant à {CONTACT_EMAIL}.",
        ],
    },
    {
        "id": "destinataires",
        "title": "8 — Destinataires et sous-traitants",
        "subsections": [
            {
                "title": "8.1 Accès internes",
                "paragraphs": [
                    "Seules les personnes habilitées (support, modération, technique, administration) accèdent aux données, dans la limite du besoin d'en connaître.",
                ],
            },
            {
                "title": "8.2 Prestataires techniques",
                "paragraphs": [
                    "Hébergement, e-mails transactionnels, notifications push (Firebase), paiements, CDN / DNS (ex. Cloudflare), sauvegardes. Ces acteurs agissent selon des obligations contractuelles de confidentialité et de sécurité.",
                    "Certains prestataires peuvent être situés hors du Sénégal ; des garanties appropriées (chiffrement en transit, clauses contractuelles) sont recherchées.",
                ],
            },
            {
                "title": "8.3 Autorités",
                "paragraphs": [
                    "Communication possible uniquement lorsque la loi l'exige (réquisition) ou pour protéger la sécurité des utilisateurs, dans le strict cadre légal.",
                ],
            },
            {
                "title": "8.4 Ce que nous ne faisons pas",
                "list": [
                    "Vendre ou louer vos données à des annonceurs / data brokers",
                    "Créer des profils publicitaires vendus à des tiers",
                    "Utiliser vos photos ou messages à des fins publicitaires tierces",
                    "Transmettre vos données de paiement complètes à des acteurs non habilités",
                ],
            },
        ],
    },
    {
        "id": "conservation",
        "title": "9 — Durées de conservation",
        "table": {
            "headers": ["Catégorie", "Durée indicative"],
            "rows": [
                ["Compte actif", "Durée de vie du compte + courte période technique de sauvegarde"],
                ["Après suppression de compte", "Voir Politique de suppression de compte"],
                ["Transactions / facturation", "Délais comptables et fiscaux applicables (souvent plusieurs années)"],
                ["Journaux serveur / sécurité", "Quelques jours à 12 mois selon criticité"],
                ["Jetons push", "Tant que le compte est actif et l'appareil enregistré"],
            ],
        },
        "paragraphs_after": [
            "À l'issue des durées, les données sont supprimées ou anonymisées de façon irréversible lorsque leur conservation n'est plus justifiée.",
        ],
    },
    {
        "id": "securite",
        "title": "10 — Sécurité",
        "list": [
            "Chiffrement en transit (HTTPS / TLS)",
            "Mots de passe hachés (algorithmes adaptés)",
            "Contrôle d'accès et moindre privilège",
            "Sauvegardes et restauration",
            "Mises à jour de sécurité raisonnables",
            "Modération et signalements pour protéger la communauté",
        ],
        "paragraphs": [
            "Aucune transmission sur Internet n'est garantie à 100 % inviolable. Protégez vos appareils et méfiez-vous des messages frauduleux se faisant passer pour TimaLove.",
        ],
    },
    {
        "id": "mobile",
        "title": "11 — Application mobile : permissions",
        "paragraphs": [
            "Avant chaque demande système, l'application peut afficher une explication in-app. Détail des usages :",
        ],
        "table": {
            "headers": ["Permission", "Usage"],
            "rows": [
                ["Caméra", "Photo de profil, selfie de vérification, image dans une discussion"],
                ["Microphone", "Message vocal dans une conversation uniquement"],
                ["Galerie / photos", "Import d'une photo existante pour le profil ou la discussion"],
                ["Localisation (pendant l'usage)", "Profils à proximité / ville du profil — pas d'arrière-plan"],
                ["Notifications", "Likes, matchs, nouveaux messages — refusable"],
            ],
        },
        "paragraphs_after": [
            "Non utilisés : contacts, localisation « toujours », suivi GPS en arrière-plan.",
        ],
    },
    {
        "id": "cookies",
        "title": "12 — Cookies et technologies similaires",
        "paragraphs": [
            "Nous utilisons des cookies ou stockage local nécessaires à la session, à la sécurité et au bon fonctionnement du site. Des mesures d'audience peuvent être utilisées de façon agrégée.",
            "Vous pouvez restreindre les cookies via les réglages de votre navigateur ; certaines fonctions pourront alors être limitées.",
        ],
    },
    {
        "id": "notifications",
        "title": "13 — Communications et notifications",
        "paragraphs": [
            "Nous pouvons vous envoyer des e-mails ou notifications liés au Service (sécurité, match, message, validation de compte). Les notifications push mobiles nécessitent votre autorisation système.",
            "Vous pouvez gérer certaines préférences dans l'application ou les réglages de l'appareil, et vous désinscrire des communications marketing lorsque proposées.",
        ],
    },
    {
        "id": "mineurs",
        "title": "14 — Mineurs",
        "paragraphs": [
            "Le Service est strictement réservé aux personnes majeures (18 ans révolus). TimaLove ne collecte pas sciemment de données auprès de mineurs.",
            "Tout compte mineur détecté sera supprimé. Pour Apple / Google : aucune collecte volontaire auprès d'enfants au sens des règles des stores.",
        ],
    },
    {
        "id": "droits",
        "title": "15 — Vos droits",
        "paragraphs": [
            "Sous réserve du droit applicable, vous pouvez notamment :",
        ],
        "list": [
            "Accéder à vos données",
            "Les rectifier depuis votre profil ou sur demande",
            "Demander l'effacement / la suppression de compte",
            "Vous opposer à certains traitements",
            "Limiter certains traitements",
            "Retirer un consentement (permissions appareil, notifications)",
        ],
        "paragraphs_after": [
            f"Exercice des droits : depuis l'espace Paramètres / Profil, ou par e-mail à {CONTACT_EMAIL}. Nous pouvons demander une preuve d'identité raisonnable pour éviter les abus. Délai de réponse habituel : 30 jours.",
        ],
    },
    {
        "id": "suppression",
        "title": "16 — Suppression du compte",
        "paragraphs": [
            "Vous pouvez supprimer votre compte depuis l'application / le site (Paramètres → Supprimer mon compte) lorsque la fonctionnalité est disponible, ou en suivant la procédure décrite sur la page « Suppression de compte ».",
            f"URL publique : {SITE_URL}/suppression-de-compte/",
        ],
    },
    {
        "id": "reclame",
        "title": "17 — Réclamations",
        "paragraphs": [
            f"Contactez d'abord {CONTACT_EMAIL}. Vous pouvez également saisir l'autorité compétente en matière de protection des données dans votre pays de résidence, le cas échéant.",
        ],
    },
    {
        "id": "evolution",
        "title": "18 — Évolution de cette politique",
        "paragraphs": [
            f"Nous pouvons mettre à jour cette politique pour refléter des évolutions légales ou produit. La date de mise à jour figurera en tête de page. La version en vigueur est publiée sur {SITE_URL}/politique-de-confidentialite/.",
        ],
    },
]

ACCOUNT_DELETION_SECTIONS = [
    {
        "id": "intro",
        "title": "1 — Objet",
        "paragraphs": [
            f"Cette page décrit comment demander la suppression de votre compte utilisateur {BRAND}, quelles données sont effacées ou conservées, et les délais associés.",
            "Elle répond aux exigences de Google Play et de l'App Store Apple concernant la suppression de compte et la transparence des données.",
            f"Elle complète la Politique de confidentialité ({SITE_URL}/politique-de-confidentialite/).",
        ],
        "note": f"Dernière mise à jour : {UPDATED}",
    },
    {
        "id": "procedure-app",
        "title": "2 — Suppression depuis l'application ou le site (recommandé)",
        "paragraphs": [
            "Connectez-vous à votre compte TimaLove, ouvrez votre profil / paramètres, puis choisissez « Supprimer mon compte » et confirmez.",
            "Cette action ferme l'accès au compte et déclenche la suppression des données associées selon les règles ci-dessous.",
        ],
    },
    {
        "id": "procedure-email",
        "title": "3 — Demande par e-mail",
        "paragraphs": [
            f"Si vous ne pouvez plus vous connecter, écrivez à {CONTACT_EMAIL} avec l'objet « Demande de suppression de compte TimaLove ».",
        ],
        "list": [
            "Utilisez de préférence l'e-mail associé au compte (ou indiquez le téléphone au format international)",
            "Précisez nom / prénom tels qu'enregistrés",
            "Nous pouvons demander une preuve d'identité raisonnable pour éviter qu'un tiers ne demande la suppression à votre place",
            "Après vérification, nous confirmons généralement sous 30 jours (délai pouvant être prolongé si la demande est complexe)",
        ],
    },
    {
        "id": "donnees",
        "title": "4 — Données supprimées / conservées",
        "subsections": [
            {
                "title": "En principe supprimées ou anonymisées",
                "list": [
                    "Profil (identité, bio, préférences, photos hébergées liées au compte)",
                    "E-mail et téléphone liés au compte lorsqu'ils ne sont plus nécessaires",
                    "Mot de passe (enregistrement du compte)",
                    "Likes, matchs, messages et stories liés au compte (sous réserve d'obligations légales)",
                    "Jetons de notification push associés à l'appareil",
                ],
            },
            {
                "title": "Susceptibles d'être conservées",
                "list": [
                    "Éléments nécessaires à la preuve de transactions / abonnements / facturation",
                    "Informations pour litiges, signalements graves ou obligation légale",
                    "Journaux techniques anonymisés ou pseudonymisés (sécurité)",
                    "Données imposées par une autorité ou décision judiciaire",
                ],
            },
        ],
    },
    {
        "id": "delais",
        "title": "5 — Délais",
        "paragraphs": [
            "La fermeture d'accès est en principe immédiate ou rapide après confirmation.",
            "La purge complète des copies de sauvegarde peut prendre un délai technique supplémentaire (jours / semaines selon le cycle de backup).",
            "Les données comptables ou litigieuses suivent les délais légaux applicables, sans réactivation du profil commercial.",
        ],
    },
    {
        "id": "stores",
        "title": "6 — Informations pour Google Play et App Store",
        "paragraphs": [
            f"URL de la politique de confidentialité : {SITE_URL}/politique-de-confidentialite/",
            f"URL de suppression de compte : {SITE_URL}/suppression-de-compte/",
            f"URL des mentions légales : {SITE_URL}/mentions-legales/",
            "Le compte peut être supprimé depuis l'app (chemin Paramètres / Profil) ou par e-mail comme indiqué ci-dessus.",
        ],
    },
]
