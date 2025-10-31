"""Notification routing for trading alerts."""

from __future__ import annotations

import smtplib
from dataclasses import dataclass, field
from email.message import EmailMessage
from pathlib import Path
from typing import Callable, Iterable, List, Mapping, Optional

import requests
from loguru import logger


DesktopNotifier = Callable[[str, str], None]
SMSNotifier = Callable[[str, str], None]


@dataclass(slots=True)
class NotificationChannel:
    name: str
    callback: Callable[[str, str], None]
    level: str = "info"


class NotificationManager:
    """Dispatch notifications across email, webhooks, and desktop alerts."""

    def __init__(self) -> None:
        self.channels: List[NotificationChannel] = []

    # ------------------------------------------------------------------
    # Channel registration
    # ------------------------------------------------------------------
    def register_channel(self, name: str, callback: Callable[[str, str], None], level: str = "info") -> None:
        self.channels.append(NotificationChannel(name, callback, level))
        logger.debug("Registered notification channel {}", name)

    def register_email(
        self,
        smtp_server: str,
        port: int,
        sender: str,
        password: str,
        recipients: Iterable[str],
    ) -> None:
        def send_email(level: str, message: str) -> None:
            email = EmailMessage()
            email["From"] = sender
            email["To"] = ", ".join(recipients)
            email["Subject"] = f"Quantum Trading Alert [{level.upper()}]"
            email.set_content(message)
            try:
                with smtplib.SMTP_SSL(smtp_server, port) as server:
                    server.login(sender, password)
                    server.send_message(email)
            except Exception as exc:  # noqa: BLE001
                logger.error("Failed to send email notification: {}", exc)

        self.register_channel("email", send_email, level="warning")

    def register_webhook(self, url: str, level: str = "info") -> None:
        def send_webhook(event_level: str, message: str) -> None:
            payload = {"text": f"[{event_level.upper()}] {message}"}
            try:
                response = requests.post(url, json=payload, timeout=5)
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.error("Webhook notification failed: {}", exc)

        self.register_channel("webhook", send_webhook, level=level)

    def register_desktop(self, notifier: Optional[DesktopNotifier] = None) -> None:
        def default_desktop(level: str, message: str) -> None:
            logger.info("Desktop notification [{}]: {}", level.upper(), message)

        self.register_channel("desktop", notifier or default_desktop)

    def register_sms(self, notifier: SMSNotifier) -> None:
        self.register_channel("sms", notifier, level="critical")

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------
    def notify(self, level: str, message: str) -> None:
        logger.info("Notification [{}]: {}", level.upper(), message)
        for channel in self.channels:
            if self._level_priority(level) >= self._level_priority(channel.level):
                channel.callback(level, message)

    @staticmethod
    def _level_priority(level: str) -> int:
        mapping = {"info": 1, "warning": 2, "risk": 3, "critical": 4}
        return mapping.get(level.lower(), 1)


__all__ = ["NotificationManager", "NotificationChannel"]

