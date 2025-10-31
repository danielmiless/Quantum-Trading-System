"""Monte Carlo simulation utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Optional

import numpy as np
import pandas as pd


@dataclass(slots=True)
class SimulationResult:
    """Container for Monte Carlo simulation results."""

    simulated_paths: pd.DataFrame
    summary: dict[str, float]


class MonteCarloSimulator:
    """Monte Carlo engine for portfolio return generation."""

    def __init__(self, seed: Optional[int] = None) -> None:
        self.rng = np.random.default_rng(seed)

    def simulate_portfolio_returns(
        self,
        expected_returns: Iterable[float],
        cov_matrix: np.ndarray,
        periods: int,
        simulations: int = 10_000,
    ) -> SimulationResult:
        mean = np.array(list(expected_returns), dtype=float)
        if cov_matrix.shape[0] != cov_matrix.shape[1]:
            raise ValueError("Covariance matrix must be square")
        draws = self.rng.multivariate_normal(mean, cov_matrix, size=(simulations, periods))
        paths = pd.DataFrame(draws.reshape(simulations * periods, -1))
        portfolio_returns = paths.mean(axis=1)
        summary = {
            "mean": float(portfolio_returns.mean()),
            "std": float(portfolio_returns.std(ddof=0)),
            "var_95": float(-np.quantile(portfolio_returns, 0.05)),
        }
        return SimulationResult(paths, summary)

    def generate_risk_scenarios(
        self,
        base_returns: pd.Series,
        shocks: Mapping[str, float],
    ) -> pd.DataFrame:
        scenarios = {}
        for name, shock in shocks.items():
            scenarios[name] = base_returns + shock
        return pd.DataFrame(scenarios)

    def confidence_intervals(
        self,
        data: Iterable[float],
        confidence: float = 0.95,
    ) -> tuple[float, float]:
        series = pd.Series(list(data)).dropna()
        if series.empty:
            raise ValueError("Data cannot be empty for confidence intervals")
        alpha = (1 - confidence) / 2
        lower = float(series.quantile(alpha))
        upper = float(series.quantile(1 - alpha))
        return lower, upper

    def stress_test(
        self,
        portfolio_weights: Mapping[str, float],
        scenario_matrix: pd.DataFrame,
    ) -> pd.Series:
        weights = pd.Series(portfolio_weights, dtype=float)
        weights = weights / weights.sum()
        aligned = scenario_matrix.reindex(weights.index, axis=0).fillna(0.0)
        losses = aligned.mul(weights, axis=0).sum(axis=0)
        return losses


__all__ = ["MonteCarloSimulator", "SimulationResult"]

