"""Trading system tests with mocked Alpaca interaction."""

from __future__ import annotations

from datetime import datetime, time
from typing import Dict, List

import numpy as np
import pandas as pd
import pytest

from notifications import NotificationManager
from trading.alpaca_client import Position
from trading.execution_engine import ExecutionEngine
from trading.performance_tracker import PerformanceTracker
from trading.portfolio_manager import LivePortfolioManager
from trading.risk_monitor import RiskLimits, RiskMonitor
from trading.scheduler import Schedule, TradingScheduler


class DummyAlpacaClient:
    def __init__(self) -> None:
        self.orders: List[Dict[str, str]] = []

    def place_order(self, symbol: str, qty: float, side: str, order_type: str = "market") -> Dict[str, str]:
        order = {
            "id": f"{symbol}-{len(self.orders)}",
            "symbol": symbol,
            "qty": qty,
            "filled_avg_price": 100.0,
            "status": "filled",
            "side": side,
        }
        self.orders.append(order)
        return order


def test_execution_engine_order_split() -> None:
    engine = ExecutionEngine(twap_slices=3, min_order_size=10)
    plan = type(
        "Plan",
        (),
        {
            "target_weights": {"AAPL": 0.5},
            "current_values": {"AAPL": 0.0},
            "current_quantities": {"AAPL": 0.0},
            "latest_prices": {"AAPL": 50.0},
            "portfolio_value": 1000.0,
            "cash_available": 1000.0,
        },
    )()
    orders = engine.construct_orders(plan)
    assert len(orders) == 3
    assert sum(order.qty for order in orders) == pytest.approx(10.0)


def test_risk_monitor_triggers_notifications() -> None:
    notified = []
    manager = NotificationManager()
    manager.register_channel("test", lambda level, message: notified.append((level, message)))
    monitor = RiskMonitor(
        limits=RiskLimits(max_var=0.01, max_drawdown=-0.05, max_position_concentration=0.4),
        notifier=manager.notify,
    )
    returns = np.random.default_rng(42).normal(0.0, 0.05, 100)
    positions = {"AAPL": 0.5, "MSFT": 0.6}
    monitor.evaluate_portfolio(returns, positions)
    assert notified


def test_live_portfolio_manager_rebalance(monkeypatch) -> None:
    client = DummyAlpacaClient()
    engine = ExecutionEngine(twap_slices=2, min_order_size=0.1)
    tracker = PerformanceTracker()
    manager = LivePortfolioManager(
        trading_client=client,
        execution_engine=engine,
        performance_tracker=tracker,
        max_position_pct=0.6,
        min_cash_buffer=0.05,
    )

    account_info = {"cash": "50000", "portfolio_value": "100000"}
    positions = [Position(symbol="AAPL", qty=100, avg_entry_price=150, current_price=155, unrealized_pl=500)]
    plan = manager.generate_rebalance_plan(
        optimization_output={"AAPL": 0.4, "MSFT": 0.6},
        account_info=account_info,
        positions=positions,
        market_prices={"MSFT": 250.0},
    )
    manager.execute_rebalance(plan)
    assert client.orders
    tracker.update_equity(100000)
    tracker.update_equity(100500)
    performance = tracker.current_performance()
    assert performance["pnl"] == 500


def test_trading_scheduler_runs_jobs(monkeypatch) -> None:
    scheduler = TradingScheduler()
    executed = []

    def job():
        executed.append(True)

    scheduler.add_job(Schedule(name="rebalance", callback=job, time_of_day=time(14, 30)))

    class DummyCalendar:
        def schedule(self, start_date, end_date):
            return pd.DataFrame(
                {
                    "market_open": [pd.Timestamp(datetime(2024, 1, 2, 9, 30))],
                    "market_close": [pd.Timestamp(datetime(2024, 1, 2, 16, 0))],
                }
            )

    monkeypatch.setattr(scheduler, "calendar", DummyCalendar())
    scheduler.run_pending(datetime(2024, 1, 2, 14, 30))
    assert executed

