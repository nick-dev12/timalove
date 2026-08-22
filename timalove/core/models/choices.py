"""Enums métier — parité structuresqltinalove.sql."""

from django.db import models


class Gender(models.TextChoices):
    MALE = "male", "Homme"
    FEMALE = "female", "Femme"


class Religion(models.TextChoices):
    MUSULMANE = "musulmane", "Musulmane"
    CHRETIENNE = "chretienne", "Chrétienne"
    AUTRE = "autre", "Autre"


class RelationshipIntent(models.TextChoices):
    MARIAGE = "mariage", "Mariage"
    RELATION_SERIEUSE = "relation_serieuse", "Relation sérieuse"
    A_PRECISER = "a_preciser", "À préciser"


class UserRole(models.TextChoices):
    MEMBER = "member", "Membre"
    ADMIN = "admin", "Admin"


class RegistrationStatus(models.TextChoices):
    PENDING = "pending", "En attente"
    APPROVED = "approved", "Approuvé"
    REJECTED = "rejected", "Rejeté"


class SubscriptionTier(models.TextChoices):
    FREE = "free", "Gratuit"
    # Offres actuelles
    JOURNEE_AMOUREUSE = "journee_amoureuse", "Journée amoureuse"
    PASS_AMOUR = "pass_amour", "Pass Amour"
    ETERNITE = "eternite", "Éternité"
    VIP_1M = "vip_1m", "VIP"
    PASS_FEMME = "pass_femme", "Pass Femme"
    # Anciennes offres (import / historique)
    PREMIUM_10D = "premium_10d", "Premium 10 jours"
    PREMIUM_1M = "premium_1m", "Premium 1 mois"
    PREMIUM_2M = "premium_2m", "Premium 2 mois"
    VIP_2M = "vip_2m", "VIP 2 mois"
    VIP_FEMME_1W = "vip_femme_1w", "VIP Femme 1 semaine"


class SubscriptionStatus(models.TextChoices):
    INACTIVE = "inactive", "Inactif"
    ACTIVE = "active", "Actif"
    EXPIRED = "expired", "Expiré"


class MatchStatus(models.TextChoices):
    ACTIVE = "active", "Actif"
    UNMATCHED = "unmatched", "Unmatch"
    SCHEDULED = "scheduled", "Planifié"
    ENDED = "ended", "Terminé"


class MessageType(models.TextChoices):
    TEXT = "text", "Texte"
    VOICE = "voice", "Vocal"
    IMAGE = "image", "Image"
    SYSTEM = "system", "Système"


class NotificationType(models.TextChoices):
    NEW_LIKE = "new_like", "Nouveau like"
    NEW_MATCH = "new_match", "Nouveau match"
    NEW_MESSAGE = "new_message", "Nouveau message"
    SUBSCRIPTION_ACTIVATED = "subscription_activated", "Abonnement activé"
    SUBSCRIPTION_EXPIRED = "subscription_expired", "Abonnement expiré"
    PROFILE_APPROVED = "profile_approved", "Profil approuvé"
    PROFILE_REJECTED = "profile_rejected", "Profil rejeté"
    NEW_REGISTRATION = "new_registration", "Nouvelle inscription"
    BOOST_ACTIVATED = "boost_activated", "Boost activé"


class PaymentMethod(models.TextChoices):
    WAVE = "wave", "Wave"
    ORANGE_MONEY = "orange_money", "Orange Money"
    CB = "cb", "Carte bancaire"


class TransactionType(models.TextChoices):
    SUBSCRIPTION = "subscription", "Abonnement"
    COACHING = "coaching", "Coaching"
    BOOST = "boost", "Boost"


class TransactionStatus(models.TextChoices):
    PENDING = "pending", "En attente"
    PAID = "paid", "Payé"
    FAILED = "failed", "Échoué"
    REFUNDED = "refunded", "Remboursé"


class CoachingStatus(models.TextChoices):
    PENDING = "pending", "En attente"
    CONFIRMED = "confirmed", "Confirmé"
    COMPLETED = "completed", "Terminé"
    CANCELLED = "cancelled", "Annulé"


class CoachingTheme(models.TextChoices):
    COUPLE = "couple", "Couple"
    RUPTURE = "rupture", "Rupture"
    CONFIANCE = "confiance", "Confiance"
    COMMUNICATION = "communication", "Communication"
    RENCONTRES = "rencontres", "Rencontres"
    MARIAGE = "mariage", "Mariage"
    AUTRE = "autre", "Autre"


class TimeSlot(models.TextChoices):
    MATIN = "matin", "Matin"
    APREM = "aprem", "Après-midi"
    SOIR = "soir", "Soir"


class SwipeAction(models.TextChoices):
    PASS = "pass", "Pass"
    LIKE = "like", "Like"
    SUPER_LIKE = "super_like", "Super like"


class LastSeenVisibility(models.TextChoices):
    EVERYONE = "everyone", "Tout le monde"
    MATCHES = "matches", "Matchs uniquement"
    NOBODY = "nobody", "Personne"


class ReportReason(models.TextChoices):
    FAKE_PROFILE = "fake_profile", "Faux profil"
    HARASSMENT = "harassment", "Harcèlement"
    INAPPROPRIATE_CONTENT = "inappropriate_content", "Contenu inapproprié"
    SCAM = "scam", "Arnaque"
    SPAM = "spam", "Spam"
    OTHER = "other", "Autre"
    PLATFORM = "platform", "Plateforme"


class ReportStatus(models.TextChoices):
    PENDING = "pending", "En attente"
    RESOLVED = "resolved", "Résolu"
    DISMISSED = "dismissed", "Rejeté"
    REVIEWED = "reviewed", "Examiné"
    ACTION_TAKEN = "action_taken", "Action prise"


class ReportKind(models.TextChoices):
    PROFILE = "profile", "Profil"
    SUPPORT = "support", "Support"
