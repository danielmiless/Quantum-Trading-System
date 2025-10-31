"""Controller for managing portfolio state and market data operations."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, List

import numpy as np
from loguru import logger

try:
    import yfinance as yf
except ImportError:  # pragma: no cover - safety
    yf = None

from PySide6.QtCore import QObject

from ..utils.signal_manager import SignalManager


@dataclass(slots=True)
class PortfolioAsset:
    symbol: str
    allocation: float
    expected_return: float


class PortfolioController(QObject):
    """Manage portfolio lifecycle, validation, and persistence."""

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self._signal_manager = SignalManager.instance()

    def create_portfolio(
        self,
        assets: Iterable[PortfolioAsset],
        *,
        risk_aversion: float,
        max_assets: int,
    ) -> dict[str, Any]:
        asset_list = list(assets)
        if not asset_list:
            raise ValueError("Portfolio must contain at least one asset")
        if not 0 <= risk_aversion <= 1:
            raise ValueError("Risk aversion must be within [0, 1]")
        if len(asset_list) > max_assets:
            raise ValueError("Portfolio exceeds maximum asset constraint")

        total_allocation = sum(asset.allocation for asset in asset_list)
        if not np.isclose(total_allocation, 100.0, atol=1e-2):
            raise ValueError("Total allocation must sum to 100%")

        payload = {
            "assets": [asdict(asset) for asset in asset_list],
            "risk_aversion": risk_aversion,
            "max_assets": max_assets,
        }
        self._signal_manager.portfolio_updated.emit(payload)
        return payload

    def fetch_market_data(self, symbols: List[str]) -> dict[str, Any]:
        if yf is None:
            raise RuntimeError("yfinance is not installed")
        if not symbols:
            raise ValueError("No symbols provided for market data fetch")

        self._signal_manager.notification.emit("info", "Fetching market data…")
        try:
            data = yf.download(symbols, period="1mo", interval="1d", progress=False)
            self._signal_manager.notification.emit("success", "Market data refreshed")
            return {"symbols": symbols, "data": data.tail(5).to_dict()}
        except Exception as exc:
            logger.error("Market data fetch failed: {}", exc)
            self._signal_manager.portfolio_error.emit(str(exc))
            raise

    def save_portfolio(self, file_path: Path, payload: dict[str, Any]) -> None:
        try:
            file_path.write_text(json.dumps(payload, indent=2))
            self._signal_manager.notification.emit(
                "success", f"Portfolio saved to {file_path}"
            )
        except OSError as exc:
            logger.error("Failed to save portfolio: {}", exc)
            self._signal_manager.portfolio_error.emit(str(exc))
            raise

    def load_portfolio(self, file_path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(file_path.read_text())
            self._signal_manager.portfolio_updated.emit(payload)
            return payload
        except (OSError, json.JSONDecodeError) as exc:
            logger.error("Failed to load portfolio: {}", exc)
            self._signal_manager.portfolio_error.emit(str(exc))
            raise


__all__ = ["PortfolioController", "PortfolioAsset"]

