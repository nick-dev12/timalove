"""Nettoie le journal Monitoring des erreurs non bloquantes."""

from django.core.management.base import BaseCommand

from core.controllers import monitoring_controller


class Command(BaseCommand):
    help = "Supprime les Http404, doublons django.request et autres bruits du Monitoring."

    def handle(self, *args, **options):
        deleted = monitoring_controller.prune_benign_events()
        self.stdout.write(self.style.SUCCESS(f"{deleted} événement(s) non bloquant(s) supprimé(s)."))
