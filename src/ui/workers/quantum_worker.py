"""Background worker executing quantum optimization."""

from __future__ import annotations

import time
from typing import Any, Optional

from loguru import logger
from PySide6.QtCore import QObject, QRunnable, Signal

from quantum_engine.qaoa_optimizer import OptimizationResult, QuantumPortfolioOptimizer

from ..utils.signal_manager import SignalManager


class QuantumWorker(QObject, QRunnable):
    """QRunnable executing the quantum optimization in a background thread."""

    finished = Signal()

    def __init__(
        self,
        *,
        optimizer: QuantumPortfolioOptimizer,
        returns: list[float],
        covariances: list[list[float]],
        budget: float,
        sector_limits: Optional[dict[str, dict[str, Any]]],
        shots: int,
    ) -> None:
        QObject.__init__(self)
        QRunnable.__init__(self)
        self.optimizer = optimizer
        self.returns = returns
        self.covariances = covariances
        self.budget = budget
        self.sector_limits = sector_limits
        self.shots = shots
        self._cancelled = False
        self._signal_manager = SignalManager.instance()

    def run(self) -> None:  # type: ignore[override]
        job_id = f"job-{int(time.time())}"
        self._signal_manager.quantum_job_started.emit(job_id)
        try:
            self._emit_progress(5, "Preparing quantum optimization")
            if self._cancelled:
                self._signal_manager.quantum_job_cancelled.emit("Cancelled before start")
                return
            result = self._execute_optimization()
            if self._cancelled:
                self._signal_manager.quantum_job_cancelled.emit("Cancelled by user")
                return
            payload = self._format_result(result)
            self._signal_manager.quantum_job_completed.emit(payload)
        except Exception as exc:  # pragma: no cover - runtime safety
            logger.exception("Quantum optimization failed: {}", exc)
            self._signal_manager.quantum_job_failed.emit(str(exc))
        finally:
            self.finished.emit()

    def cancel(self) -> None:
        self._cancelled = True

    def _emit_progress(self, value: int, message: str) -> None:
        self._signal_manager.quantum_job_progress.emit(value, message)

    def _execute_optimization(self) -> OptimizationResult:
        self._emit_progress(20, "Running QAOA optimizer")
        result = self.optimizer.optimize_portfolio(
            returns=self.returns,
            covariances=self.covariances,
            budget=self.budget,
            sector_limits=self.sector_limits,
            shots=self.shots,
        )
        self._emit_progress(90, "Processing optimization results")
        return result

    def _format_result(self, result: OptimizationResult) -> dict[str, Any]:
        self._emit_progress(98, "Finalizing results")
        return {
            "weights": result.weights.tolist(),
            "bitstring": result.bitstring,
            "objective_value": result.objective_value,
            "eigenvalue": result.eigenvalue,
            "metadata": result.metadata,
        }


__all__ = ["QuantumWorker"]

