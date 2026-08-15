"""Appareils enregistrés pour les notifications push FCM."""

from __future__ import annotations

import uuid

from django.db import models

from .profile import Profile


class PushDevice(models.Model):
    class Platform(models.TextChoices):
        WEB = "web", "Web"
        ANDROID = "android", "Android"
        IOS = "ios", "iOS"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="push_devices",
    )
    token = models.CharField(max_length=512, unique=True)
    platform = models.CharField(
        max_length=20,
        choices=Platform.choices,
        default=Platform.WEB,
    )
    user_agent = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["profile", "-last_used_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.platform} — {self.profile_id}"
