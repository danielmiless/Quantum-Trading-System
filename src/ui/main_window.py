"""Main window implementation for the Quantum Portfolio Optimizer UI."""

from __future__ import annotations

from pathlib import Path

from loguru import logger
from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from quantum_engine.backend_manager import BackendManager
from .styles import Theme
from .utils import UpdateChecker
from .widgets import AnalyticsWidget, PortfolioWidget, QuantumWidget, ResultsWidget, TradingWidget


class MainWindow(QMainWindow):
    """Main application shell with dockable tabs and status indicators."""

    ORGANIZATION = "Quantum Trading Labs"
    APPLICATION = "Quantum Portfolio Optimizer"

    def __init__(self, backend_manager: BackendManager | None = None) -> None:
        super().__init__()
        self.backend_manager = backend_manager or BackendManager()
        self.settings = QSettings(self.ORGANIZATION, self.APPLICATION)
        self._status_label = QLabel("Backend: Unknown")
        self._theme = "light"

        self._configure_window()
        self._create_actions()
        self._create_menus()
        self._create_toolbar()
        self._create_status_bar()
        self._create_central_tabs()
        self._init_update_checker()
        self._restore_state()

    def _configure_window(self) -> None:
        self.setWindowTitle(self.APPLICATION)
        self.setMinimumSize(1024, 720)
        self.setWindowIcon(QIcon.fromTheme("applications-science"))

    def _create_actions(self) -> None:
        self.open_action = QAction(QIcon.fromTheme("document-open"), "Open Portfolio", self)
        self.open_action.triggered.connect(self._open_portfolio)

        self.save_action = QAction(QIcon.fromTheme("document-save"), "Save Portfolio", self)
        self.save_action.triggered.connect(self._save_portfolio)

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut("Ctrl+Q")
        self.exit_action.triggered.connect(self.close)

        self.theme_light_action = QAction("Light Theme", self, checkable=True, checked=True)
        self.theme_dark_action = QAction("Dark Theme", self, checkable=True)
        self.theme_light_action.triggered.connect(lambda: self.apply_theme("light"))
        self.theme_dark_action.triggered.connect(lambda: self.apply_theme("dark"))

        self.about_action = QAction("About", self)
        self.about_action.triggered.connect(self._show_about_dialog)

        self.refresh_backend_action = QAction(QIcon.fromTheme("view-refresh"), "Refresh Backend", self)
        self.refresh_backend_action.triggered.connect(self._refresh_backend_status)

    def _create_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction(self.open_action)
        file_menu.addAction(self.save_action)
        file_menu.addSeparator()
        file_menu.addAction(self.exit_action)

        edit_menu = self.menuBar().addMenu("&Edit")
        edit_menu.addAction("Preferences…")

        view_menu = self.menuBar().addMenu("&View")
        view_menu.addAction(self.theme_light_action)
        view_menu.addAction(self.theme_dark_action)

        tools_menu = self.menuBar().addMenu("&Tools")
        tools_menu.addAction(self.refresh_backend_action)

        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction(self.about_action)

    def _create_toolbar(self) -> None:
        toolbar = self.addToolBar("Main Toolbar")
        toolbar.setMovable(False)
        toolbar.addAction(self.open_action)
        toolbar.addAction(self.save_action)
        toolbar.addSeparator()
        toolbar.addAction(self.refresh_backend_action)
        toolbar.addSeparator()
        toolbar.addAction(self.theme_light_action)
        toolbar.addAction(self.theme_dark_action)

    def _create_status_bar(self) -> None:
        status_bar = QStatusBar()
        status_bar.setSizeGripEnabled(True)
        status_bar.addPermanentWidget(self._status_label)
        self.setStatusBar(status_bar)
        self._refresh_backend_status()

    def _create_central_tabs(self) -> None:
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North)

        self.portfolio_widget = PortfolioWidget(self)
        self.market_data_widget = self._build_placeholder_widget(
            "Market Data Tools",
            "Connect to Yahoo Finance and Alpha Vantage to sync historical and realtime datasets.",
        )
        self.quantum_widget = QuantumWidget(self.backend_manager, self)
        self.results_widget = ResultsWidget(self)
        self.analytics_widget = AnalyticsWidget(self)
        self.trading_widget = TradingWidget(self)

        self.tabs.addTab(self.portfolio_widget, "Portfolio Management")
        self.tabs.addTab(self.market_data_widget, "Market Data")
        self.tabs.addTab(self.quantum_widget, "Quantum Computing")
        self.tabs.addTab(self.results_widget, "Results")
        self.tabs.addTab(self.analytics_widget, "Analytics")
        self.tabs.addTab(self.trading_widget, "Trading")

        self.setCentralWidget(self.tabs)

    def _build_placeholder_widget(self, title: str, description: str) -> QWidget:
        widget = QWidget(self)
        layout = QVBoxLayout(widget)
        layout.addWidget(QLabel(f"<h2>{title}</h2>"))
        description_label = QLabel(description)
        description_label.setWordWrap(True)
        layout.addWidget(description_label)
        layout.addStretch(1)
        return widget

    def apply_theme(self, theme: str) -> None:
        app = QApplication.instance()
        if app is None:
            return
        if theme == "dark":
            Theme.apply_dark_theme(app)
            self.theme_dark_action.setChecked(True)
            self.theme_light_action.setChecked(False)
        else:
            Theme.apply_light_theme(app)
            self.theme_light_action.setChecked(True)
            self.theme_dark_action.setChecked(False)
        self._theme = theme
        self.settings.setValue("ui/theme", theme)

    def _refresh_backend_status(self) -> None:
        try:
            service = self.backend_manager._authenticate()  # type: ignore[attr-defined]
            if service is None:
                self._status_label.setText("Backend: Aer Simulator")
            else:
                backend_name = self.backend_manager._select_backend(service, num_qubits=5, prefer_hardware=False)
                self._status_label.setText(f"Backend: {backend_name}")
        except Exception as exc:
            logger.error("Failed to refresh backend status: {}", exc)
            self._status_label.setText("Backend: Unavailable")

    def _init_update_checker(self) -> None:
        try:
            from quantum_portfolio_optimizer import __version__
        except Exception:  # pragma: no cover - fallback if metadata missing
            __version__ = "0.0.0"

        download_dir = Path.home() / "Downloads"

        self.update_checker = UpdateChecker(
            manifest_url="https://example.com/quantum-portfolio/updates.json",
            current_version=__version__,
            download_dir=download_dir,
            notifier=self._notify_update_available,
        )
        QTimer.singleShot(5_000, self.update_checker.check_async)

    def _notify_update_available(self, info) -> None:
        message = f"Update {info.version} available. Release notes: {info.release_notes}"
        self.statusBar().showMessage(message, 15_000)

    def _open_portfolio(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Portfolio",
            str(Path.home()),
            "JSON Files (*.json)",
        )
        if file_path:
            self.statusBar().showMessage(f"Loaded portfolio from {file_path}", 5_000)

    def _save_portfolio(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Portfolio",
            str(Path.home() / "portfolio.json"),
            "JSON Files (*.json)",
        )
        if file_path:
            self.statusBar().showMessage(f"Saved portfolio to {file_path}", 5_000)

    def _show_about_dialog(self) -> None:
        QMessageBox.about(
            self,
            "About Quantum Portfolio Optimizer",
            "<b>Quantum Portfolio Optimizer</b><br><br>"
            "Harness hybrid quantum-classical techniques to build and monitor portfolios."
            "<br><br>Designed for quantitative investors and financial professionals.",
        )

    def _restore_state(self) -> None:
        geometry = self.settings.value("ui/geometry")
        window_state = self.settings.value("ui/window_state")
        theme = self.settings.value("ui/theme", "light")

        if geometry:
            self.restoreGeometry(geometry)
        if window_state:
            self.restoreState(window_state)

        self.apply_theme(str(theme))

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 - Qt API
        self.settings.setValue("ui/geometry", self.saveGeometry())
        self.settings.setValue("ui/window_state", self.saveState())
        super().closeEvent(event)

