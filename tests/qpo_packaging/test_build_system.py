"""Tests for packaging build utilities."""

from __future__ import annotations

from pathlib import Path

from qpo_packaging.build import _ensure_icon  # type: ignore[attr-defined]
from qpo_packaging.build_config import BuildConfig


def test_build_config_uses_fallback_icons(tmp_path: Path) -> None:
    (tmp_path / "qpo_packaging" / "icons" / "dist").mkdir(parents=True)
    config = BuildConfig.default(tmp_path)
    mac_icon = config.platforms["macos"].icon_path
    win_icon = config.platforms["windows"].icon_path
    assert "fallback" in str(mac_icon)
    assert "fallback" in str(win_icon)


def test_ensure_icon_creates_placeholder(tmp_path: Path) -> None:
    icon_path = tmp_path / "placeholder.ico"
    _ensure_icon(icon_path)
    assert icon_path.exists()

