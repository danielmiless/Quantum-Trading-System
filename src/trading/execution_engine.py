"""Smart order execution strategies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np
from loguru import logger


@dataclass(slots=True)
class Order:
    symbol: str
    qty: float
    side: str
    order_type: str = "market"


class ExecutionEngine:
    """Create execution strategies such as TWAP and order splitting."""

    def __init__(self, twap_slices: int = 5, min_order_size: float = 1.0) -> None:
        self.twap_slices = twap_slices
        self.min_order_size = min_order_size
        self.slippage_records: list[float] = []

    def construct_orders(self, plan) -> List[Order]:
        orders: List[Order] = []
        remaining_cash = plan.cash_available
        for symbol, target_weight in plan.target_weights.items():
            price = plan.latest_prices.get(symbol)
            if not price or price <= 0:
                logger.warning("Skipping {} due to invalid price", symbol)
                continue
            target_value = plan.portfolio_value * target_weight
            current_value = plan.current_values.get(symbol, 0.0)
            value_diff = target_value - current_value
            if abs(value_diff) < 1e-2:
                continue
            qty_diff = value_diff / price
            side = "buy" if qty_diff > 0 else "sell"
            qty = abs(qty_diff)
            if side == "buy":
                if (qty * price) > remaining_cash:
                    qty = max((remaining_cash / price), 0.0)
                remaining_cash = max(remaining_cash - qty * price, 0.0)
            if qty <= 0:
                continue
            orders.extend(self._split_order(symbol, qty, side))
        logger.debug("Constructed {} orders", len(orders))
        return orders

    def _split_order(self, symbol: str, qty: float, side: str) -> List[Order]:
        if qty <= self.min_order_size:
            return [Order(symbol, qty, side)]
        slice_qty = qty / self.twap_slices
        return [Order(symbol, slice_qty, side) for _ in range(self.twap_slices)]

    def record_slippage(self, expected_price: float, filled_price: float) -> None:
        slippage = filled_price - expected_price
        self.slippage_records.append(slippage)
        logger.debug("Recorded slippage {}", slippage)

    def slippage_summary(self) -> Dict[str, float]:
        if not self.slippage_records:
            return {"mean_slippage": 0.0, "max_slippage": 0.0}
        records = np.array(self.slippage_records, dtype=float)
        return {
            "mean_slippage": float(records.mean()),
            "max_slippage": float(records.max()),
        }


__all__ = ["ExecutionEngine", "Order"]

