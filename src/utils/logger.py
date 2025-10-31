"""Centralized logging configuration using Loguru."""

from __future__ import annotations

import pathlib
import sys
from typing import Any

from loguru import logger


def setup_logging(
    *,
    console_level: str = "INFO",
    file_level: str = "DEBUG",
    log_directory: str = "logs",
    log_filename: str = "quantum_portfolio.log",
) -> None:
    """Configure application-wide logging sinks.

    Parameters
    ----------
    console_level:
        Minimum log level for console output.
    file_level:
        Minimum log level for file output.
    log_directory:
        Relative or absolute path where the log file should be stored.
    log_filename:
        Name of the file that captures structured log output.

    The logger is configured to emit console logs in color and write structured
    JSON logs to disk. Existing handlers are removed to avoid duplicate entries
    when reconfiguring during runtime.
    """

    logger.remove()

    log_path = pathlib.Path(log_directory).expanduser().resolve()
    log_path.mkdir(parents=True, exist_ok=True)
    file_path = log_path / log_filename

    logger.add(
        sys.stdout,
        level=console_level.upper(),
        enqueue=True,
        backtrace=True,
        diagnose=False,
        colorize=True,
    )

    logger.add(
        file_path,
        level=file_level.upper(),
        enqueue=True,
        backtrace=False,
        diagnose=False,
        rotation="10 MB",
        retention="30 days",
        compression="zip",
        serialize=True,
    )

    logger.bind(
        console_level=console_level,
        file_level=file_level,
        log_directory=str(log_path),
        log_file=str(file_path),
    ).debug("Logging configured")


def log_quantum_job(event: str, **metadata: Any) -> None:
    """Emit a structured log entry related to quantum job lifecycle.

    Parameters
    ----------
    event:
        Describes the quantum job event being logged (e.g., ``"submitted"``).
    **metadata:
        Additional keyword metadata such as ``job_id``, ``backend_name``,
        ``status``, ``queue_position``, or cost metrics.
    """

    logger.bind(event=event, **metadata).info("quantum_job_event")


def log_performance_metric(metric: str, value: float, **context: Any) -> None:
    """Log performance metrics for optimization routines.

    Parameters
    ----------
    metric:
        Name of the metric, e.g., ``"execution_time"``.
    value:
        Numeric value associated with the metric.
    **context:
        Optional context (asset count, backend type) to aid analysis.
    """

    payload = {"metric": metric, "value": value, **context}
    logger.bind(**payload).info("performance_metric")


__all__ = ["setup_logging", "log_quantum_job", "log_performance_metric"]

