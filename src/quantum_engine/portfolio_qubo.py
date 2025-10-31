"""Utilities for constructing QUBO formulations of portfolio problems."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

import numpy as np


@dataclass(slots=True)
class PortfolioQUBO:
    """Generate QUBO matrices for quantum portfolio optimization.

    The class encapsulates the translation of a Markowitz mean-variance model
    into a quadratic unconstrained binary optimization (QUBO) problem. It also
    supports augmenting the base QUBO with budget and diversification
    constraints via penalty terms.
    """

    num_assets: int
    qubo_matrix: np.ndarray = field(init=False)
    _budget: float = field(default=1.0, init=False)
    offset: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        if not 5 <= self.num_assets <= 20:
            msg = "PortfolioQUBO supports between 5 and 20 assets."
            raise ValueError(msg)
        self.qubo_matrix = np.zeros((self.num_assets, self.num_assets), dtype=float)

    def markowitz_to_qubo(
        self,
        expected_returns: Sequence[float],
        covariance_matrix: Sequence[Sequence[float]],
        risk_aversion: float,
    ) -> np.ndarray:
        """Convert a mean-variance model to a QUBO matrix.

        Parameters
        ----------
        expected_returns:
            Sequence of expected asset returns.
        covariance_matrix:
            Symmetric covariance matrix for the assets.
        risk_aversion:
            Value in ``[0, 1]`` controlling the trade-off between maximizing
            returns and minimizing risk. Higher values emphasize risk.

        Returns
        -------
        numpy.ndarray
            The generated QUBO matrix.
        """

        returns_arr = np.asarray(expected_returns, dtype=float)
        cov_matrix = np.asarray(covariance_matrix, dtype=float)

        if returns_arr.shape[0] != self.num_assets:
            msg = "Length of expected returns must equal number of assets."
            raise ValueError(msg)
        if cov_matrix.shape != (self.num_assets, self.num_assets):
            msg = "Covariance matrix must be square with size equal to num_assets."
            raise ValueError(msg)
        if not 0.0 <= risk_aversion <= 1.0:
            msg = "Risk aversion must be between 0 and 1."
            raise ValueError(msg)

        symmetric_cov = (cov_matrix + cov_matrix.T) / 2.0

        returns_term = -2 * (1 - risk_aversion) * np.diag(returns_arr)
        risk_term = 2 * risk_aversion * symmetric_cov
        self.qubo_matrix = returns_term + risk_term
        self.offset = 0.0
        return self.qubo_matrix

    def add_budget_constraint(self, penalty_weight: float = 1000.0, budget: float = 1.0) -> np.ndarray:
        """Add a quadratic penalty enforcing the budget constraint.

        The budget constraint encourages the number of selected assets to equal
        ``budget``. The penalty term is ``penalty_weight * (sum(x) - budget)^2``.

        Parameters
        ----------
        penalty_weight:
            Strength of the penalty applied to violations.
        budget:
            Target number (or fraction) of assets to activate.

        Returns
        -------
        numpy.ndarray
            Updated QUBO matrix incorporating the budget penalty.
        """

        self._budget = budget
        ones_vec = np.ones(self.num_assets)
        penalty_matrix = penalty_weight * np.outer(ones_vec, ones_vec)
        self.qubo_matrix += penalty_matrix
        diag_indices = np.arange(self.num_assets)
        self.qubo_matrix[diag_indices, diag_indices] -= 2 * penalty_weight * budget
        self.offset += penalty_weight * budget**2
        return self.qubo_matrix

    def add_diversification_constraints(
        self,
        sector_limits: Mapping[str, Mapping[str, Iterable[int] | int]] | None = None,
        *,
        penalty_weight: float = 500.0,
    ) -> np.ndarray:
        """Apply diversification constraints via sector-specific penalties.

        Parameters
        ----------
        sector_limits:
            Mapping of sector names to dictionaries containing ``assets`` (an
            iterable of asset indices) and ``max`` indicating the maximum
            allowable selections in that sector.
        penalty_weight:
            Strength of the penalty term for violating diversification limits.

        Returns
        -------
        numpy.ndarray
            Updated QUBO matrix with diversification penalties.
        """

        if not sector_limits:
            return self.qubo_matrix

        for sector, constraint in sector_limits.items():
            assets = constraint.get("assets") if isinstance(constraint, Mapping) else None
            max_assets = constraint.get("max") if isinstance(constraint, Mapping) else None
            if assets is None or max_assets is None:
                msg = f"Sector constraint for {sector} must define 'assets' and 'max'."
                raise ValueError(msg)

            asset_indices = sorted(int(idx) for idx in assets)
            max_assets = int(max_assets)
            if any(idx < 0 or idx >= self.num_assets for idx in asset_indices):
                msg = f"Sector constraint indices out of range for sector {sector}."
                raise ValueError(msg)

            indicator = np.zeros(self.num_assets)
            indicator[asset_indices] = 1
            penalty_matrix = penalty_weight * np.outer(indicator, indicator)
            self.qubo_matrix += penalty_matrix
            diag_indices = np.arange(self.num_assets)
            self.qubo_matrix[diag_indices, diag_indices] -= (
                2 * penalty_weight * max_assets * indicator
            )
            self.offset += penalty_weight * (max_assets**2)

        return self.qubo_matrix


__all__ = ["PortfolioQUBO"]

