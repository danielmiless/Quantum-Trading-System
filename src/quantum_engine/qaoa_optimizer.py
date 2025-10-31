"""QAOA-based quantum portfolio optimization engine."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
from loguru import logger
from qiskit import QuantumCircuit
from qiskit_algorithms.minimum_eigensolvers import QAOA
from qiskit_algorithms.optimizers import COBYLA
from qiskit.quantum_info import SparsePauliOp
from qiskit.result import QuasiDistribution

from .backend_manager import BackendManager
from .portfolio_qubo import PortfolioQUBO
from utils.logger import log_performance_metric


@dataclass(slots=True)
class OptimizationResult:
    """Container for QAOA optimization outcomes."""

    weights: np.ndarray
    bitstring: str
    objective_value: float
    eigenvalue: float
    metadata: dict[str, object]


class QuantumPortfolioOptimizer:
    """Optimize portfolios using Quantum Approximate Optimization Algorithm."""

    def __init__(
        self,
        *,
        risk_factor: float = 0.5,
        num_layers: int = 2,
        optimizer_maxiter: int = 200,
        backend_manager: BackendManager | None = None,
    ) -> None:
        if not 0.0 <= risk_factor <= 1.0:
            msg = "risk_factor must be between 0 and 1"
            raise ValueError(msg)
        if num_layers <= 0:
            msg = "num_layers must be positive"
            raise ValueError(msg)

        self.risk_factor = risk_factor
        self.num_layers = num_layers
        self.optimizer_maxiter = optimizer_maxiter
        self.backend_manager = backend_manager or BackendManager()

    def optimize_portfolio(
        self,
        returns: Sequence[float],
        covariances: Sequence[Sequence[float]],
        *,
        budget: float = 1.0,
        sector_limits: dict[str, dict[str, Iterable[int] | int]] | None = None,
        shots: int = 2048,
    ) -> OptimizationResult:
        """Find optimal portfolio weights using QAOA.

        Parameters
        ----------
        returns:
            Expected asset returns.
        covariances:
            Covariance matrix for the assets.
        budget:
            Target count (or proportion) of assets to allocate capital to.
        sector_limits:
            Optional diversification constraints by sector.
        shots:
            Number of measurement shots for the quantum primitive.
        """

        start_time = time.perf_counter()
        returns_arr = np.asarray(returns, dtype=float)
        num_assets = returns_arr.shape[0]

        if not 5 <= num_assets <= 20:
            msg = "QuantumPortfolioOptimizer supports portfolios of 5-20 assets"
            raise ValueError(msg)

        if budget <= 0:
            msg = "budget must be positive"
            raise ValueError(msg)

        portfolio_qubo = PortfolioQUBO(num_assets)
        qubo_matrix = portfolio_qubo.markowitz_to_qubo(returns_arr, covariances, self.risk_factor)
        qubo_matrix = portfolio_qubo.add_budget_constraint(penalty_weight=1000.0, budget=budget)
        qubo_matrix = portfolio_qubo.add_diversification_constraints(
            sector_limits=sector_limits,
            penalty_weight=750.0,
        )

        h, j_matrix, offset = self._qubo_to_ising(qubo_matrix)
        offset += portfolio_qubo.offset
        logger.debug("Converted QUBO to Ising: h={}, offset={}", h.tolist(), offset)

        operator = self._ising_to_pauli(h, j_matrix, offset)
        initial_point = np.concatenate(
            [np.full(self.num_layers, 0.1), np.full(self.num_layers, 0.1)]
        )

        optimizer = COBYLA(maxiter=self.optimizer_maxiter, tol=1e-3)

        with self.backend_manager.get_sampler(num_qubits=num_assets, shots=shots) as sampler:
            qaoa = QAOA(
                sampler=sampler,
                optimizer=optimizer,
                reps=self.num_layers,
                initial_point=initial_point,
            )

            result = self.backend_manager.execute_with_retries(
                lambda: qaoa.compute_minimum_eigenvalue(operator),
                description="QAOA minimum eigenvalue computation",
            )

        eigen_distribution = self._extract_distribution(result.eigenstate, num_assets)
        best_bitstring, probability = self._select_bitstring(eigen_distribution, num_assets)
        weights = self._bitstring_to_weights(best_bitstring)
        objective = float(weights @ returns_arr)

        elapsed = time.perf_counter() - start_time
        log_performance_metric(
            "qaoa_execution_time",
            elapsed,
            assets=num_assets,
            shots=shots,
            probability=probability,
        )

        metadata = {
            "optimizer_eigenvalue": result.eigenvalue,
            "eigen_distributions": eigen_distribution,
            "execution_time": elapsed,
            "total_cost": self.backend_manager.total_cost,
        }

        logger.success(
            "QAOA optimization completed (bitstring={}, objective={}, eigenvalue={})",
            best_bitstring,
            objective,
            result.eigenvalue,
        )

        return OptimizationResult(
            weights=weights,
            bitstring=best_bitstring,
            objective_value=objective,
            eigenvalue=float(result.eigenvalue.real),
            metadata=metadata,
        )

    def _build_qaoa_circuit(
        self,
        qubo_matrix: np.ndarray,
        beta: Sequence[float],
        gamma: Sequence[float],
    ) -> QuantumCircuit:
        """Construct a parameterized QAOA circuit for the provided QUBO."""

        if len(beta) != self.num_layers or len(gamma) != self.num_layers:
            msg = "beta and gamma must match the configured number of layers"
            raise ValueError(msg)

        num_qubits = qubo_matrix.shape[0]
        h, j_matrix, _ = self._qubo_to_ising(qubo_matrix)
        circuit = QuantumCircuit(num_qubits)
        circuit.h(range(num_qubits))

        for layer in range(self.num_layers):
            gamma_l = gamma[layer]
            beta_l = beta[layer]

            for i in range(num_qubits):
                if abs(h[i]) > 1e-9:
                    circuit.rz(2 * gamma_l * h[i], i)

            for i in range(num_qubits - 1):
                for j in range(i + 1, num_qubits):
                    if abs(j_matrix[i, j]) > 1e-9:
                        circuit.cx(i, j)
                        circuit.rz(2 * gamma_l * j_matrix[i, j], j)
                        circuit.cx(i, j)

            for i in range(num_qubits):
                circuit.rx(2 * beta_l, i)

        return circuit

    def _ising_to_pauli(
        self,
        h: np.ndarray,
        j_matrix: np.ndarray,
        offset: float,
    ) -> SparsePauliOp:
        terms: list[tuple[str, float]] = []
        num_qubits = h.shape[0]

        for i, coeff in enumerate(h):
            if abs(coeff) > 1e-12:
                label = ["I"] * num_qubits
                label[i] = "Z"
                terms.append(("".join(label), coeff))

        for i in range(num_qubits - 1):
            for j in range(i + 1, num_qubits):
                coeff = j_matrix[i, j]
                if abs(coeff) > 1e-12:
                    label = ["I"] * num_qubits
                    label[i] = "Z"
                    label[j] = "Z"
                    terms.append(("".join(label), coeff))

        operator = SparsePauliOp.from_list(terms) if terms else SparsePauliOp([("I" * num_qubits, 0.0)])
        if abs(offset) > 1e-12:
            operator = operator + SparsePauliOp.from_list([("I" * num_qubits, offset)])
        return operator

    def _extract_distribution(
        self,
        eigenstate: QuasiDistribution | dict[str, float] | None,
        num_qubits: int,
    ) -> dict[str, float]:
        if eigenstate is None:
            return {}
        if isinstance(eigenstate, QuasiDistribution):
            return eigenstate.binary_probabilities(num_bits=num_qubits)
        return {str(key): float(value) for key, value in eigenstate.items()}

    def _select_bitstring(self, distribution: dict[str, float], num_qubits: int) -> tuple[str, float]:
        if not distribution:
            logger.warning("Empty eigenstate distribution; defaulting to all zeros")
            return "0" * num_qubits, 0.0
        best = max(distribution.items(), key=lambda item: item[1])
        return best[0], float(best[1])

    def _bitstring_to_weights(self, bitstring: str) -> np.ndarray:
        bits = np.array([int(bit) for bit in bitstring], dtype=float)
        if bits.size == 0:
            return bits
        if bits.sum() == 0:
            return np.full(bits.shape, 1.0 / bits.size)
        return bits / bits.sum()

    def _qubo_to_ising(self, qubo_matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
        num_qubits = qubo_matrix.shape[0]
        symmetric_qubo = (qubo_matrix + qubo_matrix.T) / 2.0
        h = np.zeros(num_qubits)
        j_matrix = np.zeros((num_qubits, num_qubits))
        offset = 0.0

        for i in range(num_qubits):
            h[i] += symmetric_qubo[i, i] / 2.0
            offset += symmetric_qubo[i, i] / 2.0
            for j in range(i + 1, num_qubits):
                q = symmetric_qubo[i, j]
                h[i] += q / 4.0
                h[j] += q / 4.0
                j_matrix[i, j] = q / 4.0
                offset += q / 4.0

        return h, j_matrix, offset


__all__ = ["QuantumPortfolioOptimizer", "OptimizationResult"]

