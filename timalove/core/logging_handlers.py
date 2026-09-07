"""Handler logging → SystemEvent (Monitoring)."""

from __future__ import annotations

import logging
import traceback


class SystemEventLogHandler(logging.Handler):
    """Persiste les logs ERROR/CRITICAL dans SystemEvent."""

    # Bruit scanners / Host invalides — pas utile dans Monitoring
    IGNORE_MESSAGE_SNIPPETS = (
        "Invalid HTTP_HOST header",
        "DisallowedHost",
        "You're accessing the development server over HTTPS",
    )

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno < logging.ERROR:
            return
        # Évite le bruit / récursion
        if record.name.startswith("django.db") or "monitoring_controller" in record.name:
            return
        if record.name in {"django.security.DisallowedHost", "django.security"}:
            return
        try:
            msg_preview = record.getMessage() if hasattr(record, "getMessage") else str(record.msg)
        except Exception:  # noqa: BLE001
            msg_preview = str(record.msg)
        if any(s in msg_preview for s in self.IGNORE_MESSAGE_SNIPPETS):
            return
        try:
            from core.controllers import monitoring_controller
            from core.models.system_event import SystemEvent

            tb_text = ""
            if record.exc_info:
                tb_text = "".join(traceback.format_exception(*record.exc_info))
            msg = self.format(record)
            source = SystemEvent.Source.LOGGING
            name = record.name or ""
            if "payment" in name or "naboo" in name or "cinetpay" in name:
                source = SystemEvent.Source.PAYMENT
            elif "email" in name:
                source = SystemEvent.Source.EMAIL
            elif "push" in name or "fcm" in name:
                source = SystemEvent.Source.PUSH
            elif "celery" in name:
                source = SystemEvent.Source.CELERY

            level = SystemEvent.Level.CRITICAL if record.levelno >= logging.CRITICAL else SystemEvent.Level.ERROR
            exception_type = ""
            if record.exc_info and record.exc_info[0]:
                exception_type = record.exc_info[0].__name__
            if exception_type == "DisallowedHost":
                return
            monitoring_controller.record_event(
                level=level,
                source=source,
                title=(record.getMessage() or str(record.msg) or "Erreur applicative")[:220],
                message=msg,
                exception_type=exception_type,
                location=f"{record.pathname.replace(chr(92), '/').split('/')[-1]}:{record.lineno}",
                traceback_text=tb_text,
                metadata={"logger": record.name, "func": record.funcName},
            )
        except Exception:  # noqa: BLE001
            self.handleError(record)
