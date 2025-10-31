"""Widget-level tests ensuring UI components behave as expected."""

from __future__ import annotations

import sys

import pytest
from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow
from ui.styles import Theme
from ui.utils.signal_manager import SignalManager
from ui.utils.validators import PercentageValidator, StockSymbolValidator
from ui.widgets.portfolio_widget import PortfolioWidget
from ui.widgets.quantum_widget import QuantumWidget
from ui.widgets.results_widget import OptimizationPerformance, ResultsWidget


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance() or QApplication(sys.argv)
    return application


def test_portfolio_widget_add_asset(app: QApplication) -> None:
    widget = PortfolioWidget()
    widget.symbol_input.setText("AAPL")
    widget._handle_symbol_submit()
    assert widget.table.rowCount() == 1
    assert widget.table.item(0, 0).text() == "AAPL"


def test_quantum_widget_progress_emission(monkeypatch) -> None:
    widget = QuantumWidget()

    def fake_refresh():
        widget.backend_list.addItem("AerSimulator")
        widget.backend_list.setCurrentRow(0)

    monkeypatch.setattr(widget.backend_manager, "_authenticate", lambda: None)
    widget.refresh_backends = fake_refresh  # type: ignore[assignment]
    widget.refresh_backends()
    widget.start_optimization()
    SignalManager.instance().quantum_job_progress.emit(50, "Testing")
    assert widget.backend_label.text() == "AerSimulator"
    assert widget.job_status_label.text() == "Testing"


def test_theme_switching(app: QApplication) -> None:
    window = MainWindow()
    Theme.apply_dark_theme(app)
    window.apply_theme("dark")
    assert window.theme_dark_action.isChecked()
    Theme.apply_light_theme(app)
    window.apply_theme("light")
    assert window.theme_light_action.isChecked()


def test_results_widget_update() -> None:
    widget = ResultsWidget()
    performance = OptimizationPerformance(quantum_return=15.0, classical_return=10.0, quantum_risk=0.3, classical_risk=0.4)
    widget.update_results(
        ["A", "B"],
        [0.6, 0.4],
        [0.5, 0.5],
        performance,
        execution_time=2.5,
        probability=0.75,
        backend="AerSimulator",
        estimated_cost=0.1,
    )
    assert widget.probability_label.text() == "75.00%"


def test_validators_behaviour() -> None:
    symbol_validator = StockSymbolValidator()
    state, _, _ = symbol_validator.validate("AAPL", 0)
    assert state == symbol_validator.State.Acceptable

    percent_validator = PercentageValidator()
    state, *_ = percent_validator.validate("101", 0)
    assert state == percent_validator.State.Invalid

