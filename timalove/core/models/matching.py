"""Matching, swipes, messages, blocks."""

from __future__ import annotations

import uuid

from django.db import models

from .choices import MatchStatus, MessageType, SwipeAction
from .profile import Profile


class Swipe(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    swiper = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="swipes_made")
    swiped = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="swipes_received")
    is_like = models.BooleanField(default=False)
    is_super_like = models.BooleanField(default=False)
    action = models.CharField(max_length=20, choices=SwipeAction.choices, default=SwipeAction.PASS)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["swiper", "swiped"], name="unique_swipe_pair"),
        ]
        indexes = [
            models.Index(fields=["swiper", "swiped"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.swiper_id} → {self.swiped_id} ({self.action})"


class Match(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user_1 = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="matches_as_user1")
    user_2 = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="matches_as_user2")
    status = models.CharField(max_length=20, choices=MatchStatus.choices, default=MatchStatus.ACTIVE)
    is_one_sided = models.BooleanField(
        default=False,
        help_text="Conversation ouverte après like envoyé, sans like retour.",
    )
    user_1_message_count = models.PositiveIntegerField(default=0)
    user_2_message_count = models.PositiveIntegerField(default=0)
    scheduled_date = models.DateTimeField(blank=True, null=True)
    meet_link = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user_1", "user_2"], name="unique_match_pair"),
            models.CheckConstraint(condition=~models.Q(user_1=models.F("user_2")), name="no_self_match"),
        ]
        indexes = [
            models.Index(fields=["user_1"]),
            models.Index(fields=["user_2"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"Match {self.user_1_id} / {self.user_2_id}"

    def partner_of(self, profile: Profile) -> Profile:
        return self.user_2 if self.user_1_id == profile.id else self.user_1

    def is_participant(self, profile: Profile) -> bool:
        return profile.id in {self.user_1_id, self.user_2_id}


class Message(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="messages_sent")
    content = models.TextField(blank=True, default="")
    message_type = models.CharField(max_length=20, choices=MessageType.choices, default=MessageType.TEXT)
    voice_url = models.TextField(blank=True, null=True)
    voice_duration_seconds = models.PositiveIntegerField(blank=True, null=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)
    is_flagged = models.BooleanField(default=False)
    original_content = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        indexes = [
            models.Index(fields=["match", "created_at"]),
            models.Index(fields=["sender"]),
        ]

    def __str__(self) -> str:
        return f"Msg {self.id} ({self.message_type})"


class ConversationHide(models.Model):
    user = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="hidden_conversations")
    partner = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="hidden_by")
    hidden_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "partner"], name="unique_conversation_hide"),
            models.CheckConstraint(condition=~models.Q(user=models.F("partner")), name="no_self_hide"),
        ]

    def __str__(self) -> str:
        return f"Hide {self.user_id} / {self.partner_id}"


class BlockedUser(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    blocker = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="blocks_made")
    blocked = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="blocks_received")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["blocker", "blocked"], name="unique_block"),
            models.CheckConstraint(condition=~models.Q(blocker=models.F("blocked")), name="no_self_block"),
        ]

    def __str__(self) -> str:
        return f"Block {self.blocker_id} → {self.blocked_id}"
