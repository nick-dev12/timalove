"""Tâches Celery."""

from __future__ import annotations

from celery import shared_task


@shared_task
def expire_subscriptions_and_boosts():
    from core.controllers import payment_controller

    return payment_controller.expire_subscriptions_and_boosts()


@shared_task
def send_email_task(to: str, subject: str, html: str):
    from core.controllers import email_controller

    return email_controller.send_email(to, subject, html)


@shared_task
def send_push_notification(notification_id: str, force: bool = False):
    from core.controllers import push_controller

    return push_controller.send_for_notification(notification_id, force=force)
