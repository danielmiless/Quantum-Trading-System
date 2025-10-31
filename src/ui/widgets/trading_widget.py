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


class TradingWidget(QWidget):
    """Display real-time trading status, positions, and orders."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.override_callback = None
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addLayout(self._build_top_section())
        layout.addLayout(self._build_tables())

    def _build_top_section(self) -> QHBoxLayout:
        section = QHBoxLayout()

        self.account_group = self._create_summary_group("Account Summary", ["Cash", "Buying Power", "Equity"])
        self.performance_group = self._create_summary_group("Performance", ["PnL", "Sharpe", "Sortino"])

        override_group = QGroupBox("Controls")
        override_layout = QVBoxLayout(override_group)
        self.override_button = QPushButton("Trigger Manual Override")
        self.override_button.clicked.connect(self._handle_override)
        override_layout.addWidget(self.override_button)
        override_layout.addStretch(1)

        section.addWidget(self.account_group)
        section.addWidget(self.performance_group)
        section.addWidget(override_group)
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

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _populate_table(self, table: QTableWidget, rows: Iterable[Mapping[str, object]]) -> None:
        table.setRowCount(0)
        for row_data in rows:
            row = table.rowCount()
            table.insertRow(row)
            for col, value in enumerate(row_data.values()):
                table.setItem(row, col, QTableWidgetItem(str(value)))

    def _handle_override(self) -> None:
        if self.override_callback:
            self.override_callback()


__all__ = ["TradingWidget"]

