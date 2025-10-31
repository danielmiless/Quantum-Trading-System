"""Performance attribution utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Optional

import numpy as np
import pandas as pd


@dataclass(slots=True)
class ComparisonResult:
    """Output of a quantum versus classical comparison."""

    alpha: float
    beta: float
    information_ratio: float
    cumulative_difference: pd.Series


class PerformanceAnalyzer:
    """Compute risk-adjusted performance and attribution statistics."""

    def __init__(self, periods_per_year: int = 252) -> None:
        self.periods_per_year = periods_per_year

    def calculate_sharpe_ratio(
        self,
        returns: pd.Series,
        risk_free_rate: float = 0.0,
    ) -> float:
        excess = returns.mean() * self.periods_per_year - risk_free_rate
        vol = returns.std(ddof=0) * np.sqrt(self.periods_per_year)
        return float(excess / vol) if vol > 0 else np.nan

    def calculate_sortino_ratio(
        self,
        returns: pd.Series,
        mar: float = 0.0,
    ) -> float:
        downside = returns[returns < mar]
        downside_vol = downside.std(ddof=0) * np.sqrt(self.periods_per_year)
        mean_excess = (returns.mean() - mar) * self.periods_per_year
        return float(mean_excess / downside_vol) if downside_vol > 0 else np.nan

    def calculate_calmar_ratio(
        self,
        returns: pd.Series,
        max_drawdown: float,
    ) -> float:
        annual_return = (1 + returns.mean()) ** self.periods_per_year - 1
        denominator = abs(max_drawdown) if max_drawdown != 0 else np.nan
        return float(annual_return / denominator) if denominator else np.nan

    def sector_attribution(
        self,
        portfolio_returns: pd.DataFrame,
        sector_returns: Mapping[str, pd.Series],
    ) -> pd.DataFrame:
        contributions: dict[str, float] = {}
        total_return = portfolio_returns.sum().sum()
        for sector, series in sector_returns.items():
            aligned = portfolio_returns.reindex(series.index, method="ffill")
            contribution = float((aligned.sum(axis=1) * series).sum())
            contributions[sector] = contribution
        df = pd.DataFrame.from_dict(contributions, orient="index", columns=["contribution"])
        df["weight"] = df["contribution"] / total_return if total_return != 0 else np.nan
        return df

    def quantum_vs_classical_comparison(
        self,
        quantum_results: pd.Series,
        classical_results: pd.Series,
        benchmark: Optional[pd.Series] = None,
    ) -> ComparisonResult:
        aligned = pd.concat(
            [
                quantum_results.rename("quantum"),
                classical_results.rename("classical"),
            ],
            axis=1,
        ).dropna()
        if aligned.empty:
            raise ValueError("No overlapping data between quantum and classical results")

        diff = aligned["quantum"] - aligned["classical"]
        information_ratio = diff.mean() * self.periods_per_year / (
            diff.std(ddof=0) * np.sqrt(self.periods_per_year)
        ) if diff.std(ddof=0) > 0 else np.nan

        if benchmark is not None:
            matched = pd.concat([aligned, benchmark.rename("benchmark")], axis=1).dropna()
            X = matched[["benchmark"]]
            X = np.column_stack([np.ones(len(X)), X.values.ravel()])
            y = matched["quantum"].values
            beta = float(np.linalg.lstsq(X, y, rcond=None)[0][1])
            alpha = float(np.linalg.lstsq(X, y, rcond=None)[0][0] * self.periods_per_year)
        else:
            alpha = float(diff.mean() * self.periods_per_year)
            beta = np.nan

        cumulative_diff = (1 + diff).cumprod() - 1

        return ComparisonResult(
            alpha=alpha,
            beta=beta,
            information_ratio=float(information_ratio),
            cumulative_difference=cumulative_diff,
        )


__all__ = ["PerformanceAnalyzer", "ComparisonResult"]

