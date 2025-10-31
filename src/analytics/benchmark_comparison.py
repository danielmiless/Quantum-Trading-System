"""Benchmark comparison utilities."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping, Optional

import numpy as np
import pandas as pd


DataProvider = Callable[[str, pd.Timestamp, pd.Timestamp], pd.Series]


@dataclass(slots=True)
class BenchmarkResult:
    """Summary of benchmark comparison statistics."""

    tracking_error: float
    information_ratio: float
    active_share: float
    t_statistic: float
    p_value: float
    style_drift: Optional[float]


class BenchmarkComparator:
    """Compare quantum portfolio outcomes against traditional benchmarks."""

    def __init__(
        self,
        data_provider: Optional[DataProvider] = None,
        periods_per_year: int = 252,
    ) -> None:
        self.data_provider = data_provider
        self.periods_per_year = periods_per_year

    def load_benchmark_data(
        self,
        symbol: str,
        start: str | pd.Timestamp,
        end: str | pd.Timestamp,
    ) -> pd.Series:
        if self.data_provider is None:
            raise ValueError("No data provider available for benchmark loading")
        series = self.data_provider(symbol, pd.to_datetime(start), pd.to_datetime(end))
        if not isinstance(series, pd.Series):
            raise TypeError("Benchmark data provider must return a pandas Series")
        return series.sort_index()

    def statistical_significance(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> tuple[float, float]:
        diff = (portfolio_returns - benchmark_returns).dropna()
        if diff.empty:
            return np.nan, np.nan
        mean_diff = diff.mean()
        std_diff = diff.std(ddof=1)
        n = len(diff)
        if std_diff == 0 or n <= 1:
            return np.nan, np.nan
        t_stat = mean_diff / (std_diff / np.sqrt(n))
        # Two-tailed p-value using Normal approximation
        p_value = 2 * (1 - 0.5 * (1 + np.math.erf(abs(t_stat) / np.sqrt(2))))
        return float(t_stat), float(p_value)

    def tracking_error_and_information_ratio(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
    ) -> tuple[float, float]:
        diff = (portfolio_returns - benchmark_returns).dropna()
        if diff.empty:
            return np.nan, np.nan
        tracking_error = diff.std(ddof=0) * np.sqrt(self.periods_per_year)
        information_ratio = (
            diff.mean() * self.periods_per_year / tracking_error
            if tracking_error > 0
            else np.nan
        )
        return float(tracking_error), float(information_ratio)

    def active_share(
        self,
        portfolio_weights: Mapping[str, float],
        benchmark_weights: Mapping[str, float],
    ) -> float:
        assets = sorted(set(portfolio_weights) | set(benchmark_weights))
        port = np.array([portfolio_weights.get(asset, 0.0) for asset in assets])
        bench = np.array([benchmark_weights.get(asset, 0.0) for asset in assets])
        port = port / port.sum() if port.sum() else port
        bench = bench / bench.sum() if bench.sum() else bench
        return float(0.5 * np.abs(port - bench).sum())

    def style_drift(
        self,
        style_exposures: Mapping[str, float],
        benchmark_style: Mapping[str, float],
    ) -> float:
        exposures = pd.Series(style_exposures)
        benchmark = pd.Series(benchmark_style)
        aligned = exposures.reindex(sorted(set(exposures.index) | set(benchmark.index)), fill_value=0.0)
        benchmark = benchmark.reindex(aligned.index, fill_value=0.0)
        return float(np.abs(aligned - benchmark).sum())

    def compare(
        self,
        portfolio_returns: pd.Series,
        benchmark_returns: pd.Series,
        portfolio_weights: Mapping[str, float],
        benchmark_weights: Mapping[str, float],
        *,
        style_exposures: Optional[Mapping[str, float]] = None,
        benchmark_style: Optional[Mapping[str, float]] = None,
    ) -> BenchmarkResult:
        tracking_error, information_ratio = self.tracking_error_and_information_ratio(
            portfolio_returns, benchmark_returns
        )
        t_stat, p_value = self.statistical_significance(portfolio_returns, benchmark_returns)
        active = self.active_share(portfolio_weights, benchmark_weights)
        style_value = None
        if style_exposures and benchmark_style:
            style_value = self.style_drift(style_exposures, benchmark_style)
        return BenchmarkResult(
            tracking_error=tracking_error,
            information_ratio=information_ratio,
            active_share=active,
            t_statistic=t_stat,
            p_value=p_value,
            style_drift=style_value,
        )


__all__ = ["BenchmarkComparator", "BenchmarkResult"]

