"""Campagnes marketing — push, email, popups in-app."""

from __future__ import annotations

import uuid

from django.db import models

from .profile import Profile


class CampaignChannel(models.TextChoices):
    PUSH = "push", "Push notification"
    EMAIL = "email", "Email"
    IN_APP = "in_app", "Popup in-app"
    PUSH_IN_APP = "push_in_app", "Push + popup in-app"


class CampaignStatus(models.TextChoices):
    DRAFT = "draft", "Brouillon"
    SCHEDULED = "scheduled", "Programmée"
    SENDING = "sending", "Envoi en cours"
    SENT = "sent", "Envoyée"
    CANCELLED = "cancelled", "Annulée"


class CampaignSendMode(models.TextChoices):
    IMMEDIATE = "immediate", "Immédiat"
    SCHEDULED = "scheduled", "Programmé"


class MarketingCampaign(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=120)
    channel = models.CharField(max_length=20, choices=CampaignChannel.choices, default=CampaignChannel.PUSH_IN_APP)
    title = models.CharField(max_length=200)
    body = models.TextField()
    image_url = models.URLField(max_length=500, blank=True, default="")
    deep_link = models.CharField(max_length=300, default="/")
    segment = models.JSONField(default=dict, blank=True)
    send_mode = models.CharField(
        max_length=20,
        choices=CampaignSendMode.choices,
        default=CampaignSendMode.IMMEDIATE,
    )
    scheduled_at = models.DateTimeField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=CampaignStatus.choices,
        default=CampaignStatus.DRAFT,
    )
    recipients_count = models.PositiveIntegerField(default=0)
    delivered_count = models.PositiveIntegerField(default=0)
    opened_count = models.PositiveIntegerField(default=0)
    clicked_count = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="campaigns_created",
    )
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.name


class CampaignDelivery(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    campaign = models.ForeignKey(
        MarketingCampaign,
        on_delete=models.CASCADE,
        related_name="deliveries",
    )
    profile = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="campaign_deliveries",
    )
    channel = models.CharField(max_length=20, choices=CampaignChannel.choices)
    delivered_at = models.DateTimeField(auto_now_add=True)
    opened_at = models.DateTimeField(blank=True, null=True)
    clicked_at = models.DateTimeField(blank=True, null=True)
    dismissed_at = models.DateTimeField(blank=True, null=True)
    push_sent = models.BooleanField(default=False)
    email_sent = models.BooleanField(default=False)
    in_app_shown = models.BooleanField(default=False)

    class Meta:
        ordering = ["-delivered_at"]
        constraints = [
            models.UniqueConstraint(fields=["campaign", "profile"], name="uniq_campaign_profile_delivery"),
        ]
        indexes = [
            models.Index(fields=["profile", "-delivered_at"]),
            models.Index(fields=["campaign", "-delivered_at"]),
        ]
