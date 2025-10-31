"""Quantum backend management utilities."""

from __future__ import annotations

import math
import os
import time
from contextlib import contextmanager
from typing import Any, Callable, Generator

from loguru import logger

try:  # Optional IBM Quantum runtime imports
    from qiskit_ibm_runtime import (
        QiskitRuntimeService,
        Sampler,
        Session,
        Options,
    )
except Exception:  # pragma: no cover - import fallback path
    QiskitRuntimeService = None  # type: ignore[assignment]
    Sampler = None  # type: ignore[assignment]
    Session = None  # type: ignore[assignment]
    Options = None  # type: ignore[assignment]

try:  # Local simulator sampler
    from qiskit_aer.primitives import Sampler as AerSampler
except Exception:  # pragma: no cover - import fallback path
    AerSampler = None  # type: ignore[assignment]

from qiskit.primitives import Sampler as ReferenceSampler

from utils.logger import log_quantum_job


class BackendManager:
    """Manage IBM Quantum backends with robust fallbacks.

    The manager encapsulates authentication, backend selection, cost tracking,
    and retry policies for executing quantum workloads. When IBM Quantum
    services are unavailable, it transparently falls back to the local Aer
    simulator or the reference statevector sampler.
    """

    def __init__(
        self,
        *,
        prefer_hardware: bool = False,
        max_retries: int = 3,
        price_per_shot: float = 1e-4,
    ) -> None:
        self.prefer_hardware = prefer_hardware
        self.max_retries = max_retries
        self.price_per_shot = price_per_shot
        self._service: QiskitRuntimeService | None = None
        self._total_cost: float = 0.0

    @property
    def total_cost(self) -> float:
        """Aggregate estimated quantum execution cost."""

        return self._total_cost

    def _authenticate(self) -> QiskitRuntimeService | None:
        if QiskitRuntimeService is None:
            logger.warning("QiskitRuntimeService not available; using simulator fallback")
            return None

        if self._service is not None:
            return self._service

        token = os.getenv("IBM_QUANTUM_TOKEN")
        if not token:
            logger.info("IBM_QUANTUM_TOKEN not found; defaulting to simulator")
            return None

        channel = os.getenv("IBM_QUANTUM_CHANNEL", "ibm_quantum")
        instance = os.getenv("IBM_QUANTUM_INSTANCE")

        try:
            self._service = QiskitRuntimeService(
                channel=channel,
                token=token,
                instance=instance,
            )
            logger.success("Authenticated with IBM Quantum Runtime (channel={})", channel)
        except Exception as exc:  # pragma: no cover
            logger.error("Unable to authenticate with IBM Quantum Runtime: {}", exc)
            self._service = None
        return self._service

    def _select_backend(
        self,
        service: QiskitRuntimeService,
        num_qubits: int,
        *,
        prefer_hardware: bool,
    ) -> str:
        try:
            candidates = service.backends()
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to retrieve IBM backends: {}", exc)
            raise

        filtered = [
            backend
            for backend in candidates
            if backend.configuration().num_qubits >= num_qubits
        ]

        if not filtered:
            raise RuntimeError("No IBM Quantum backends support the requested qubit count")

        if prefer_hardware:
            hardware = [b for b in filtered if not b.configuration().simulator]
            if hardware:
                backend = min(
                    hardware,
                    key=lambda b: getattr(getattr(b, "status", lambda: None)(), "pending_jobs", math.inf),
                )
                logger.info("Selected hardware backend {}", backend.name)
                return backend.name

        backend = min(
            filtered,
            key=lambda b: getattr(getattr(b, "status", lambda: None)(), "pending_jobs", math.inf),
        )
        pending = getattr(getattr(backend, "status", lambda: None)(), "pending_jobs", "unknown")
        logger.info("Selected backend {} with pending jobs {}", backend.name, pending)
        return backend.name

    @contextmanager
    def get_sampler(
        self,
        num_qubits: int,
        *,
        shots: int = 2048,
        prefer_hardware: bool | None = None,
    ) -> Generator[Any, None, None]:
        """Provide a sampler primitive with automatic backend selection.

        Parameters
        ----------
        num_qubits:
            Number of qubits required for the circuits.
        shots:
            Number of shots for execution.
        prefer_hardware:
            Override the default hardware preference for this call.
        """

        session: Session | None = None
        sampler: Any
        backend_name: str | None = None

        preference = self.prefer_hardware if prefer_hardware is None else prefer_hardware

        service = self._authenticate()
        if service is not None and Sampler is not None and Options is not None:
            try:
                backend_name = self._select_backend(
                    service,
                    num_qubits,
                    prefer_hardware=preference,
                )
                session = Session(service=service, backend=backend_name)
                options = Options()
                options.execution.shots = shots
                sampler = Sampler(session=session, options=options)
                estimated_cost = shots * self.price_per_shot
                self._total_cost += estimated_cost
                log_quantum_job(
                    "sampler_initialized",
                    backend=backend_name,
                    shots=shots,
                    estimated_cost=estimated_cost,
                    preference="hardware" if preference else "simulator",
                )
            except Exception as exc:  # pragma: no cover - fall back path
                logger.warning("Falling back to simulator due to backend error: {}", exc)
                session = None
                sampler = self._fallback_sampler(shots=shots)
        else:
            sampler = self._fallback_sampler(shots=shots)

        try:
            yield sampler
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception as exc:  # pragma: no cover
                    logger.warning("Failed to close IBM Quantum session: {}", exc)

    def _fallback_sampler(self, shots: int) -> Any:
        use_aer = os.getenv("QPO_ENABLE_AER", "").lower() in {"1", "true", "yes"}
        if use_aer and AerSampler is not None:
            logger.info("Using AerSampler fallback with {} shots", shots)
            sampler = AerSampler()
            try:
                sampler.options.shots = shots  # type: ignore[attr-defined]
            except AttributeError:  # pragma: no cover - legacy interface
                try:
                    sampler.set_options(shots=shots)  # type: ignore[call-arg]
                except AttributeError:
                    logger.warning("AerSampler does not expose options API; using defaults")
            return sampler

        logger.info("Using reference Sampler fallback with {} shots", shots)
        sampler = ReferenceSampler()
        try:
            sampler.options.shots = shots  # type: ignore[attr-defined]
        except AttributeError:  # pragma: no cover - older versions
            try:
                sampler.set_options(shots=shots)  # type: ignore[call-arg]
            except AttributeError:
                logger.debug("ReferenceSampler ignoring shots configuration")
        return sampler

    def monitor_job(
        self,
        job: Any,
        *,
        poll_interval: float = 5.0,
        timeout: float = 600.0,
    ) -> Any:
        """Monitor a quantum job until completion or timeout."""

        start_time = time.time()
        while True:
            status = job.status()
            job_id_attr = getattr(job, "job_id", None)
            job_id = job_id_attr() if callable(job_id_attr) else job_id_attr
            queue_attr = getattr(job, "queue_position", None)
            queue_position = queue_attr() if callable(queue_attr) else queue_attr
            log_quantum_job(
                "status_update",
                job_id=job_id,
                status=str(status),
                queue_position=queue_position,
            )
            if status.name in {"DONE", "ERROR", "CANCELLED"}:
                break
            if time.time() - start_time > timeout:
                raise TimeoutError("Quantum job monitoring timed out")
            time.sleep(poll_interval)
        return job.result()

    def execute_with_retries(self, executor: Callable[[], Any], description: str) -> Any:
        """Execute a callable with retry semantics for robustness."""

        attempt = 0
        last_exception: Exception | None = None
        while attempt < self.max_retries:
            attempt += 1
            try:
                logger.info("Attempt {} for {}", attempt, description)
                return executor()
            except Exception as exc:  # pragma: no cover - runtime specific
                last_exception = exc
                logger.error("Execution attempt {} failed for {}: {}", attempt, description, exc)
                time.sleep(min(2**attempt, 30))

        assert last_exception is not None  # for mypy
        raise RuntimeError(f"All retries failed for {description}") from last_exception


__all__ = ["BackendManager"]

