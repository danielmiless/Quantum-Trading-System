"""Application entrypoint for the Quantum Portfolio Optimizer UI."""

from __future__ import annotations

import os
import sys

from loguru import logger
from PySide6.QtWidgets import QApplication, QLabel, QMainWindow


class QuantumPortfolioWindow(QMainWindow):
    """Minimal placeholder window for the PySide6 application."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Quantum Portfolio Optimizer")
        self.resize(960, 640)
        label = QLabel("Quantum Portfolio Optimizer setup successful!", parent=self)
        label.setObjectName("statusLabel")
        label.setMargin(24)
        self.setCentralWidget(label)


def configure_logging() -> None:
    """Configure loguru logging for the application."""

    log_level = os.getenv("LOG_LEVEL", "INFO")
    logger.remove()
    logger.add(sys.stdout, level=log_level)
    logger.debug("Logging initialized with level {}", log_level)


def main() -> int:
    """Launch the PySide6 application."""

    configure_logging()

    app = QApplication(sys.argv)
    window = QuantumPortfolioWindow()
    window.show()

    logger.info("Quantum Portfolio Optimizer UI initialized")
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())


