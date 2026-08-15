"""Notifications, paiements, coaching, modération, settings, avis."""

from __future__ import annotations

import uuid

from django.db import models

from .choices import (
    CoachingStatus,
    CoachingTheme,
    Gender,
    NotificationType,
    PaymentMethod,
    ReportKind,
    ReportReason,
    ReportStatus,
    SubscriptionStatus,
    SubscriptionTier,
    TimeSlot,
    TransactionStatus,
    TransactionType,
)
from .matching import Match
from .profile import Profile


class Notification(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="notifications")
    type = models.CharField(max_length=40, choices=NotificationType.choices)
    title = models.CharField(max_length=200)
    message = models.TextField()
    related_user = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="related_notifications",
    )
    related_match = models.ForeignKey(
        Match,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
    )
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "-created_at"])]


class Transaction(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        Profile,
        on_delete=models.CASCADE,
        related_name="transactions",
        null=True,
        blank=True,
    )
    order_id = models.CharField(max_length=120, unique=True)
    amount = models.PositiveIntegerField()
    payment_method = models.CharField(max_length=30, choices=PaymentMethod.choices, blank=True, null=True)
    type = models.CharField(max_length=30, choices=TransactionType.choices)
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
    )
    subscription = models.ForeignKey(
        "Subscription",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    coaching_request = models.ForeignKey(
        "CoachingRequest",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transactions",
    )
    naboo_transaction_id = models.CharField(max_length=120, blank=True, null=True)
    payment_details = models.JSONField(default=dict, blank=True)
    plan_tier = models.CharField(max_length=30, choices=SubscriptionTier.choices, blank=True, null=True)
    subscription_end_date = models.DateTimeField(blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class Subscription(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="subscriptions")
    tier = models.CharField(max_length=30, choices=SubscriptionTier.choices)
    status = models.CharField(
        max_length=20,
        choices=SubscriptionStatus.choices,
        default=SubscriptionStatus.INACTIVE,
    )
    amount = models.PositiveIntegerField(default=0)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    transaction = models.ForeignKey(
        Transaction,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="linked_subscriptions",
    )
    plan_tier = models.CharField(max_length=30, choices=SubscriptionTier.choices, blank=True, null=True)
    order_id = models.CharField(max_length=120, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class CoachingRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coaching_requests",
    )
    first_name = models.CharField(max_length=120)
    last_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=40)
    gender = models.CharField(max_length=10, choices=Gender.choices, blank=True, null=True)
    situation = models.TextField(blank=True, null=True)
    requested_date = models.DateField()
    time_slot = models.CharField(max_length=20, choices=TimeSlot.choices)
    theme = models.CharField(max_length=30, choices=CoachingTheme.choices)
    message = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=20,
        choices=CoachingStatus.choices,
        default=CoachingStatus.PENDING,
    )
    confirmed_date = models.DateTimeField(blank=True, null=True)
    meet_link = models.TextField(blank=True, null=True)
    payment_status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.PENDING,
    )
    payment_amount = models.PositiveIntegerField(default=26000)
    admin_notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reporter = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="reports_made")
    reported_profile = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_received",
    )
    reason = models.CharField(max_length=40, choices=ReportReason.choices)
    message = models.TextField(blank=True, null=True)
    admin_notes = models.TextField(blank=True, null=True)
    report_kind = models.CharField(
        max_length=20,
        choices=ReportKind.choices,
        default=ReportKind.PROFILE,
    )
    status = models.CharField(
        max_length=20,
        choices=ReportStatus.choices,
        default=ReportStatus.PENDING,
    )
    resolution = models.CharField(max_length=40, blank=True, null=True)
    admin_note = models.TextField(blank=True, null=True)
    resolved_by = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports_resolved",
    )
    reviewed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class BannedIdentity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    profile = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="banned_identities",
    )
    email_normalized = models.TextField(blank=True, null=True)
    phone_normalized = models.TextField(blank=True, null=True)
    reason = models.TextField(blank=True, null=True)
    banned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=models.Q(email_normalized__isnull=False) | models.Q(phone_normalized__isnull=False),
                name="banned_has_identifier",
            ),
        ]


class Testimonial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author_name = models.CharField(max_length=120)
    author_age = models.PositiveSmallIntegerField(blank=True, null=True)
    content = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    is_verified = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    user = models.ForeignKey(
        Profile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="testimonials",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]


class SiteSetting(models.Model):
    key = models.CharField(max_length=100, primary_key=True)
    value = models.JSONField(default=dict)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.key
