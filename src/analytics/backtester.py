"""Backtesting utilities for the Quantum Portfolio Optimizer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Mapping, Optional

import numpy as np
import pandas as pd


FREQ_MAP = {
    "daily": "D",
    "weekly": "W-FRI",
    "monthly": "M",
}


@dataclass(slots=True)
class BacktestResult:
    """Container for backtest outcomes."""

    returns: pd.DataFrame
    trades: pd.DataFrame
    metrics: dict[str, float]


class BacktestEngine:
    """Run portfolio backtests with realistic frictions and market impact."""

    def __init__(
        self,
        price_data: Optional[pd.DataFrame] = None,
        benchmark_returns: Optional[pd.Series] = None,
        *,
        transaction_cost: float = 0.0005,
        slippage: float = 0.0002,
        market_impact: float = 0.0001,
        risk_free_rate: float = 0.01,
    ) -> None:
        self.price_data = price_data
        self.benchmark_returns = benchmark_returns
        self.transaction_cost = transaction_cost
        self.slippage = slippage
        self.market_impact = market_impact
        self.risk_free_rate = risk_free_rate

    def run_backtest(
        self,
        portfolio: Mapping[str, object],
        start_date: str | pd.Timestamp,
        end_date: str | pd.Timestamp,
        rebalance_freq: str = "monthly",
    ) -> BacktestResult:
        """Execute a backtest over the requested period.

        Parameters
        ----------
        portfolio:
            Mapping containing ``weights`` (symbol -> target weight) and optionally
            ``prices`` (DataFrame of asset prices). If ``prices`` is omitted, the
            engine-level price data is used.
        start_date, end_date:
            Inclusive date range for the analysis.
        rebalance_freq:
            One of ``"daily"``, ``"weekly"``, or ``"monthly"``.
        """

        prices = self._resolve_price_data(portfolio)
        prices = prices.loc[pd.to_datetime(start_date) : pd.to_datetime(end_date)]
        if prices.empty:
            raise ValueError("No price data available for requested period")

        returns = prices.pct_change().fillna(0.0)
        benchmark_ret = self._slice_benchmark(returns.index)

        target_weights = self._normalize_weights(portfolio.get("weights", {}), returns.columns)
        if (target_weights <= 0).all():
            raise ValueError("Portfolio weights must contain at least one positive entry")

        rebalance_dates = self._rebalance_schedule(returns.index, rebalance_freq)
        positions = pd.Series(np.zeros(len(returns.columns)), index=returns.columns, dtype=float)

        portfolio_rets: list[float] = []
        bench_series: list[float] = []
        trades: list[dict[str, float]] = []

        for idx, (date, row) in enumerate(returns.iterrows()):
            trade_cost = 0.0
            if idx == 0 or date in rebalance_dates:
                trade = target_weights - positions
                turnover = float(trade.abs().sum())
                trade_cost = turnover * (self.transaction_cost + self.slippage + self.market_impact)
                positions = target_weights.copy()
                trades.append({"date": date, "turnover": turnover})
            else:
                trades.append({"date": date, "turnover": 0.0})

            daily_return = float(np.dot(positions.values, row.values)) - trade_cost
            portfolio_rets.append(daily_return)

            if benchmark_ret is not None:
                bench_value = float(benchmark_ret.get(date, np.nan))
            else:
                bench_value = np.nan
            bench_series.append(bench_value)

            # Allow portfolio weights to drift with market moves for next iteration.
            positions = positions * (1.0 + row)
            if positions.sum() != 0:
                positions = positions / positions.sum()

        result_df = pd.DataFrame(
            {
                "portfolio": portfolio_rets,
                "benchmark": bench_series,
            },
            index=returns.index,
        )
        trades_df = pd.DataFrame(trades).set_index("date")

        metrics = self.calculate_performance_metrics(
            result_df["portfolio"],
            result_df["benchmark"],
        )

        return BacktestResult(result_df, trades_df, metrics)

    def calculate_performance_metrics(
        self,
        returns: pd.Series,
        benchmark_returns: Optional[pd.Series],
    ) -> dict[str, float]:
        """Compute standard performance metrics for the portfolio."""

        returns = returns.dropna()
        periods_per_year = 252
        mean_return = returns.mean()
        annualized_return = (1 + mean_return) ** periods_per_year - 1
        annualized_vol = returns.std(ddof=0) * np.sqrt(periods_per_year)
        sharpe = (
            (annualized_return - self.risk_free_rate)
            / annualized_vol
            if annualized_vol > 0
            else np.nan
        )

        downside = returns[returns < 0]
        downside_vol = downside.std(ddof=0) * np.sqrt(periods_per_year)
        sortino = (
            (annualized_return - self.risk_free_rate) / downside_vol
            if downside_vol > 0
            else np.nan
        )

        cumulative = (1 + returns).cumprod()
        running_max = cumulative.cummax()
        drawdown = cumulative / running_max - 1
        max_drawdown = float(drawdown.min())

        metrics = {
            "annualized_return": float(annualized_return),
            "annualized_volatility": float(annualized_vol),
            "sharpe_ratio": float(sharpe),
            "sortino_ratio": float(sortino),
            "max_drawdown": max_drawdown,
        }

        if benchmark_returns is not None and not benchmark_returns.dropna().empty:
            aligned = pd.concat(
                [returns, benchmark_returns.rename("benchmark")], axis=1
            ).dropna()
            if not aligned.empty:
                active = aligned.iloc[:, 0] - aligned.iloc[:, 1]
                tracking_error = active.std(ddof=0) * np.sqrt(periods_per_year)
                information_ratio = (
                    active.mean() * periods_per_year / tracking_error
                    if tracking_error > 0
                    else np.nan
                )
                metrics.update(
                    {
                        "tracking_error": float(tracking_error),
                        "information_ratio": float(information_ratio),
                    }
                )

        return metrics

    def generate_trade_signals(
        self,
        optimization_results: Mapping[str, Mapping[str, float]],
    ) -> pd.DataFrame:
        """Create trade instructions from optimization output."""

        current = pd.Series(optimization_results.get("current_weights", {}), dtype=float)
        target = pd.Series(optimization_results.get("target_weights", {}), dtype=float)
        index = sorted(set(current.index) | set(target.index))
        current = current.reindex(index, fill_value=0.0)
        target = target.reindex(index, fill_value=0.0)

        delta = target - current
        signal = np.where(delta > 0, "BUY", np.where(delta < 0, "SELL", "HOLD"))

        return pd.DataFrame(
            {
                "current_weight": current,
                "target_weight": target,
                "change": delta,
                "signal": signal,
            }
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _resolve_price_data(self, portfolio: Mapping[str, object]) -> pd.DataFrame:
        prices = portfolio.get("prices") if isinstance(portfolio, Mapping) else None
        if prices is None:
            if self.price_data is None:
                raise ValueError("Price data must be provided at initialization or per call")
            prices = self.price_data
        if not isinstance(prices, pd.DataFrame):
            raise TypeError("Price data must be a pandas DataFrame")
        if prices.isna().all().all():
            raise ValueError("Price data contains only NaN values")
        return prices.sort_index()

    def _slice_benchmark(self, index: pd.Index) -> Optional[pd.Series]:
        if self.benchmark_returns is None:
            return None
        return self.benchmark_returns.reindex(index).fillna(method="ffill")

    def _normalize_weights(
        self,
        weights: Mapping[str, float] | Iterable[tuple[str, float]],
        assets: Iterable[str],
    ) -> pd.Series:
        if isinstance(weights, Mapping):
            series = pd.Series(weights, dtype=float)
        else:
            series = pd.Series(dict(weights), dtype=float)
        series = series.reindex(list(assets), fill_value=0.0)
        total = series.sum()
        if total <= 0:
            return series
        return series / total

    def _rebalance_schedule(self, index: pd.Index, freq: str) -> pd.Index:
        freq_key = freq.lower()
        if freq_key not in FREQ_MAP:
            raise ValueError(f"Unsupported rebalance frequency: {freq}")
        sampled = index.to_series().resample(FREQ_MAP[freq_key]).first().dropna()
        return sampled.index


__all__ = ["BacktestEngine", "BacktestResult"]

