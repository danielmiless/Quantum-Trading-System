"""Analytics dashboard widget for the desktop client."""

from __future__ import annotations

from typing import Mapping, Optional

import numpy as np
import pandas as pd
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from analytics.backtester import BacktestResult


class AnalyticsWidget(QWidget):
    """Interactive analytics dashboard combining performance and risk views."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addLayout(self._build_chart_section())
        layout.addLayout(self._build_metrics_section())

    def _build_chart_section(self) -> QHBoxLayout:
        section = QHBoxLayout()
        self.performance_canvas = self._create_canvas()
        self.drawdown_canvas = self._create_canvas()

        perf_group = QGroupBox("Performance")
        perf_layout = QVBoxLayout(perf_group)
        perf_layout.addWidget(self.performance_canvas)

        draw_group = QGroupBox("Drawdown")
        draw_layout = QVBoxLayout(draw_group)
        draw_layout.addWidget(self.drawdown_canvas)

        section.addWidget(perf_group, stretch=2)
        section.addWidget(draw_group, stretch=2)
        return section

    def _build_metrics_section(self) -> QHBoxLayout:
        section = QHBoxLayout()

        self.metrics_table = self._create_table("Performance Metrics")
        self.risk_table = self._create_table("Risk Dashboard")
        self.benchmark_table = self._create_table("Benchmark Comparison")

        section.addWidget(self.metrics_table)
        section.addWidget(self.risk_table)
        section.addWidget(self.benchmark_table)
        return section

    def _create_canvas(self) -> FigureCanvasQTAgg:
        figure = Figure(figsize=(5, 3), tight_layout=True)
        return FigureCanvasQTAgg(figure)

    def _create_table(self, title: str) -> QGroupBox:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Metric", "Value"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        layout.addWidget(table)
        group.table = table  # type: ignore[attr-defined]
        return group

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def update_backtest(self, result: BacktestResult) -> None:
        self._plot_performance(result.returns)
        self._plot_drawdown(result.returns["portfolio"])
        self._populate_table(self.metrics_table.table, result.metrics)

    def update_risk_metrics(self, risk_metrics: Mapping[str, float | str]) -> None:
        self._populate_table(self.risk_table.table, risk_metrics)

    def update_benchmark(self, benchmark_metrics: Mapping[str, float | str]) -> None:
        self._populate_table(self.benchmark_table.table, benchmark_metrics)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _populate_table(self, table: QTableWidget, metrics: Mapping[str, float | str]) -> None:
        table.setRowCount(len(metrics))
        for row, (key, value) in enumerate(metrics.items()):
            table.setItem(row, 0, QTableWidgetItem(str(key)))
            if isinstance(value, (int, float, np.number)):
                display = f"{float(value):.4f}"
            else:
                display = str(value)
            table.setItem(row, 1, QTableWidgetItem(display))

    def _plot_performance(self, returns: pd.DataFrame) -> None:
        ax = self.performance_canvas.figure.subplots()
        ax.clear()
        cumulative = (1 + returns.fillna(0)).cumprod()
        cumulative.plot(ax=ax)
        ax.set_title("Cumulative Returns")
        ax.set_ylabel("Growth of $1")
        ax.legend(loc="upper left")
        self.performance_canvas.draw()

    def _plot_drawdown(self, portfolio_returns: pd.Series) -> None:
        ax = self.drawdown_canvas.figure.subplots()
        ax.clear()
        cumulative = (1 + portfolio_returns.fillna(0)).cumprod()
        running_max = cumulative.cummax()
        drawdown = cumulative / running_max - 1
        drawdown.plot(ax=ax, color="tab:red")
        ax.set_title("Drawdown")
        ax.set_ylabel("Drawdown")
        ax.fill_between(drawdown.index, drawdown.values, color="tab:red", alpha=0.2)
        self.drawdown_canvas.draw()


__all__ = ["AnalyticsWidget"]

