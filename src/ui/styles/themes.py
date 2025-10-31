"""Theme management for the Quantum Portfolio Optimizer UI."""

from __future__ import annotations

from PySide6.QtGui import QFont, QPalette, QColor
from PySide6.QtWidgets import QApplication


class Theme:
    """Apply consistent styling across the application."""

    BASE_FONT = QFont("Helvetica Neue", 10)

    @classmethod
    def apply_dark_theme(cls, app: QApplication) -> None:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 35))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Base, QColor(40, 40, 45))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(50, 50, 60))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(250, 250, 250))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(10, 10, 10))
        palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
        palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 55))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(235, 235, 235))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(64, 128, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Link, QColor(100, 180, 255))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 85, 85))

        app.setPalette(palette)
        cls._apply_common_styles(app)

    @classmethod
    def apply_light_theme(cls, app: QApplication) -> None:
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(246, 248, 252))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(240, 243, 247))
        palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        palette.setColor(QPalette.ColorRole.Text, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.Button, QColor(236, 239, 244))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(25, 25, 25))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(30, 116, 253))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        palette.setColor(QPalette.ColorRole.Link, QColor(34, 112, 224))
        palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 85, 85))

        app.setPalette(palette)
        cls._apply_common_styles(app)

    @classmethod
    def _apply_common_styles(cls, app: QApplication) -> None:
        app.setFont(cls.BASE_FONT)
        app.setStyleSheet(
            """
            QWidget {
                font-size: 10pt;
            }
            QToolBar {
                padding: 4px;
                spacing: 6px;
            }
            QStatusBar {
                padding: 4px 8px;
            }
            QPushButton {
                padding: 6px 12px;
                border-radius: 4px;
            }
            QTableView::item:selected {
                color: #ffffff;
                background-color: #1f6feb;
            }
            """
        )

