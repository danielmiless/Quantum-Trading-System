"""Integration tests covering the UI to quantum engine bridge."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from ui.controllers.quantum_controller import QuantumController, QuantumJobConfig
from ui.controllers.portfolio_controller import PortfolioAsset, PortfolioController
from ui.utils.signal_manager import SignalManager
from ui.widgets.results_widget import OptimizationPerformance, ResultsWidget


@pytest.fixture(scope="session")
def app() -> QApplication:
    application = QApplication.instance() or QApplication(sys.argv)
    return application


@pytest.fixture
def signal_manager() -> SignalManager:
    return SignalManager.instance()


def wait_for_signal(app: QApplication, signal, timeout: int = 5_000) -> None:
    loop = QEventLoop()

    def handler(*_args, **_kwargs) -> None:
        loop.quit()

    signal.connect(handler)
    timer = QTimer()
    timer.setSingleShot(True)
    timer.timeout.connect(loop.quit)
    timer.start(timeout)
    loop.exec()
    signal.disconnect(handler)
    if timer.remainingTime() == 0:
        pytest.fail("Timeout while waiting for signal")


def test_quantum_workflow_success(app: QApplication, signal_manager: SignalManager) -> None:
    controller = QuantumController()
    results: dict | None = None

    def capture(payload: dict) -> None:
        nonlocal results
        results = payload

    controller.job_completed.connect(capture)

    returns = [0.12, 0.1, 0.08, 0.07, 0.06]
    cov = np.identity(5).tolist()

    controller.start_optimization(returns, cov, QuantumJobConfig(num_layers=1, shots=128, budget=2))
    wait_for_signal(app, controller.job_completed, timeout=15_000)

    assert results is not None
    assert "weights" in results
    assert pytest.approx(sum(results["weights"])) == 1.0


def test_quantum_workflow_failure(app: QApplication, monkeypatch, signal_manager: SignalManager) -> None:
    controller = QuantumController()
    errors: list[str] = []
    controller.job_failed.connect(errors.append)

    def fail_run(self):  # noqa: ANN001
        raise RuntimeError("Injected failure")

    monkeypatch.setattr("ui.workers.quantum_worker.QuantumWorker._execute_optimization", fail_run)

    controller.start_optimization([0.1] * 5, np.identity(5).tolist(), QuantumJobConfig())
    wait_for_signal(app, controller.job_failed)
    assert errors and "Injected failure" in errors[0]


def test_ui_responsiveness_during_job(app: QApplication, signal_manager: SignalManager) -> None:
    controller = QuantumController()
    heartbeat = {"ticks": 0}

    def on_progress(value: int, message: str) -> None:
        heartbeat["ticks"] += 1

    controller.job_progress.connect(on_progress)
    controller.start_optimization([0.1] * 5, np.identity(5).tolist(), QuantumJobConfig(shots=64))

    timer = QTimer()
    timer.start(2_000)
    while controller.history == [] and timer.isActive():
        app.processEvents()

    assert heartbeat["ticks"] > 0


def test_results_visualization_accuracy(app: QApplication) -> None:
    widget = ResultsWidget()
    labels = ["AAPL", "MSFT", "GOOGL"]
    q_weights = [0.4, 0.3, 0.3]
    c_weights = [0.33, 0.33, 0.34]
    performance = OptimizationPerformance(
        quantum_return=12.0,
        classical_return=10.0,
        quantum_risk=0.2,
        classical_risk=0.25,
    )
    widget.update_results(
        labels,
        q_weights,
        c_weights,
        performance,
        execution_time=1.5,
        probability=0.8,
        backend="AerSimulator",
        estimated_cost=0.05,
    )

    assert widget.comparison_table.rowCount() == 2
    assert widget.comparison_table.item(0, 1).text() == "12.00"
    assert widget.execution_time_label.text() == "1.50s"


def test_portfolio_controller_validation(tmp_path: Path, signal_manager: SignalManager) -> None:
    controller = PortfolioController()
    assets = [
        PortfolioAsset(symbol="AAPL", allocation=50.0, expected_return=8.0),
        PortfolioAsset(symbol="MSFT", allocation=50.0, expected_return=7.0),
    ]
    payload = controller.create_portfolio(assets, risk_aversion=0.5, max_assets=5)
    file_path = tmp_path / "portfolio.json"
    controller.save_portfolio(file_path, payload)
    loaded = controller.load_portfolio(file_path)
    assert loaded["assets"][0]["symbol"] == "AAPL"

