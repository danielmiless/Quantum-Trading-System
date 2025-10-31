"""Placeholder tests for the project scaffold."""

from __future__ import annotations

from quantum_portfolio_optimizer import __version__


def test_version_format() -> None:
    """Ensure the project exposes a semantic version string."""

    assert isinstance(__version__, str)
    assert __version__


