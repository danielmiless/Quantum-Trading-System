"""Settings dialog providing configuration panels for the application."""

from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLineEdit,
    QMessageBox,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..utils.validators import NumericRangeValidator


class SettingsDialog(QDialog):
    """Configuration interface for quantum, market, and display settings."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(520, 420)
        self._settings = QSettings("Quantum Trading Labs", "Quantum Portfolio Optimizer")
        self._build_ui()
        self._load_settings()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget(self)
        self.tabs.addTab(self._build_quantum_page(), "Quantum")
        self.tabs.addTab(self._build_market_page(), "Market Data")
        self.tabs.addTab(self._build_display_page(), "Display")
        self.tabs.addTab(self._build_performance_page(), "Performance")

        layout.addWidget(self.tabs)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._persist_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _build_quantum_page(self) -> QWidget:
        widget = QWidget(self)
        form = QFormLayout(widget)

        self.ibm_token_input = QLineEdit()
        self.ibm_instance_input = QLineEdit()
        self.backend_preference_input = QLineEdit()

        form.addRow("IBM Quantum Token", self.ibm_token_input)
        form.addRow("IBM Instance", self.ibm_instance_input)
        form.addRow("Preferred Backend", self.backend_preference_input)
        return widget

    def _build_market_page(self) -> QWidget:
        widget = QWidget(self)
        form = QFormLayout(widget)

        self.alpha_vantage_input = QLineEdit()
        self.yahoo_enabled_input = QLineEdit()

        self.yahoo_enabled_input.setPlaceholderText("true/false")

        form.addRow("Alpha Vantage API Key", self.alpha_vantage_input)
        form.addRow("Yahoo Finance Enabled", self.yahoo_enabled_input)
        return widget

    def _build_display_page(self) -> QWidget:
        widget = QWidget(self)
        form = QFormLayout(widget)

        self.theme_input = QLineEdit()
        self.update_interval_spin = QSpinBox()
        self.update_interval_spin.setRange(1, 60)
        self.update_interval_spin.setSuffix(" min")

        form.addRow("Theme", self.theme_input)
        form.addRow("Update Interval", self.update_interval_spin)
        return widget

    def _build_performance_page(self) -> QWidget:
        widget = QWidget(self)
        form = QFormLayout(widget)

        self.cache_size_input = QLineEdit()
        self.timeout_input = QLineEdit()

        self.cache_size_input.setValidator(NumericRangeValidator(10, 10_000, 0))
        self.timeout_input.setValidator(NumericRangeValidator(5, 600, 0))

        form.addRow("Cache Size (MB)", self.cache_size_input)
        form.addRow("Timeout (s)", self.timeout_input)
        return widget

    def _load_settings(self) -> None:
        self.ibm_token_input.setText(self._settings.value("quantum/token", ""))
        self.ibm_instance_input.setText(self._settings.value("quantum/instance", ""))
        self.backend_preference_input.setText(self._settings.value("quantum/backend", ""))

        self.alpha_vantage_input.setText(self._settings.value("market/alpha_vantage", ""))
        self.yahoo_enabled_input.setText(self._settings.value("market/yahoo_enabled", "true"))

        self.theme_input.setText(self._settings.value("display/theme", "light"))
        self.update_interval_spin.setValue(int(self._settings.value("display/update_interval", 5)))

        self.cache_size_input.setText(str(self._settings.value("performance/cache_size", "128")))
        self.timeout_input.setText(str(self._settings.value("performance/timeout", "60")))

    def _persist_settings(self) -> None:
        if self.yahoo_enabled_input.text().lower() not in {"true", "false"}:
            QMessageBox.warning(self, "Validation Error", "Yahoo Finance enabled must be true or false")
            return

        if not self.cache_size_input.hasAcceptableInput() or not self.timeout_input.hasAcceptableInput():
            QMessageBox.warning(self, "Validation Error", "Performance settings are invalid")
            return

        self._settings.setValue("quantum/token", self.ibm_token_input.text())
        self._settings.setValue("quantum/instance", self.ibm_instance_input.text())
        self._settings.setValue("quantum/backend", self.backend_preference_input.text())

        self._settings.setValue("market/alpha_vantage", self.alpha_vantage_input.text())
        self._settings.setValue("market/yahoo_enabled", self.yahoo_enabled_input.text())

        self._settings.setValue("display/theme", self.theme_input.text())
        self._settings.setValue("display/update_interval", self.update_interval_spin.value())

        self._settings.setValue("performance/cache_size", self.cache_size_input.text())
        self._settings.setValue("performance/timeout", self.timeout_input.text())

        self.accept()


__all__ = ["SettingsDialog"]

