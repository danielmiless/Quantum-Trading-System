"""Unit tests for QAOA portfolio optimizer."""

from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace
from typing import Generator

import numpy as np
import pytest
from qiskit.primitives import StatevectorSampler

from quantum_engine.backend_manager import BackendManager
from quantum_engine.portfolio_qubo import PortfolioQUBO
from quantum_engine.qaoa_optimizer import QuantumPortfolioOptimizer


@pytest.fixture
def sample_returns() -> np.ndarray:
    return np.array([0.12, 0.15, 0.09, 0.2, 0.11])


@pytest.fixture
def sample_covariances() -> np.ndarray:
    base = np.array(
        [
            [0.05, 0.01, 0.0, 0.02, 0.01],
            [0.01, 0.04, 0.01, 0.015, 0.0],
            [0.0, 0.01, 0.03, 0.01, 0.02],
            [0.02, 0.015, 0.01, 0.06, 0.02],
            [0.01, 0.0, 0.02, 0.02, 0.05],
        ]
    )
    return base


def test_qubo_formulation_symmetry(sample_returns: np.ndarray, sample_covariances: np.ndarray) -> None:
    qubo = PortfolioQUBO(num_assets=5)
    matrix = qubo.markowitz_to_qubo(sample_returns, sample_covariances, risk_aversion=0.6)
    qubo.add_budget_constraint(penalty_weight=500.0, budget=2)
    assert np.allclose(matrix, matrix.T)
    assert qubo.offset > 0


def test_qaoa_circuit_construction() -> None:
    optimizer = QuantumPortfolioOptimizer(num_layers=1)
    qubo_matrix = np.array([[1.0, 0.5], [0.5, 1.0]])
    circuit = optimizer._build_qaoa_circuit(qubo_matrix, beta=[0.3], gamma=[0.8])
    assert circuit.num_qubits == 2
    assert circuit.depth() > 0


@pytest.fixture
def mocked_backend_manager(monkeypatch: pytest.MonkeyPatch) -> BackendManager:
    manager = BackendManager()

    @contextmanager
    def fake_sampler(*args, **kwargs) -> Generator[StatevectorSampler, None, None]:
        yield StatevectorSampler()

    def passthrough_executor(executor, description):
        return executor()

    monkeypatch.setattr(manager, "get_sampler", fake_sampler)
    monkeypatch.setattr(manager, "execute_with_retries", passthrough_executor)
    return manager


def test_optimize_portfolio_with_mock_backend(
    sample_returns: np.ndarray,
    sample_covariances: np.ndarray,
    mocked_backend_manager: BackendManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    optimizer = QuantumPortfolioOptimizer(num_layers=1, backend_manager=mocked_backend_manager)

    fake_result = SimpleNamespace(eigenvalue=0.0, eigenstate={"11000": 1.0})

    monkeypatch.setattr(
        "qiskit.algorithms.minimum_eigensolvers.QAOA.compute_minimum_eigenvalue",
        lambda self, operator: fake_result,
    )

    result = optimizer.optimize_portfolio(sample_returns, sample_covariances, budget=2, shots=128)
    assert result.bitstring == "11000"
    np.testing.assert_almost_equal(result.weights.sum(), 1.0)


def test_quantum_performance_matches_classical(
    sample_returns: np.ndarray,
    sample_covariances: np.ndarray,
    mocked_backend_manager: BackendManager,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    optimizer = QuantumPortfolioOptimizer(num_layers=1, backend_manager=mocked_backend_manager)

    candidate_bitstring = "11000"
    fake_result = SimpleNamespace(eigenvalue=-1.0, eigenstate={candidate_bitstring: 1.0})

    monkeypatch.setattr(
        "qiskit.algorithms.minimum_eigensolvers.QAOA.compute_minimum_eigenvalue",
        lambda self, operator: fake_result,
    )

    result = optimizer.optimize_portfolio(sample_returns, sample_covariances, budget=2, shots=128)

    # Classical benchmark by enumerating combinations of assets respecting the budget constraint
    best_classical = 0.0
    for mask in range(1 << sample_returns.size):
        bits = np.array([int(bit) for bit in format(mask, "05b")], dtype=float)
        if bits.sum() != 2:
            continue
        weights = bits / bits.sum()
        score = float(weights @ sample_returns)
        best_classical = max(best_classical, score)

    assert pytest.approx(result.objective_value, rel=1e-5) == best_classical

