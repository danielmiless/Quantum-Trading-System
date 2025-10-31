"""Visualization widget presenting optimization results."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("QtAgg")

import numpy as np
from loguru import logger
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

@dataclass(slots=True)
class OptimizationPerformance:
    quantum_return: float
    classical_return: float
    quantum_risk: float
    classical_risk: float


class ResultsWidget(QWidget):
    """Widget combining charts and comparative analytics."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        charts_group = QGroupBox("Visualizations")
        charts_layout = QHBoxLayout(charts_group)
        self.pie_canvas = self._create_canvas()
        self.risk_return_canvas = self._create_canvas()
        charts_layout.addWidget(self.pie_canvas)
        charts_layout.addWidget(self.risk_return_canvas)

        layout.addWidget(charts_group)
        layout.addWidget(self._build_comparison_table())
        layout.addWidget(self._build_metrics_group())
        layout.addLayout(self._build_export_row())

    def _create_canvas(self) -> FigureCanvasQTAgg:
        figure = Figure(figsize=(4, 3), tight_layout=True)
        return FigureCanvasQTAgg(figure)

    def _build_comparison_table(self) -> QWidget:
        self.comparison_table = QTableWidget(0, 3)
        self.comparison_table.setHorizontalHeaderLabels(["Metric", "Quantum", "Classical"])
        self.comparison_table.horizontalHeader().setStretchLastSection(True)
        self.comparison_table.verticalHeader().setVisible(False)
        self.comparison_table.setAlternatingRowColors(True)
        return self.comparison_table

    def _build_metrics_group(self) -> QWidget:
        group = QGroupBox("Performance Metrics")
        layout = QGridLayout(group)

        self.execution_time_label = QLabel("0.0s")
        self.probability_label = QLabel("0.0")
        self.backend_label = QLabel("N/A")
        self.cost_label = QLabel("$0.00")

        layout.addWidget(QLabel("Execution Time"), 0, 0)
        layout.addWidget(self.execution_time_label, 0, 1)
        layout.addWidget(QLabel("Success Probability"), 1, 0)
        layout.addWidget(self.probability_label, 1, 1)
        layout.addWidget(QLabel("Backend"), 2, 0)
        layout.addWidget(self.backend_label, 2, 1)
        layout.addWidget(QLabel("Estimated Cost"), 3, 0)
        layout.addWidget(self.cost_label, 3, 1)
        return group

    def _build_export_row(self) -> QHBoxLayout:
        export_csv_btn = QPushButton("Export CSV")
        export_csv_btn.clicked.connect(self._export_csv)

        export_png_btn = QPushButton("Export Charts PNG")
        export_png_btn.clicked.connect(self._export_png)

        export_pdf_btn = QPushButton("Export Report PDF")
        export_pdf_btn.clicked.connect(self._export_pdf)

        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(export_csv_btn)
        row.addWidget(export_png_btn)
        row.addWidget(export_pdf_btn)
        return row

    def update_results(
        self,
        asset_labels: Sequence[str],
        quantum_weights: Sequence[float],
        classical_weights: Sequence[float],
        performance: OptimizationPerformance,
        *,
        execution_time: float,
        probability: float,
        backend: str,
        estimated_cost: float,
    ) -> None:
        self._update_pie_chart(asset_labels, quantum_weights)
        self._update_risk_return(performance)
        self._populate_comparison_table(performance)
        self.execution_time_label.setText(f"{execution_time:.2f}s")
        self.probability_label.setText(f"{probability:.2%}")
        self.backend_label.setText(backend)
        self.cost_label.setText(f"${estimated_cost:,.2f}")

    def _update_pie_chart(self, labels: Sequence[str], weights: Sequence[float]) -> None:
        ax = self.pie_canvas.figure.subplots()
        ax.clear()
        total = sum(weights)
        if total <= 0:
            ax.text(0.5, 0.5, "No data", ha="center", va="center")
        else:
            normalized = [max(weight, 0) for weight in weights]
            ax.pie(normalized, labels=labels, autopct="%1.1f%%", startangle=90)
        self.pie_canvas.draw()

    def _update_risk_return(self, performance: OptimizationPerformance) -> None:
        ax = self.risk_return_canvas.figure.subplots()
        ax.clear()
        ax.scatter(performance.classical_risk, performance.classical_return, color="gray", label="Classical")
        ax.scatter(performance.quantum_risk, performance.quantum_return, color="tab:green", label="Quantum")
        ax.set_xlabel("Risk (σ)")
        ax.set_ylabel("Return (%)")
        ax.legend()
        self.risk_return_canvas.draw()

    def _populate_comparison_table(self, performance: OptimizationPerformance) -> None:
        metrics = {
            "Return (%)": (performance.quantum_return, performance.classical_return),
            "Risk": (performance.quantum_risk, performance.classical_risk),
        }
        self.comparison_table.setRowCount(len(metrics))
        for row, (metric, values) in enumerate(metrics.items()):
            self.comparison_table.setItem(row, 0, QTableWidgetItem(metric))
            self.comparison_table.setItem(row, 1, self._format_value(values[0]))
            self.comparison_table.setItem(row, 2, self._format_value(values[1]))

    def _format_value(self, value: float) -> QTableWidgetItem:
        item = QTableWidgetItem(f"{value:.2f}")
        item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        return item

    def _export_csv(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Comparison CSV",
            str(Path.home() / "quantum_results.csv"),
            "CSV Files (*.csv)",
        )
        if not file_path:
            return

        try:
            with open(file_path, "w", newline="", encoding="utf-8") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(["Metric", "Quantum", "Classical"])
                for row in range(self.comparison_table.rowCount()):
                    metric = self.comparison_table.item(row, 0).text()
                    quantum = self.comparison_table.item(row, 1).text()
                    classical = self.comparison_table.item(row, 2).text()
                    writer.writerow([metric, quantum, classical])
            logger.success("Exported comparison CSV to {}", file_path)
        except OSError as exc:
            logger.error("Failed to export CSV: {}", exc)

    def _export_png(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Charts PNG",
            str(Path.home() / "quantum_results.png"),
            "PNG Files (*.png)",
        )
        if not file_path:
            return

        try:
            self.pie_canvas.figure.savefig(file_path, dpi=300)
            logger.success("Saved charts to {}", file_path)
        except OSError as exc:
            logger.error("Failed to export charts: {}", exc)

    def _export_pdf(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Report PDF",
            str(Path.home() / "quantum_report.pdf"),
            "PDF Files (*.pdf)",
        )
        if not file_path:
            return

        try:
            from matplotlib.backends.backend_pdf import PdfPages

            with PdfPages(file_path) as pdf:
                pdf.savefig(self.pie_canvas.figure)
                pdf.savefig(self.risk_return_canvas.figure)
            logger.success("Exported PDF report to {}", file_path)
        except (ImportError, OSError) as exc:
            logger.error("Failed to export PDF report: {}", exc)

