"""Quantum Portfolio Optimizer package."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("quantum-portfolio-optimizer")
except PackageNotFoundError:  # pragma: no cover - package metadata absent in dev
    __version__ = "0.0.0"

__all__ = ["__version__"]


