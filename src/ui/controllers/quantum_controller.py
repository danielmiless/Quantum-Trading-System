"""Controller coordinating quantum optimization tasks for the UI."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, List, Optional

from loguru import logger
from PySide6.QtCore import QObject, QThread, Signal

from quantum_engine.qaoa_optimizer import QuantumPortfolioOptimizer

from ..utils.signal_manager import SignalManager
from ..workers.quantum_worker import QuantumWorker


@dataclass(slots=True)
class QuantumJobConfig:
    """Configuration payload for a quantum optimization run."""

    risk_factor: float = 0.5
    num_layers: int = 2
    shots: int = 2_048
    budget: float = 1.0
    sector_limits: Optional[dict[str, dict[str, Any]]] = None


class QuantumController(QObject):
    """Bridge between UI components and the quantum optimization engine."""

    job_started = Signal(str)
    job_progress = Signal(int, str)
    job_completed = Signal(dict)
    job_failed = Signal(str)
    job_cancelled = Signal()

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._thread: QThread | None = None
        self._worker: QuantumWorker | None = None
        self._history: List[dict[str, Any]] = []
        self._signal_manager = SignalManager.instance()
        self._connect_signal_manager()

    def _connect_signal_manager(self) -> None:
        self._signal_manager.quantum_job_started.connect(self.job_started.emit)
        self._signal_manager.quantum_job_progress.connect(self.job_progress.emit)
        self._signal_manager.quantum_job_completed.connect(self._handle_completion)
        self._signal_manager.quantum_job_failed.connect(self._handle_failure)
        self._signal_manager.quantum_job_cancelled.connect(self._handle_cancelled)

    def start_optimization(
        self,
        returns: list[float],
        covariances: list[list[float]],
        config: QuantumJobConfig | None = None,
    ) -> None:
        """Kick off an asynchronous quantum optimization job."""

        if self._thread is not None and self._thread.isRunning():
            logger.warning("Quantum job already in progress; ignoring new request")
            self._signal_manager.notification.emit(
                "warning", "A quantum optimization is already running."
            )
            return

        job_config = config or QuantumJobConfig()

        optimizer = QuantumPortfolioOptimizer(
            risk_factor=job_config.risk_factor,
            num_layers=job_config.num_layers,
        )
        self._worker = QuantumWorker(
            optimizer=optimizer,
            returns=returns,
            covariances=covariances,
            budget=job_config.budget,
            sector_limits=job_config.sector_limits,
            shots=job_config.shots,
        )

        if os.getenv("QPO_SYNC_QUANTUM", "").lower() in {"1", "true", "yes"}:
            logger.debug("Running quantum optimization synchronously")
            self._worker.run()
            self._worker = None
            self._thread = None
            return

        self._thread = QThread(self)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.finished.connect(self._cleanup_thread)
        self._worker.finished.connect(self._thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)

        logger.debug("Starting quantum optimization thread")
        self._thread.start()

    def cancel_current_job(self) -> None:
        if self._worker is not None:
            logger.info("Cancelling active quantum job")
            self._worker.cancel()

    def _handle_completion(self, payload: dict[str, Any]) -> None:
        self._history.append({"status": "completed", "payload": payload})
        self.job_completed.emit(payload)

    def _handle_failure(self, reason: str) -> None:
        self._history.append({"status": "failed", "reason": reason})
        self.job_failed.emit(reason)

    def _handle_cancelled(self, message: str) -> None:
        self._history.append({"status": "cancelled", "reason": message})
        self.job_cancelled.emit()

    def _cleanup_thread(self) -> None:
        logger.debug("Cleaning up quantum worker thread")
        self._worker = None
        self._thread = None

    @property
    def history(self) -> List[dict[str, Any]]:
        return list(self._history)


__all__ = ["QuantumController", "QuantumJobConfig"]

