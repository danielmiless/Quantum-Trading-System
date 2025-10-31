"""Alpaca trading API integration for paper trading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

import pandas as pd
from alpaca_trade_api.rest import REST, APIError
from loguru import logger


@dataclass(slots=True)
class Position:
    symbol: str
    qty: float
    avg_entry_price: float
    current_price: float
    unrealized_pl: float


class AlpacaClient:
    """Wrapper around Alpaca REST API for paper trading."""

    def __init__(self) -> None:
        self.api: Optional[REST] = None

    def authenticate(self, api_key: str, secret_key: str, paper: bool = True) -> None:
        base_url = "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
        self.api = REST(api_key, secret_key, base_url)
        logger.info("Authenticated with Alpaca {} environment", "paper" if paper else "live")

    def _ensure_client(self) -> REST:
        if self.api is None:
            raise RuntimeError("Alpaca client not authenticated")
        return self.api

    def get_account_info(self) -> Dict[str, str]:
        api = self._ensure_client()
        try:
            account = api.get_account()
            info = {
                "id": account.id,
                "status": account.status,
                "cash": account.cash,
                "portfolio_value": account.portfolio_value,
                "buying_power": account.buying_power,
            }
            logger.debug("Fetched account info: {}", info)
            return info
        except APIError as exc:
            logger.error("Failed to fetch Alpaca account info: {}", exc)
            raise

    def place_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        order_type: str = "market",
        time_in_force: str = "day",
    ) -> Dict[str, str]:
        api = self._ensure_client()
        try:
            order = api.submit_order(
                symbol=symbol,
                qty=qty,
                side=side,
                type=order_type,
                time_in_force=time_in_force,
            )
            logger.info("Placed {} order for {} shares of {}", side, qty, symbol)
            return {
                "id": order.id,
                "symbol": order.symbol,
                "qty": order.qty,
                "filled_avg_price": order.filled_avg_price,
                "status": order.status,
            }
        except APIError as exc:
            logger.error("Failed to place order: {}", exc)
            raise

    def get_positions(self) -> List[Position]:
        api = self._ensure_client()
        try:
            positions = api.list_positions()
            result = [
                Position(
                    symbol=pos.symbol,
                    qty=float(pos.qty),
                    avg_entry_price=float(pos.avg_entry_price),
                    current_price=float(pos.current_price),
                    unrealized_pl=float(pos.unrealized_pl),
                )
                for pos in positions
            ]
            logger.debug("Retrieved {} positions", len(result))
            return result
        except APIError as exc:
            logger.error("Failed to fetch positions: {}", exc)
            raise

    def get_portfolio_history(self, period: str = "1M") -> pd.DataFrame:
        api = self._ensure_client()
        try:
            history = api.get_portfolio_history(period=period)
            df = pd.DataFrame(
                {
                    "timestamp": pd.to_datetime(history.timestamp, unit="s"),
                    "equity": history.equity,
                    "profit_loss": history.profit_loss,
                }
            ).set_index("timestamp")
            logger.debug("Retrieved portfolio history with {} records", len(df))
            return df
        except RESTError as exc:
            logger.error("Failed to fetch portfolio history: {}", exc)
            raise


__all__ = ["AlpacaClient", "Position"]

