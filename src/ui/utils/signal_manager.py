"""Centralized signal manager for coordinating UI events."""

from __future__ import annotations

from typing import Optional

from PySide6.QtCore import QObject, Signal


class SignalManager(QObject):
    """Singleton object broadcasting application-wide signals."""

    _instance: Optional["SignalManager"] = None

    quantum_job_started = Signal(str)
    quantum_job_progress = Signal(int, str)
    quantum_job_completed = Signal(dict)
    quantum_job_failed = Signal(str)
    quantum_job_cancelled = Signal(str)

    portfolio_updated = Signal(dict)
    portfolio_error = Signal(str)

    notification = Signal(str, str)  # level, message

    def __new__(cls, *args, **kwargs) -> "SignalManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance

    @classmethod
    def instance(cls) -> "SignalManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance


__all__ = ["SignalManager"]

