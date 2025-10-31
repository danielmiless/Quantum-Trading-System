"""Real-time performance tracking utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Mapping

import numpy as np
import pandas as pd
from loguru import logger


@dataclass(slots=True)
class OrderRecord:
    order_id: str
    symbol: str
    qty: float
    filled_price: float
    status: str


class PerformanceTracker:
    """Track live P&L and compute rolling performance metrics."""

    def __init__(self, periods_per_year: int = 252) -> None:
        self.orders: List[OrderRecord] = []
        self.equity_curve: List[float] = []
        self.periods_per_year = periods_per_year

    def record_order(self, order_response: Mapping[str, str]) -> None:
        try:
            record = OrderRecord(
                order_id=str(order_response.get("id")),
                symbol=str(order_response.get("symbol")),
                qty=float(order_response.get("qty", 0.0)),
                filled_price=float(order_response.get("filled_avg_price", 0.0)),
                status=str(order_response.get("status", "")),
            )
            self.orders.append(record)
            logger.debug("Recorded order {}", record)
        except (TypeError, ValueError) as exc:
            logger.error("Failed to record order: {}", exc)

    def update_equity(self, equity_value: float) -> None:
        self.equity_curve.append(equity_value)
        logger.debug("Equity updated: {}", equity_value)

    def current_performance(self) -> Dict[str, float]:
        if len(self.equity_curve) < 2:
            return {"pnl": 0.0, "sharpe": np.nan, "sortino": np.nan}
        returns = pd.Series(self.equity_curve).pct_change().dropna()
        pnl = self.equity_curve[-1] - self.equity_curve[0]
        sharpe = self._sharpe_ratio(returns)
        sortino = self._sortino_ratio(returns)
        return {"pnl": pnl, "sharpe": sharpe, "sortino": sortino}

    def _sharpe_ratio(self, returns: pd.Series) -> float:
        mean_return = returns.mean() * self.periods_per_year
        vol = returns.std(ddof=0) * np.sqrt(self.periods_per_year)
        return float(mean_return / vol) if vol > 0 else np.nan

    def _sortino_ratio(self, returns: pd.Series) -> float:
        downside = returns[returns < 0]
        downside_vol = downside.std(ddof=0) * np.sqrt(self.periods_per_year)
        mean_return = returns.mean() * self.periods_per_year
        return float(mean_return / downside_vol) if downside_vol > 0 else np.nan


__all__ = ["PerformanceTracker", "OrderRecord"]

