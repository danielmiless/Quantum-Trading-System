"""Live portfolio management leveraging the quantum optimizer."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Mapping, Optional, Sequence

import numpy as np
from loguru import logger

from analytics.risk_analytics import RiskAnalyzer
from trading.alpaca_client import AlpacaClient, Position
from trading.execution_engine import ExecutionEngine
from trading.performance_tracker import PerformanceTracker


@dataclass(slots=True)
class RebalancePlan:
    target_weights: Dict[str, float]
    current_quantities: Dict[str, float]
    current_values: Dict[str, float]
    latest_prices: Dict[str, float]
    portfolio_value: float
    cash_available: float


class LivePortfolioManager:
    """Coordinate live portfolio actions based on quantum optimization outputs."""

    def __init__(
        self,
        trading_client: AlpacaClient,
        execution_engine: ExecutionEngine,
        performance_tracker: PerformanceTracker,
        risk_analyzer: Optional[RiskAnalyzer] = None,
        max_position_pct: float = 0.1,
        min_cash_buffer: float = 0.05,
    ) -> None:
        self.client = trading_client
        self.execution = execution_engine
        self.tracker = performance_tracker
        self.risk = risk_analyzer or RiskAnalyzer()
        self.max_position_pct = max_position_pct
        self.min_cash_buffer = min_cash_buffer

    def generate_rebalance_plan(
        self,
        optimization_output: Mapping[str, float],
        account_info: Mapping[str, str],
        positions: Sequence[Position],
        market_prices: Optional[Mapping[str, float]] = None,
    ) -> RebalancePlan:
        portfolio_value = float(account_info.get("portfolio_value", 0.0))
        cash = float(account_info.get("cash", 0.0))
        buffer = portfolio_value * self.min_cash_buffer
        cash_available = max(cash - buffer, 0.0)

        target_weights = self._enforce_position_limits(optimization_output)

        current_quantities: Dict[str, float] = {}
        current_values: Dict[str, float] = {}
        latest_prices: Dict[str, float] = {}

        for position in positions:
            current_quantities[position.symbol] = position.qty
            latest_prices[position.symbol] = position.current_price
            current_values[position.symbol] = position.qty * position.current_price

        for symbol in target_weights:
            if symbol not in latest_prices:
                if market_prices and symbol in market_prices:
                    latest_prices[symbol] = float(market_prices[symbol])
                else:
                    raise ValueError(f"Missing market price for {symbol}")
            current_quantities.setdefault(symbol, 0.0)
            current_values.setdefault(symbol, current_quantities[symbol] * latest_prices[symbol])

        return RebalancePlan(
            target_weights=target_weights,
            current_quantities=current_quantities,
            current_values=current_values,
            latest_prices=latest_prices,
            portfolio_value=portfolio_value,
            cash_available=cash_available,
        )

    def execute_rebalance(self, plan: RebalancePlan) -> None:
        orders = self.execution.construct_orders(plan)
        for order in orders:
            try:
                response = self.client.place_order(
                    symbol=order.symbol,
                    qty=order.qty,
                    side=order.side,
                    order_type=order.order_type,
                )
                logger.info("Executed order: {}", response)
                self.tracker.record_order(response)
            except Exception as exc:  # noqa: BLE001
                logger.error("Order execution failed for {}: {}", order.symbol, exc)

    def _enforce_position_limits(self, weights: Mapping[str, float]) -> Dict[str, float]:
        series = np.array(list(weights.values()), dtype=float)
        symbols = list(weights.keys())
        if series.sum() <= 0:
            raise ValueError("Optimization returned non-positive weight sum")
        normalized = series / series.sum()
        capped = np.minimum(normalized, self.max_position_pct)
        total = capped.sum()
        if total <= 0:
            capped = normalized
            total = capped.sum()
        capped /= total
        return dict(zip(symbols, capped))


__all__ = ["LivePortfolioManager", "RebalancePlan"]

