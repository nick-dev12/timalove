"""Événements système pour le monitoring back-office."""

from __future__ import annotations

import uuid

from django.db import models


class SystemEvent(models.Model):
    """Erreur / alerte technique capturée pour la page Monitoring."""

    class Level(models.TextChoices):
        CRITICAL = "critical", "Critique"
        ERROR = "error", "Erreur"
        WARNING = "warning", "Avertissement"
        INFO = "info", "Info"

    class Source(models.TextChoices):
        HTTP = "http", "HTTP"
        EXCEPTION = "exception", "Exception"
        SLOW = "slow", "Requête lente"
        LOGGING = "logging", "Logger"
        CELERY = "celery", "Celery"
        PAYMENT = "payment", "Paiement"
        EMAIL = "email", "Email"
        PUSH = "push", "Push"
        SYSTEM = "system", "Système"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    level = models.CharField(max_length=16, choices=Level.choices, default=Level.ERROR, db_index=True)
    source = models.CharField(max_length=24, choices=Source.choices, default=Source.SYSTEM, db_index=True)
    title = models.CharField(max_length=220)
    message = models.TextField(blank=True, default="")
    path = models.CharField(max_length=500, blank=True, default="")
    method = models.CharField(max_length=12, blank=True, default="")
    status_code = models.PositiveSmallIntegerField(null=True, blank=True)
    exception_type = models.CharField(max_length=120, blank=True, default="")
    location = models.CharField(max_length=300, blank=True, default="", help_text="fichier:ligne")
    traceback = models.TextField(blank=True, default="")
    fingerprint = models.CharField(max_length=64, blank=True, default="", db_index=True)
    occurrence_count = models.PositiveIntegerField(default=1)
    user_email = models.CharField(max_length=254, blank=True, default="")
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-last_seen_at"]
        indexes = [
            models.Index(fields=["-last_seen_at", "level"]),
            models.Index(fields=["fingerprint", "-last_seen_at"]),
            models.Index(fields=["source", "-last_seen_at"]),
        ]

    def __str__(self) -> str:
        return f"[{self.level}] {self.title[:80]}"
