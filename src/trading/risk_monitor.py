"""Real-time risk monitoring for live trading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Mapping

import numpy as np
from loguru import logger

from analytics.risk_analytics import RiskAnalyzer


AlertCallback = Callable[[str, str], None]


@dataclass(slots=True)
class RiskLimits:
    max_var: float
    max_drawdown: float
    max_position_concentration: float


class RiskMonitor:
    """Monitor risk metrics and trigger alerts."""

    def __init__(
        self,
        limits: RiskLimits,
        notifier: AlertCallback,
        risk_analyzer: RiskAnalyzer | None = None,
    ) -> None:
        self.limits = limits
        self.notify = notifier
        self.analyzer = risk_analyzer or RiskAnalyzer()

    def evaluate_portfolio(
        self,
        portfolio_returns: np.ndarray,
        positions: Mapping[str, float],
    ) -> None:
        var = self.analyzer.value_at_risk_parametric(portfolio_returns)
        if var > self.limits.max_var:
            msg = f"VaR limit breached: {var:.4f} > {self.limits.max_var:.4f}"
            logger.warning(msg)
            self.notify("risk", msg)

        drawdown, _ = self.analyzer.maximum_drawdown(portfolio_returns)
        if abs(drawdown) > abs(self.limits.max_drawdown):
            msg = f"Drawdown limit breached: {drawdown:.4f}"
            logger.warning(msg)
            self.notify("risk", msg)

        concentration = max(abs(value) for value in positions.values())
        if concentration > self.limits.max_position_concentration:
            msg = f"Position concentration exceeded: {concentration:.4f}"
            logger.warning(msg)
            self.notify("risk", msg)


__all__ = ["RiskMonitor", "RiskLimits"]

