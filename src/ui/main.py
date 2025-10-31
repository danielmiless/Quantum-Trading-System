"""Application entry point for the Qt desktop client."""

from __future__ import annotations

import argparse
import sys
import traceback

from loguru import logger
from PySide6.QtWidgets import QApplication, QMessageBox

from quantum_engine.backend_manager import BackendManager
from utils.logger import setup_logging

from .main_window import MainWindow
from .styles import Theme


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Quantum Portfolio Optimizer UI")
    parser.add_argument(
        "--theme",
        choices=["light", "dark"],
        default="light",
        help="Initial theme to apply",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Console log level",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])

    setup_logging(console_level=args.log_level)
    logger.info("Launching Quantum Portfolio Optimizer UI")

    app = QApplication(sys.argv)

    if args.theme == "dark":
        Theme.apply_dark_theme(app)
    else:
        Theme.apply_light_theme(app)

    backend_manager = BackendManager()
    window = MainWindow(backend_manager)
    window.apply_theme(args.theme)
    window.show()

    try:
        return app.exec()
    except Exception as exc:  # pragma: no cover - runtime safety net
        logger.exception("Unhandled exception in UI: {}", exc)
        QMessageBox.critical(
            window,
            "Application Error",
            f"An unexpected error occurred:\n{exc}\n\n" f"{traceback.format_exc()}",
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

