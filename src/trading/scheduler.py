"""Automated trading scheduler aware of market hours."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from typing import Callable

import pandas_market_calendars as mcal
from loguru import logger


Job = Callable[[], None]


@dataclass(slots=True)
class Schedule:
    name: str
    callback: Job
    time_of_day: time


class TradingScheduler:
    """Schedule trading jobs during market hours."""

    def __init__(self, exchange: str = "NYSE") -> None:
        self.calendar = mcal.get_calendar(exchange)
        self.jobs: list[Schedule] = []

    def add_job(self, schedule: Schedule) -> None:
        self.jobs.append(schedule)
        logger.info("Scheduled job {} at {}", schedule.name, schedule.time_of_day)

    def run_pending(self, now: datetime) -> None:
        if not self._is_market_open(now):
            return
        current_time = now.time().replace(second=0, microsecond=0)
        for job in self.jobs:
            if job.time_of_day == current_time:
                try:
                    logger.debug("Executing scheduled job {}", job.name)
                    job.callback()
                except Exception as exc:  # noqa: BLE001
                    logger.error("Scheduled job {} failed: {}", job.name, exc)

    def _is_market_open(self, now: datetime) -> bool:
        schedule = self.calendar.schedule(start_date=now.date(), end_date=now.date())
        if schedule.empty:
            return False
        market_open = schedule.iloc[0]["market_open"].to_pydatetime()
        market_close = schedule.iloc[0]["market_close"].to_pydatetime()
        return market_open <= now <= market_close


__all__ = ["TradingScheduler", "Schedule"]

