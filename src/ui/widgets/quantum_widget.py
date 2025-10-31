"""Quantum backend control panel widget."""

from __future__ import annotations

from typing import Any, Iterable

from loguru import logger
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QProgressBar,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from quantum_engine.backend_manager import BackendManager
from utils.logger import log_quantum_job


class QuantumWidget(QWidget):
    """Widget offering IBM Quantum backend interactions."""

    def __init__(self, backend_manager: BackendManager | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.backend_manager = backend_manager or BackendManager()
        self._job_monitor_timer = QTimer(self)
        self._job_monitor_timer.setInterval(2_000)
        self._job_monitor_timer.timeout.connect(self._poll_job_status)
        self._active_job = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(self._build_backend_group())
        layout.addWidget(self._build_parameters_group())
        layout.addWidget(self._build_status_group())

        layout.addStretch(1)

    def _build_backend_group(self) -> QWidget:
        group = QGroupBox("Quantum Backends")
        group_layout = QVBoxLayout(group)

        self.backend_list = QListWidget()
        self.backend_list.setSelectionMode(QListWidget.SelectionMode.SingleSelection)

        refresh_btn = QPushButton("Refresh Backends")
        refresh_btn.clicked.connect(self.refresh_backends)

        group_layout.addWidget(self.backend_list)
        group_layout.addWidget(refresh_btn)
        return group

    def _build_parameters_group(self) -> QWidget:
        group = QGroupBox("Algorithm Parameters")
        layout = QGridLayout(group)

        self.layers_spin = QSpinBox()
        self.layers_spin.setRange(1, 6)
        self.layers_spin.setValue(2)

        self.iterations_spin = QSpinBox()
        self.iterations_spin.setRange(50, 10_000)
        self.iterations_spin.setSingleStep(50)
        self.iterations_spin.setValue(250)

        self.shots_spin = QSpinBox()
        self.shots_spin.setRange(256, 8_192)
        self.shots_spin.setSingleStep(256)
        self.shots_spin.setValue(2_048)

        run_btn = QPushButton("Run Optimization")
        run_btn.clicked.connect(self.start_optimization)

        layout.addWidget(QLabel("QAOA Layers"), 0, 0)
        layout.addWidget(self.layers_spin, 0, 1)
        layout.addWidget(QLabel("Max Iterations"), 1, 0)
        layout.addWidget(self.iterations_spin, 1, 1)
        layout.addWidget(QLabel("Shots"), 2, 0)
        layout.addWidget(self.shots_spin, 2, 1)
        layout.addWidget(run_btn, 3, 0, 1, 2)
        return group

    def _build_status_group(self) -> QWidget:
        group = QGroupBox("Quantum Job Status")
        layout = QGridLayout(group)

        self.backend_label = QLabel("Not Connected")
        self.queue_label = QLabel("N/A")
        self.wait_time_label = QLabel("N/A")
        self.job_status_label = QLabel("Idle")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)

        layout.addWidget(QLabel("Backend"), 0, 0)
        layout.addWidget(self.backend_label, 0, 1)
        layout.addWidget(QLabel("Queue Position"), 1, 0)
        layout.addWidget(self.queue_label, 1, 1)
        layout.addWidget(QLabel("Est. Wait"), 2, 0)
        layout.addWidget(self.wait_time_label, 2, 1)
        layout.addWidget(QLabel("Status"), 3, 0)
        layout.addWidget(self.job_status_label, 3, 1)
        layout.addWidget(self.progress_bar, 4, 0, 1, 2)
        return group

    def refresh_backends(self) -> None:
        self.backend_list.clear()
        try:
            service = self.backend_manager._authenticate()  # type: ignore[attr-defined]
            if service is None:
                self.backend_list.addItem("AerSimulator (local)")
                self.backend_label.setText("AerSimulator")
                return

            backends: Iterable[Any] = service.backends()  # type: ignore[misc]
            for backend in sorted(backends, key=lambda b: b.name):
                display = f"{backend.name} | qubits={backend.configuration().num_qubits}"
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, backend.name)
                self.backend_list.addItem(item)
            self.backend_label.setText("Select a backend")
        except Exception as exc:  # pragma: no cover - UI feedback
            logger.error("Failed to refresh quantum backends: {}", exc)
            self.backend_label.setText("Unavailable")

    def start_optimization(self) -> None:
        selected_item = self.backend_list.currentItem()
        backend_name = (
            selected_item.data(Qt.ItemDataRole.UserRole)
            if selected_item is not None
            else "AerSimulator"
        )
        self.backend_label.setText(str(backend_name))
        self.job_status_label.setText("Submitted")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)

        self._active_job = {
            "backend": backend_name,
            "layers": self.layers_spin.value(),
            "iterations": self.iterations_spin.value(),
            "shots": self.shots_spin.value(),
        }
        log_quantum_job("submitted", backend=backend_name, **self._active_job)
        self._job_monitor_timer.start()

    def _poll_job_status(self) -> None:
        if not self._active_job:
            self._job_monitor_timer.stop()
            return

        # Mocked job progression. Real integration would query BackendManager.
        status_sequence = ["Running", "Optimizing", "Finalizing", "Completed"]
        current = self.job_status_label.text()
        try:
            next_status = status_sequence[status_sequence.index(current) + 1]
        except (ValueError, IndexError):
            next_status = "Completed"

        self.job_status_label.setText(next_status)
        self.queue_label.setText("0")
        self.wait_time_label.setText("< 1 min")

        if next_status == "Completed":
            self.progress_bar.setVisible(False)
            self._job_monitor_timer.stop()
            log_quantum_job("completed", backend=self._active_job.get("backend"))
            self._active_job = None

