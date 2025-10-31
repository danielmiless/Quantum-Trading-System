"""Advanced risk analytics for quantum-enhanced portfolios."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import NormalDist
from typing import Iterable, Mapping, Optional, Sequence

import numpy as np
import pandas as pd


@dataclass(slots=True)
class StressScenario:
    """Container for stress testing scenarios."""

    name: str
    shocks: Mapping[str, float]
    multiplier: float = 1.0


class RiskAnalyzer:
    """Compute multi-model risk measures and stress scenarios."""

    def __init__(self, confidence: float = 0.95, periods_per_year: int = 252) -> None:
        self.confidence = confidence
        self.periods_per_year = periods_per_year

    # ------------------------------------------------------------------
    # Value at Risk calculations
    # ------------------------------------------------------------------
    def value_at_risk_historical(
        self,
        returns: Sequence[float] | pd.Series,
        confidence: float | None = None,
    ) -> float:
        series = pd.Series(returns).dropna()
        if series.empty:
            raise ValueError("Returns series cannot be empty")
        alpha = 1 - (confidence or self.confidence)
        var = -float(series.quantile(alpha))
        return max(var, 0.0)

    def value_at_risk_parametric(
        self,
        returns: Sequence[float] | pd.Series,
        confidence: float | None = None,
    ) -> float:
        series = pd.Series(returns).dropna()
        if series.empty:
            raise ValueError("Returns series cannot be empty")
        mu = series.mean()
        sigma = series.std(ddof=0)
        if sigma == 0:
            return max(-mu, 0.0)
        dist = NormalDist(mu, sigma)
        var_level = 1 - (confidence or self.confidence)
        var = -float(dist.inv_cdf(var_level))
        return max(var, 0.0)

    def value_at_risk_monte_carlo(
        self,
        returns: Sequence[float] | pd.Series,
        simulations: int = 10_000,
        confidence: float | None = None,
    ) -> float:
        series = pd.Series(returns).dropna()
        if series.empty:
            raise ValueError("Returns series cannot be empty")
        mean = series.mean()
        sigma = series.std(ddof=0)
        if sigma == 0:
            return max(-mean, 0.0)
        dist = NormalDist(mean, sigma)
        simulated = dist.samples(simulations)
        var_level = 1 - (confidence or self.confidence)
        var = -np.quantile(simulated, var_level)
        return max(float(var), 0.0)

    # ------------------------------------------------------------------
    # Expected shortfall and drawdown analytics
    # ------------------------------------------------------------------
    def expected_shortfall(
        self,
        returns: Sequence[float] | pd.Series,
        confidence: float | None = None,
    ) -> float:
        series = pd.Series(returns).dropna()
        alpha = 1 - (confidence or self.confidence)
        threshold = series.quantile(alpha)
        tail_losses = series[series <= threshold]
        if tail_losses.empty:
            return 0.0
        return -float(tail_losses.mean())

    def maximum_drawdown(self, returns: Sequence[float] | pd.Series) -> tuple[float, int]:
        series = pd.Series(returns).dropna()
        if series.empty:
            return 0.0, 0
        cumulative = (1 + series).cumprod()
        running_max = cumulative.cummax()
        drawdown = cumulative / running_max - 1
        max_dd = float(drawdown.min())
        end_idx = drawdown.idxmin()
        pre = cumulative.loc[:end_idx]
        start_candidates = pre[pre == running_max.loc[end_idx]].index
        start_idx = start_candidates[-1] if len(start_candidates) else end_idx
        post = cumulative.loc[end_idx:]
        recovered = post[post >= running_max.loc[end_idx]]
        recovery_idx = recovered.index.min() if not recovered.empty else end_idx
        recovery_days = (
            int((recovery_idx - start_idx).days)
            if isinstance(recovery_idx, pd.Timestamp) and isinstance(start_idx, pd.Timestamp)
            else 0
        )
        return max_dd, recovery_days

    def rolling_risk_metrics(
        self,
        returns: pd.Series,
        window: int = 63,
        benchmark: Optional[pd.Series] = None,
    ) -> pd.DataFrame:
        if returns.empty:
            raise ValueError("Returns series cannot be empty")
        data = pd.DataFrame({"returns": returns})
        rolling_vol = data["returns"].rolling(window).std(ddof=0) * np.sqrt(self.periods_per_year)
        downside = data["returns"].clip(upper=0)
        rolling_downside = downside.rolling(window).std(ddof=0) * np.sqrt(self.periods_per_year)
        metrics = pd.DataFrame(
            {
                "rolling_vol": rolling_vol,
                "rolling_downside_vol": rolling_downside,
            }
        )
        if benchmark is not None:
            aligned = pd.concat([returns, benchmark.rename("benchmark")], axis=1).dropna()
            if not aligned.empty:
                cov = aligned["returns"].rolling(window).cov(aligned["benchmark"])
                bench_var = aligned["benchmark"].rolling(window).var(ddof=0)
                beta = cov / bench_var.replace(0, np.nan)
                metrics.loc[beta.index, "rolling_beta"] = beta
        return metrics

    def regime_analysis(self, returns: pd.Series, window: int = 126) -> pd.Series:
        if returns.empty:
            raise ValueError("Returns series cannot be empty")
        rolling_mean = returns.rolling(window).mean()
        rolling_vol = returns.rolling(window).std()
        z_score = (rolling_mean - rolling_mean.mean()) / rolling_vol.replace(0, np.nan)
        regimes = pd.cut(
            z_score,
            bins=[-np.inf, -1.0, 0.0, 1.0, np.inf],
            labels=["Stress", "Bear", "Neutral", "Bull"],
        )
        return regimes.astype(str)

    # ------------------------------------------------------------------
    # Stress testing
    # ------------------------------------------------------------------
    def stress_test(
        self,
        portfolio_weights: Mapping[str, float],
        scenarios: Iterable[StressScenario],
    ) -> pd.DataFrame:
        weights = pd.Series(portfolio_weights, dtype=float)
        weights = weights / weights.sum()
        records: list[dict[str, float]] = []
        for scenario in scenarios:
            shocks = pd.Series(scenario.shocks, dtype=float)
            shocks = shocks.reindex(weights.index).fillna(0.0)
            impact = float((weights * shocks).sum() * scenario.multiplier)
            records.append({"scenario": scenario.name, "expected_loss": impact})
        return pd.DataFrame(records)


__all__ = ["RiskAnalyzer", "StressScenario"]

