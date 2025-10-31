"""Controller for Alpaca paper-trading integration."""

from __future__ import annotations

import os
from datetime import datetime
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from loguru import logger
from PySide6.QtCore import QObject, Signal

from trading.alpaca_client import AlpacaClient, Position
from trading.performance_tracker import PerformanceTracker
from trading.execution_engine import ExecutionEngine, Order
from trading.portfolio_manager import LivePortfolioManager, RebalancePlan
from ..utils.signal_manager import SignalManager

try:  # Optional dependency for price retrieval on new symbols
    import yfinance as yf
except ImportError:  # pragma: no cover - optional path
    yf = None


class TradingController(QObject):
    """Coordinate trading widget interactions with Alpaca APIs."""

    connection_changed = Signal(bool, str)
    account_updated = Signal(dict)
    performance_updated = Signal(dict)
    positions_updated = Signal(list)
    orders_updated = Signal(list)
    status_message = Signal(str, str)  # level, message
    target_updated = Signal(list)  # list of symbols represented in target

    def __init__(
        self,
        *,
        client: AlpacaClient | None = None,
        performance_tracker: PerformanceTracker | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._client = client or AlpacaClient()
        self._performance = performance_tracker or PerformanceTracker()
        self._connected = False
        self._execution = ExecutionEngine()
        self._manager = LivePortfolioManager(
            trading_client=self._client,
            execution_engine=self._execution,
            performance_tracker=self._performance,
        )
        self._signal_manager = SignalManager.instance()
        self._signal_manager.portfolio_updated.connect(self._handle_portfolio_update)
        self._signal_manager.quantum_job_completed.connect(self._handle_quantum_result)
        self._latest_symbols: list[str] = []
        self._latest_target_weights: Dict[str, float] = {}
        self._last_plan: Optional[RebalancePlan] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def has_credentials(self) -> bool:
        """Return True if Alpaca credentials are present in the environment."""

        return bool(os.getenv("APCA_API_KEY_ID") and os.getenv("APCA_API_SECRET_KEY"))

    def connect_to_alpaca(self, checked: bool | None = False) -> None:  # noqa: ARG002 - Qt passes state
        """Authenticate the Alpaca client using environment variables."""

        del checked  # Not used, but required for signal compatibility

        api_key = os.getenv("APCA_API_KEY_ID")
        secret_key = os.getenv("APCA_API_SECRET_KEY")
        base_url = os.getenv("APCA_API_BASE_URL", "https://paper-api.alpaca.markets")

        if not api_key or not secret_key:
            message = "Missing APCA_API_KEY_ID or APCA_API_SECRET_KEY in environment"
            logger.warning(message)
            self.connection_changed.emit(False, message)
            return

        try:
            paper = "paper" in base_url
            self._client.authenticate(api_key, secret_key, paper=paper, base_url=str(base_url))
            self._connected = True
            env_name = "paper" if paper else "live"
            self.connection_changed.emit(True, f"Connected to Alpaca ({env_name})")
            self.refresh_data()
        except Exception as exc:  # noqa: BLE001 - surface runtime error
            self._connected = False
            logger.exception("Failed to connect to Alpaca: {}", exc)
            self.connection_changed.emit(False, str(exc))

    def refresh_data(self, checked: bool | None = False) -> None:  # noqa: ARG002 - Qt passes state
        """Pull latest account, position, and performance data."""

        del checked

        if not self._connected:
            self.connection_changed.emit(False, "Not connected")
            return

        try:
            account = self._client.get_account_info()
            self.account_updated.emit(dict(account))

            equity = float(account.get("portfolio_value", 0.0))
            if equity:
                self._performance.update_equity(equity)
            performance = self._performance.current_performance()
            self.performance_updated.emit(performance)

            positions = self._client.get_positions()
            self.positions_updated.emit(self._transform_positions(positions))

            self.orders_updated.emit(self._transform_orders())
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.connection_changed.emit(True, f"Last refreshed at {timestamp}")
            self.status_message.emit("info", "Account data refreshed")
        except Exception as exc:  # noqa: BLE001
            logger.exception("Failed to refresh Alpaca data: {}", exc)
            self.connection_changed.emit(False, str(exc))
            self.status_message.emit("error", f"Refresh failed: {exc}")

    def preview_rebalance(self, checked: bool | None = False) -> None:  # noqa: ARG002 - Qt passes state
        """Generate a rebalance plan without placing live orders."""

        del checked

        try:
            plan = self._build_rebalance_plan()
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to build rebalance plan: {}", exc)
            self.status_message.emit("error", str(exc))
            return

        orders = self._execution.construct_orders(plan)
        self._last_plan = plan
        preview_rows = self._orders_to_rows(orders, plan, status_suffix="(preview)")
        self.orders_updated.emit(preview_rows)
        total_notional = sum(
            order.qty * plan.latest_prices.get(order.symbol, 0.0) for order in orders
        )
        self.status_message.emit(
            "info",
            f"Preview ready: {len(orders)} orders totalling ${total_notional:,.2f}",
        )

    def execute_rebalance(self, checked: bool | None = False) -> None:  # noqa: ARG002 - Qt passes state
        """Submit live orders to reach the most recent target weights."""

        del checked

        try:
            plan = self._last_plan or self._build_rebalance_plan()
        except Exception as exc:  # noqa: BLE001
            logger.error("Unable to execute rebalance: {}", exc)
            self.status_message.emit("error", str(exc))
            return

        self._manager.execute_rebalance(plan)
        self._last_plan = None
        self.status_message.emit("success", "Rebalance orders submitted")
        self.refresh_data()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _transform_positions(self, positions: List[Position]) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for position in positions:
            rows.append(
                {
                    "Symbol": position.symbol,
                    "Qty": f"{position.qty:.4f}",
                    "Avg Price": f"{position.avg_entry_price:.2f}",
                    "P&L": f"{position.unrealized_pl:.2f}",
                }
            )
        return rows

    def _transform_orders(self) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for order in self._performance.orders:
            rows.append(
                {
                    "Order ID": order.order_id,
                    "Symbol": order.symbol,
                    "Qty": f"{order.qty:.4f}",
                    "Price": f"{order.filled_price:.2f}",
                    "Status": order.status,
                }
            )
        return rows

    # ------------------------------------------------------------------
    # Target handling
    # ------------------------------------------------------------------
    def _handle_portfolio_update(self, payload: Mapping[str, object]) -> None:
        assets = payload.get("assets")
        if not isinstance(assets, list) or not assets:
            return

        symbols: list[str] = []
        raw_weights: Dict[str, float] = {}
        for entry in assets:
            if not isinstance(entry, Mapping):
                continue
            symbol = str(entry.get("symbol", "")).upper()
            if not symbol:
                continue
            try:
                allocation = float(entry.get("allocation", 0.0)) / 100.0
            except (TypeError, ValueError):
                allocation = 0.0
            symbols.append(symbol)
            raw_weights[symbol] = max(allocation, 0.0)

        normalized = self._normalize_weights(raw_weights)
        if not normalized:
            return

        self._latest_symbols = symbols
        self._latest_target_weights = normalized
        self.target_updated.emit(symbols)
        self.status_message.emit(
            "info", f"Loaded portfolio allocations for {len(symbols)} assets"
        )

    def _handle_quantum_result(self, payload: Mapping[str, object]) -> None:
        weights = payload.get("weights")
        if not isinstance(weights, Sequence):
            return
        if not self._latest_symbols:
            self.status_message.emit(
                "warning",
                "Quantum result received but no portfolio allocation is available to map symbols.",
            )
            return
        if len(weights) != len(self._latest_symbols):
            self.status_message.emit(
                "warning",
                "Quantum result length does not match current portfolio; ignoring.",
            )
            return

        mapping = {
            symbol: max(float(weight), 0.0)
            for symbol, weight in zip(self._latest_symbols, weights)
        }
        normalized = self._normalize_weights(mapping)
        if not normalized:
            self.status_message.emit("warning", "Quantum result produced zero allocation")
            return

        self._latest_target_weights = normalized
        self.target_updated.emit(list(normalized.keys()))
        self.status_message.emit(
            "success", "Applied latest quantum optimization weights to trading target"
        )
        self._last_plan = None

    def _build_rebalance_plan(self) -> RebalancePlan:
        if not self._connected:
            raise RuntimeError("Connect to Alpaca before generating a rebalance plan")
        if not self._latest_target_weights:
            raise RuntimeError("No target allocations available. Update the portfolio or run an optimization.")

        account = self._client.get_account_info()
        positions = self._client.get_positions()
        price_map = self._build_price_map(self._latest_target_weights.keys(), positions)
        plan = self._manager.generate_rebalance_plan(
            optimization_output=self._latest_target_weights,
            account_info=account,
            positions=positions,
            market_prices=price_map,
        )
        return plan

    def _build_price_map(
        self, symbols: Iterable[str], positions: Sequence[Position]
    ) -> Dict[str, float]:
        price_map: Dict[str, float] = {
            pos.symbol: float(pos.current_price)
            for pos in positions
            if pos.current_price and pos.current_price > 0
        }
        missing = [symbol for symbol in symbols if price_map.get(symbol, 0.0) <= 0]
        if missing and yf is not None:
            fetched = self._fetch_prices(missing)
            price_map.update(fetched)
            missing = [symbol for symbol in symbols if price_map.get(symbol, 0.0) <= 0]
        if missing:
            raise ValueError(
                "Missing market prices for: " + ", ".join(sorted(set(missing)))
            )
        return price_map

    def _fetch_prices(self, symbols: Sequence[str]) -> Dict[str, float]:
        if yf is None:  # pragma: no cover - optional dependency handling
            raise RuntimeError(
                "yfinance is required to fetch market prices for new symbols"
            )
        prices: Dict[str, float] = {}
        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                history = ticker.history(period="1d")
                if not history.empty:
                    prices[symbol] = float(history["Close"].iloc[-1])
            except Exception as exc:  # pragma: no cover - API variability
                logger.warning("Failed to fetch price for {}: {}", symbol, exc)
        return prices

    def _normalize_weights(self, weights: Mapping[str, float]) -> Dict[str, float]:
        positive = {symbol: max(0.0, float(weight)) for symbol, weight in weights.items()}
        total = sum(positive.values())
        if total <= 0:
            return {}
        return {symbol: value / total for symbol, value in positive.items()}

    def _orders_to_rows(
        self,
        orders: Sequence[Order],
        plan: RebalancePlan,
        *,
        status_suffix: str = "",
    ) -> list[dict[str, object]]:
        rows: list[dict[str, object]] = []
        for order in orders:
            status = order.side.upper()
            if status_suffix:
                status = f"{status} {status_suffix}".strip()
            rows.append(
                {
                    "Order ID": "-",
                    "Symbol": order.symbol,
                    "Qty": f"{order.qty:.4f}",
                    "Price": f"{plan.latest_prices.get(order.symbol, 0.0):.2f}",
                    "Status": status,
                }
            )
        return rows


__all__ = ["TradingController"]
