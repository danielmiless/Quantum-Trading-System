"""Custom QValidators and validation helpers for UI inputs."""

from __future__ import annotations

import re
from typing import Iterable

from PySide6.QtGui import QDoubleValidator, QValidator


class StockSymbolValidator(QValidator):
    """Validate stock symbols consisting of letters, numbers, and separators."""

    pattern = re.compile(r"^[A-Z]{1,5}(\.[A-Z]{1,2})?$")

    def validate(self, input_str: str, pos: int):  # type: ignore[override]
        if not input_str:
            return QValidator.State.Intermediate, input_str, pos
        if self.pattern.match(input_str.upper()):
            return QValidator.State.Acceptable, input_str.upper(), pos
        return QValidator.State.Invalid, input_str, pos


class PercentageValidator(QDoubleValidator):
    """Validator ensuring values remain within 0-100 percent."""

    def __init__(self) -> None:
        super().__init__(0.0, 100.0, 2)
        self.setNotation(QDoubleValidator.Notation.StandardNotation)

    def validate(self, input_str: str, pos: int):  # type: ignore[override]
        if not input_str:
            return QValidator.State.Intermediate, input_str, pos
        try:
            value = float(input_str)
        except ValueError:
            return QValidator.State.Invalid, input_str, pos

        if 0.0 <= value <= 100.0:
            return QValidator.State.Acceptable, f"{value:.2f}", pos
        return QValidator.State.Invalid, input_str, pos


class NumericRangeValidator(QDoubleValidator):
    """Validator enforcing numeric ranges with configurable precision."""

    def __init__(self, minimum: float, maximum: float, decimals: int = 2) -> None:
        super().__init__(minimum, maximum, decimals)
        self.setNotation(QDoubleValidator.Notation.StandardNotation)


class PortfolioConstraintValidator(QValidator):
    """Validate that allocation values satisfy portfolio constraints."""

    def __init__(self, expected_sum: float = 100.0, tolerance: float = 1e-2) -> None:
        super().__init__()
        self.expected_sum = expected_sum
        self.tolerance = tolerance

    def validate(self, input_str: str, pos: int):  # type: ignore[override]
        try:
            allocations = [float(value.strip()) for value in input_str.split(",") if value.strip()]
        except ValueError:
            return QValidator.State.Invalid, input_str, pos

        if not allocations:
            return QValidator.State.Intermediate, input_str, pos

        total = sum(allocations)
        if abs(total - self.expected_sum) <= self.tolerance:
            return QValidator.State.Acceptable, input_str, pos
        if total < self.expected_sum:
            return QValidator.State.Intermediate, input_str, pos
        return QValidator.State.Invalid, input_str, pos


__all__ = [
    "StockSymbolValidator",
    "PercentageValidator",
    "NumericRangeValidator",
    "PortfolioConstraintValidator",
]

