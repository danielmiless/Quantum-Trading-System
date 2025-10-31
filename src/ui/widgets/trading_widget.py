"""Trading interface widget for live monitoring."""

from __future__ import annotations

from typing import Iterable, Mapping

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..controllers.trading_controller import TradingController


class TradingWidget(QWidget):
    """Display real-time trading status, positions, and orders."""

    def __init__(
        self,
        controller: TradingController | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.override_callback = None
        self.controller: TradingController | None = None
        self._connected = False
        self._has_target = False
        self._build_ui()
        if controller:
            self.bind_controller(controller)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addLayout(self._build_top_section())
        layout.addLayout(self._build_tables())

    def _build_top_section(self) -> QHBoxLayout:
        section = QHBoxLayout()

        self.account_group = self._create_summary_group("Account Summary", ["Cash", "Buying Power", "Equity"])
        self.performance_group = self._create_summary_group("Performance", ["PnL", "Sharpe", "Sortino"])

        controls_group = QGroupBox("Controls")
        controls_layout = QVBoxLayout(controls_group)
        self.connection_status = QLabel("Disconnected")
        self.connection_status.setObjectName("connectionStatus")
        self.connect_button = QPushButton("Connect to Alpaca")
        self.refresh_button = QPushButton("Refresh Data")
        self.refresh_button.setEnabled(False)
        self.preview_button = QPushButton("Preview Rebalance")
        self.preview_button.setEnabled(False)
        self.execute_button = QPushButton("Execute Rebalance")
        self.execute_button.setEnabled(False)
        self.rebalance_status = QLabel("No target allocations loaded")
        self.rebalance_status.setWordWrap(True)
        self.override_button = QPushButton("Trigger Manual Override")
        self.override_button.setEnabled(False)
        self.override_button.clicked.connect(self._handle_override)
        controls_layout.addWidget(self.connection_status)
        controls_layout.addWidget(self.connect_button)
        controls_layout.addWidget(self.refresh_button)
        controls_layout.addWidget(self.preview_button)
        controls_layout.addWidget(self.execute_button)
        controls_layout.addWidget(self.override_button)
        controls_layout.addWidget(self.rebalance_status)
        controls_layout.addStretch(1)

        section.addWidget(self.account_group)
        section.addWidget(self.performance_group)
        section.addWidget(controls_group)
        return section

    def _build_tables(self) -> QHBoxLayout:
        section = QHBoxLayout()

        self.positions_table = self._create_table("Positions", ["Symbol", "Qty", "Avg Price", "P&L"])
        self.orders_table = self._create_table("Order History", ["Order ID", "Symbol", "Qty", "Price", "Status"])
        self.risk_table = self._create_table("Risk Alerts", ["Time", "Level", "Message"])

        section.addWidget(self.positions_table)
        section.addWidget(self.orders_table)
        section.addWidget(self.risk_table)
        return section

    def _create_summary_group(self, title: str, fields: Iterable[str]) -> QGroupBox:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        self_labels = {}
        for name in fields:
            label = QLabel("-")
            label.setAlignment(Qt.AlignmentFlag.AlignLeft)
            layout.addWidget(QLabel(f"{name}:"))
            layout.addWidget(label)
            self_labels[name] = label
        layout.addStretch(1)
        group.labels = self_labels  # type: ignore[attr-defined]
        return group

    def _create_table(self, title: str, headers: Iterable[str]) -> QGroupBox:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        table = QTableWidget(0, len(list(headers)))
        table.setHorizontalHeaderLabels(list(headers))
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        layout.addWidget(table)
        group.table = table  # type: ignore[attr-defined]
        return group

    # ------------------------------------------------------------------
    # Public update methods
    # ------------------------------------------------------------------
    def update_account(self, data: Mapping[str, str]) -> None:
        for key, label in getattr(self.account_group, "labels").items():
            label.setText(str(data.get(key.lower().replace(" ", "_"), "-")))

    def update_performance(self, metrics: Mapping[str, float]) -> None:
        labels = getattr(self.performance_group, "labels")
        for key, label in labels.items():
            value = metrics.get(key.lower(), "-")
            label.setText(f"{value:.4f}" if isinstance(value, (int, float)) else str(value))

    def update_positions(self, rows: Iterable[Mapping[str, object]]) -> None:
        self._populate_table(self.positions_table.table, rows)

    def update_orders(self, rows: Iterable[Mapping[str, object]]) -> None:
        self._populate_table(self.orders_table.table, rows)

    def add_risk_event(self, timestamp: str, level: str, message: str) -> None:
        table = self.risk_table.table
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(timestamp))
        table.setItem(row, 1, QTableWidgetItem(level.upper()))
        table.setItem(row, 2, QTableWidgetItem(message))

    def set_manual_override_callback(self, callback) -> None:
        self.override_callback = callback

    def bind_controller(self, controller: TradingController) -> None:
        """Attach a trading controller and wire UI callbacks."""

        if self.controller is not None:
            self.connect_button.clicked.disconnect()
            self.refresh_button.clicked.disconnect()
            self.preview_button.clicked.disconnect()
            self.execute_button.clicked.disconnect()
            self.controller.connection_changed.disconnect(self._handle_connection_state)
            self.controller.account_updated.disconnect(self.update_account)
            self.controller.performance_updated.disconnect(self.update_performance)
            self.controller.positions_updated.disconnect(self.update_positions)
            self.controller.orders_updated.disconnect(self.update_orders)
            self.controller.status_message.disconnect(self._handle_status_message)
            self.controller.target_updated.disconnect(self._handle_target_update)

        self.controller = controller
        self.connect_button.clicked.connect(controller.connect_to_alpaca)
        self.refresh_button.clicked.connect(controller.refresh_data)
        self.preview_button.clicked.connect(controller.preview_rebalance)
        self.execute_button.clicked.connect(controller.execute_rebalance)
        controller.connection_changed.connect(self._handle_connection_state)
        controller.account_updated.connect(self.update_account)
        controller.performance_updated.connect(self.update_performance)
        controller.positions_updated.connect(self.update_positions)
        controller.orders_updated.connect(self.update_orders)
        controller.status_message.connect(self._handle_status_message)
        controller.target_updated.connect(self._handle_target_update)
        self._update_action_buttons()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _populate_table(self, table: QTableWidget, rows: Iterable[Mapping[str, object]]) -> None:
        headers = [table.horizontalHeaderItem(i).text() for i in range(table.columnCount())]
        table.setRowCount(0)
        for row_data in rows:
            row_idx = table.rowCount()
            table.insertRow(row_idx)
            for col, header in enumerate(headers):
                value = row_data.get(header, "")
                table.setItem(row_idx, col, QTableWidgetItem(str(value)))

    def _handle_override(self) -> None:
        if self.override_callback:
            self.override_callback()

    def _handle_connection_state(self, connected: bool, message: str) -> None:
        self.connection_status.setText(message)
        palette = "color: #56d364;" if connected else "color: #f85149;"
        self.connection_status.setStyleSheet(palette)
        self._connected = connected
        self.refresh_button.setEnabled(connected)
        self.override_button.setEnabled(connected)
        self._update_action_buttons()

    def _handle_status_message(self, level: str, message: str) -> None:
        palette_map = {
            "success": "color: #56d364;",
            "info": "color: #8b949e;",
            "warning": "color: #d29922;",
            "error": "color: #f85149;",
        }
        self.rebalance_status.setStyleSheet(palette_map.get(level.lower(), ""))
        self.rebalance_status.setText(message)

    def _handle_target_update(self, symbols: list[str]) -> None:
        self._has_target = bool(symbols)
        if self._has_target:
            self.rebalance_status.setText(
                f"Target allocations loaded for {len(symbols)} assets"
            )
        else:
            self.rebalance_status.setText("No target allocations loaded")
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        enabled = self._connected and self._has_target
        self.preview_button.setEnabled(enabled)
        self.execute_button.setEnabled(enabled)


__all__ = ["TradingWidget"]

