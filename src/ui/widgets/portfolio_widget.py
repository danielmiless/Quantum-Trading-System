"""Portfolio management interface widget."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger
from PySide6.QtCore import Qt, QStringListModel
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCompleter,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..utils.signal_manager import SignalManager


COMMON_TICKERS = [
    "AAPL",
    "MSFT",
    "GOOGL",
    "AMZN",
    "NVDA",
    "TSLA",
    "META",
    "BRK.B",
    "JPM",
    "V",
    "UNH",
    "JNJ",
    "XOM",
    "PG",
    "MA",
    "KO",
]


@dataclass(slots=True)
class PortfolioSummary:
    total_value: float
    expected_return: float
    risk: float


class PortfolioWidget(QWidget):
    """Widget encapsulating portfolio composition workflows."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._signal_manager = SignalManager.instance()
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addLayout(self._build_symbol_entry())
        layout.addWidget(self._build_allocation_table())
        layout.addWidget(self._build_risk_controls())
        layout.addWidget(self._build_summary_panel())
        layout.addLayout(self._build_action_buttons())

        self._update_summary()

    def _build_symbol_entry(self) -> QHBoxLayout:
        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Add stock symbol (e.g., AAPL)")
        self.symbol_input.setClearButtonEnabled(True)
        completer_model = QStringListModel(COMMON_TICKERS, self)
        self.symbol_input.setCompleter(self._create_completer(completer_model))
        self.symbol_input.returnPressed.connect(self._handle_symbol_submit)

        add_button = QPushButton("Add Asset")
        add_button.clicked.connect(self._handle_symbol_submit)
        add_button.setIcon(QIcon.fromTheme("list-add"))

        row = QHBoxLayout()
        row.addWidget(QLabel("Symbol:"))
        row.addWidget(self.symbol_input, stretch=1)
        row.addWidget(add_button)
        return row

    def _create_completer(self, model: QStringListModel) -> Any:
        completer = QCompleter(model, self)
        completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        return completer

    def _build_allocation_table(self) -> QWidget:
        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["Symbol", "Allocation %", "Expected Return %"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.EditTrigger.AllEditTriggers)
        self.table.itemChanged.connect(self._handle_table_change)
        return self.table

    def _build_risk_controls(self) -> QWidget:
        group = QGroupBox("Risk Parameters")
        form = QFormLayout(group)

        self.risk_slider = QSlider(Qt.Orientation.Horizontal)
        self.risk_slider.setRange(0, 100)
        self.risk_slider.setValue(50)
        self.risk_slider.valueChanged.connect(self._update_summary)

        self.constraint_slider = QSlider(Qt.Orientation.Horizontal)
        self.constraint_slider.setRange(0, 100)
        self.constraint_slider.setValue(30)
        self.constraint_slider.valueChanged.connect(self._update_summary)

        self.max_assets_spin = QSpinBox()
        self.max_assets_spin.setRange(1, 20)
        self.max_assets_spin.setValue(10)
        self.max_assets_spin.valueChanged.connect(self._update_summary)

        form.addRow("Risk Aversion", self.risk_slider)
        form.addRow("Constraint Penalty", self.constraint_slider)
        form.addRow("Max Assets", self.max_assets_spin)
        return group

    def _build_summary_panel(self) -> QWidget:
        self.total_value_label = QLabel("0.00")
        self.expected_return_label = QLabel("0.00")
        self.risk_label = QLabel("0.00")

        group = QGroupBox("Portfolio Summary")
        form = QFormLayout(group)
        form.addRow("Total Allocation (%)", self.total_value_label)
        form.addRow("Projected Return (%)", self.expected_return_label)
        form.addRow("Risk Score", self.risk_label)
        return group

    def _build_action_buttons(self) -> QHBoxLayout:
        save_btn = QPushButton("Save Portfolio")
        save_btn.clicked.connect(self._save_portfolio)
        save_btn.setIcon(QIcon.fromTheme("document-save"))

        load_btn = QPushButton("Load Portfolio")
        load_btn.clicked.connect(self._load_portfolio)
        load_btn.setIcon(QIcon.fromTheme("document-open"))

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(save_btn)
        row.addWidget(load_btn)
        return row

    def _handle_symbol_submit(self) -> None:
        symbol = self.symbol_input.text().strip().upper()
        if not symbol:
            return

        existing_symbols = [self.table.item(row, 0).text() for row in range(self.table.rowCount())]
        if symbol in existing_symbols:
            logger.warning("Symbol {} already exists in portfolio", symbol)
            self.symbol_input.clear()
            return

        row_position = self.table.rowCount()
        self.table.insertRow(row_position)
        self.table.setItem(row_position, 0, QTableWidgetItem(symbol))
        self.table.setItem(row_position, 1, self._create_numeric_item("10.0"))
        self.table.setItem(row_position, 2, self._create_numeric_item("8.0"))
        self.symbol_input.clear()
        self._update_summary()

    def _create_numeric_item(self, value: str) -> QTableWidgetItem:
        item = QTableWidgetItem(value)
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return item

    def _handle_table_change(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            item.setText(item.text().strip().upper())
            self._update_summary()
            return

        try:
            float(item.text())
        except ValueError:
            logger.error("Invalid numeric input: {}", item.text())
            item.setText("0.0")
        finally:
            self._update_summary()

    def _gather_portfolio_data(self) -> list[dict[str, float | str]]:
        portfolio: list[dict[str, float | str]] = []
        for row in range(self.table.rowCount()):
            symbol_item = self.table.item(row, 0)
            allocation_item = self.table.item(row, 1)
            return_item = self.table.item(row, 2)
            if not symbol_item:
                continue
            symbol = symbol_item.text().strip().upper()
            if not symbol:
                continue
            try:
                allocation = float(allocation_item.text()) if allocation_item else 0.0
                expected_return = float(return_item.text()) if return_item else 0.0
            except (ValueError, AttributeError):
                allocation = 0.0
                expected_return = 0.0
            portfolio.append(
                {
                    "symbol": symbol,
                    "allocation": allocation,
                    "expected_return": expected_return,
                }
            )
        return portfolio

    def _update_summary(self) -> None:
        portfolio = self._gather_portfolio_data()
        if not portfolio:
            summary = PortfolioSummary(0.0, 0.0, 0.0)
        else:
            allocations = np.array([asset["allocation"] for asset in portfolio], dtype=float)
            returns = np.array([asset["expected_return"] for asset in portfolio], dtype=float)
            total_allocation = allocations.sum()
            normalized_returns = np.dot(allocations, returns) / max(total_allocation, 1.0)
            risk_score = float(self.risk_slider.value()) / 100 + float(self.constraint_slider.value()) / 120
            summary = PortfolioSummary(total_allocation, normalized_returns, risk_score)

        self.total_value_label.setText(f"{summary.total_value:.2f}")
        self.expected_return_label.setText(f"{summary.expected_return:.2f}")
        self.risk_label.setText(f"{summary.risk:.2f}")
        self._broadcast_portfolio(portfolio, summary)

    def _save_portfolio(self) -> None:
        portfolio = self._gather_portfolio_data()
        if not portfolio:
            logger.warning("Cannot save empty portfolio")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Portfolio",
            str(Path.home() / "portfolio.json"),
            "JSON Files (*.json)",
        )
        if not file_path:
            return

        payload = {
            "assets": portfolio,
            "risk_aversion": self.risk_slider.value(),
            "constraint": self.constraint_slider.value(),
            "max_assets": self.max_assets_spin.value(),
        }

        try:
            Path(file_path).write_text(json.dumps(payload, indent=2))
            logger.success("Portfolio saved to {}", file_path)
        except OSError as exc:
            logger.error("Failed to save portfolio: {}", exc)

    def _load_portfolio(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Portfolio",
            str(Path.home()),
            "JSON Files (*.json)",
        )
        if not file_path:
            return

        try:
            data = json.loads(Path(file_path).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to load portfolio: {}", exc)
            return

        self.table.setRowCount(0)
        for asset in data.get("assets", []):
            symbol = str(asset.get("symbol", "")).upper()
            allocation = float(asset.get("allocation", 0.0))
            expected_return = float(asset.get("expected_return", 0.0))
            row_position = self.table.rowCount()
            self.table.insertRow(row_position)
            self.table.setItem(row_position, 0, QTableWidgetItem(symbol))
            self.table.setItem(row_position, 1, self._create_numeric_item(f"{allocation:.2f}"))
            self.table.setItem(row_position, 2, self._create_numeric_item(f"{expected_return:.2f}"))

        self.risk_slider.setValue(int(data.get("risk_aversion", 50)))
        self.constraint_slider.setValue(int(data.get("constraint", 30)))
        self.max_assets_spin.setValue(int(data.get("max_assets", 10)))
        self._update_summary()

    def _broadcast_portfolio(
        self, assets: list[dict[str, float | str]], summary: PortfolioSummary
    ) -> None:
        if not assets:
            return

        payload = {
            "assets": assets,
            "risk_aversion": float(self.risk_slider.value()) / 100.0,
            "constraint": float(self.constraint_slider.value()) / 100.0,
            "max_assets": self.max_assets_spin.value(),
            "totals": {
                "allocation_percent": summary.total_value,
                "expected_return": summary.expected_return,
                "risk_score": summary.risk,
            },
        }
        self._signal_manager.portfolio_updated.emit(payload)

