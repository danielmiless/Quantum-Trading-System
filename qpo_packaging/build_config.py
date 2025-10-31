"""Packaging configuration dataclasses."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Optional


@dataclass(slots=True)
class PlatformConfig:
    """Platform-specific build settings."""

    name: str
    entry_script: Path
    icon_path: Path
    output_dir: Path
    signing_identity: Optional[str] = None
    installer_template: Optional[Path] = None


@dataclass(slots=True)
class BuildConfig:
    """Top-level configuration describing build targets."""

    app_name: str
    version: str
    description: str
    company: str
    base_dir: Path
    dist_dir: Path
    build_dir: Path
    update_manifest_url: str
    platforms: Dict[str, PlatformConfig] = field(default_factory=dict)

    @classmethod
    def default(cls, base_dir: Path) -> "BuildConfig":
        packaging_dir = base_dir / "qpo_packaging"
        icons_dir = packaging_dir / "icons" / "dist"
        dist_dir = base_dir / "dist"
        build_dir = base_dir / "build"
        fallback_icon_dir = packaging_dir / "icons"
        platforms = {
            "macos": PlatformConfig(
                name="macOS",
                entry_script=base_dir / "src" / "ui" / "main.py",
                icon_path=(icons_dir / "app.icns") if (icons_dir / "app.icns").exists() else fallback_icon_dir / "fallback.icns",
                output_dir=dist_dir / "macos",
                installer_template=packaging_dir / "templates" / "dmg.json",
            ),
            "windows": PlatformConfig(
                name="Windows",
                entry_script=base_dir / "src" / "ui" / "main.py",
                icon_path=(icons_dir / "app.ico") if (icons_dir / "app.ico").exists() else fallback_icon_dir / "fallback.ico",
                output_dir=dist_dir / "windows",
                installer_template=packaging_dir / "templates" / "nsis.nsi",
            ),
        }
        return cls(
            app_name="Quantum Portfolio Optimizer",
            version="0.1.0",
            description="Quantum-enhanced portfolio optimization desktop application",
            company="Quantum Trading Labs",
            base_dir=base_dir,
            dist_dir=dist_dir,
            build_dir=build_dir,
            update_manifest_url="https://example.com/quantum-portfolio/updates.json",
            platforms=platforms,
        )

