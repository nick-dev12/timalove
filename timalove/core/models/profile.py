"""Modèle Profile — cœur métier TimaLove."""

from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone

from .choices import (
    Gender,
    LastSeenVisibility,
    RegistrationStatus,
    RelationshipIntent,
    Religion,
    STAFF_ROLES,
    SubscriptionStatus,
    SubscriptionTier,
    UserRole,
)


class Profile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=40, blank=True, null=True)
    date_of_birth = models.DateField(blank=True, null=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True, default="")
    city = models.CharField(max_length=120, blank=True, default="")
    commune = models.CharField(max_length=180, blank=True, default="")
    relationship_intent = models.CharField(
        max_length=40,
        choices=RelationshipIntent.choices,
        blank=True,
        default="",
    )
    life_project = models.TextField(blank=True, default="")
    google_uid = models.CharField(max_length=128, blank=True, null=True, unique=True)
    apple_uid = models.CharField(max_length=128, blank=True, null=True, unique=True)
    country = models.CharField(max_length=120, default="Sénégal")
    residence_country = models.CharField(max_length=120, blank=True, null=True)
    religion = models.CharField(max_length=20, choices=Religion.choices, blank=True, null=True)
    profession = models.CharField(max_length=180, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    looking_for = models.TextField(blank=True, null=True)
    photo_url = models.TextField(blank=True, null=True)
    photo_url_2 = models.TextField(blank=True, null=True)
    photo_url_3 = models.TextField(blank=True, null=True)
    interests = models.JSONField(default=list, blank=True)
    personality_traits = models.JSONField(default=list, blank=True)
    verification_photo_url = models.TextField(blank=True, null=True)
    face_match_score = models.FloatField(blank=True, null=True)
    onboarding_step = models.PositiveSmallIntegerField(default=1)
    onboarding_completed = models.BooleanField(default=False)
    registration_status = models.CharField(
        max_length=20,
        choices=RegistrationStatus.choices,
        default=RegistrationStatus.APPROVED,
    )
    role = models.CharField(max_length=20, choices=UserRole.choices, default=UserRole.MEMBER)
    is_verified = models.BooleanField(default=False)
    rejection_reason = models.TextField(blank=True, null=True)
    subscription_tier = models.CharField(
        max_length=30,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.FREE,
    )
    subscription_status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.INACTIVE,
    )
    subscription_end_date = models.DateTimeField(blank=True, null=True)
    likes_received_count = models.PositiveIntegerField(default=0)
    likes_given_count = models.PositiveIntegerField(default=0)
    matches_count = models.PositiveIntegerField(default=0)
    is_boosted = models.BooleanField(default=False)
    boost_end_date = models.DateTimeField(blank=True, null=True)
    last_active_at = models.DateTimeField(default=timezone.now, blank=True, null=True)
    likes_inbox_seen_at = models.DateTimeField(blank=True, null=True)
    is_online = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    is_shadowbanned = models.BooleanField(default=False)
    last_seen_visibility = models.CharField(
        max_length=20,
        choices=LastSeenVisibility.choices,
        default=LastSeenVisibility.EVERYONE,
    )
    hide_age = models.BooleanField(default=False)
    notification_preferences = models.JSONField(
        default=dict,
    )
    discover_filters = models.JSONField(default=dict, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=6, blank=True, null=True)
    location_updated_at = models.DateTimeField(blank=True, null=True)
    life_values = models.JSONField(default=list, blank=True)
    suspended_at = models.DateTimeField(blank=True, null=True)
    banned_at = models.DateTimeField(blank=True, null=True)
    ban_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["gender"]),
            models.Index(fields=["city"]),
            models.Index(fields=["registration_status"]),
            models.Index(fields=["-created_at"]),
            models.Index(fields=["-last_active_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def save(self, *args, **kwargs):
        if not self.notification_preferences:
            self.notification_preferences = {
                "push": False,
                "likes": True,
                "super_likes": True,
                "matches": True,
                "messages": True,
                "status": True,
            }
        super().save(*args, **kwargs)

    @property
    def age(self) -> int | None:
        if not self.date_of_birth:
            return None
        today = timezone.localdate()
        years = today.year - self.date_of_birth.year
        if (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day):
            years -= 1
        return years

    @property
    def is_profile_complete(self) -> bool:
        if self.onboarding_completed:
            return True
        if (self.onboarding_step or 1) > 1:
            return False
        if self.registration_status == RegistrationStatus.PENDING:
            return False
        return bool(
            self.date_of_birth
            and self.gender
            and (self.first_name or "").strip()
            and (self.photo_url or "").strip()
        )

    @property
    def is_staff_member(self) -> bool:
        return self.role in STAFF_ROLES

    @property
    def is_admin(self) -> bool:
        return self.is_staff_member

    @property
    def is_super_admin(self) -> bool:
        return self.role == UserRole.SUPER_ADMIN

    @property
    def has_active_subscription(self) -> bool:
        if self.subscription_status != SubscriptionStatus.ACTIVE:
            return False
        if self.subscription_end_date and self.subscription_end_date < timezone.now():
            return False
        return self.subscription_tier != SubscriptionTier.FREE

    @property
    def display_name(self) -> str:
        first = " ".join((self.first_name or "").split())
        last = " ".join((self.last_name or "").split())
        if first and last:
            first_l, last_l = first.lower(), last.lower()
            if last_l == first_l or first_l.endswith(" " + last_l):
                return first
            return f"{first} {last}"
        return first or last or "Membre"

    @property
    def primary_photo(self) -> str | None:
        return self.photo_url


class ProfileGalleryPhoto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="gallery_photos")
    position = models.PositiveSmallIntegerField()
    photo_url = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(fields=["profile", "position"], name="unique_gallery_position"),
        ]

    def __str__(self) -> str:
        return f"{self.profile_id} #{self.position}"
