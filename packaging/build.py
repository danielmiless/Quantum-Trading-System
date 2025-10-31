"""Build orchestration for desktop packages."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Iterable

from loguru import logger

from .build_config import BuildConfig, PlatformConfig


PYINSTALLER_ARGS = [
    "--noconfirm",
    "--clean",
    "--hidden-import=PySide6.QtXml",
    "--hidden-import=PySide6.QtSvg",
]


def build_target(config: BuildConfig, platform_key: str) -> Path:
    platform = config.platforms[platform_key]
    logger.info("Building {} release", platform.name)

    _prepare_directories(platform.output_dir, config.build_dir)
    spec_path = _generate_spec(config, platform)

    _run_pyinstaller(spec_path)

    if sys.platform == "darwin" and platform_key == "macos":
        _build_macos_installer(config, platform)
    elif sys.platform.startswith("win") and platform_key == "windows":
        _build_windows_installer(config, platform)

    _generate_update_manifest(config)
    return platform.output_dir


def build_release(platforms: Iterable[str] | None = None) -> None:
    base_dir = Path(__file__).resolve().parents[1]
    config = BuildConfig.default(base_dir)
    targets = list(platforms or config.platforms.keys())
    for key in targets:
        if key not in config.platforms:
            raise ValueError(f"Unknown platform {key}")
        build_target(config, key)


def _prepare_directories(output_dir: Path, build_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    build_dir.mkdir(parents=True, exist_ok=True)


def _generate_spec(config: BuildConfig, platform: PlatformConfig) -> Path:
    spec_path = config.build_dir / f"{config.app_name.replace(' ', '_').lower()}_{platform.name.lower()}.spec"
    datas = [
        (str(config.base_dir / "resources"), "resources"),
        (str(config.base_dir / "packaging" / "update_manifest.json"), "."),
    ]
    spec_content = f"""
# -*- mode: python -*-
block_cipher = None

a = Analysis([
    r"{platform.entry_script}"],
    pathex=[r"{config.base_dir}"],
    binaries=[],
    datas={datas},
    hiddenimports=['PySide6.QtXml', 'PySide6.QtSvg'],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='{config.app_name.replace(' ', '_')}',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=r"{platform.icon_path}",
)
dist = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='{config.app_name.replace(' ', '_')}',
)
"""
    spec_path.write_text(spec_content, encoding="utf-8")
    return spec_path


def _run_pyinstaller(spec_path: Path) -> None:
    cmd = [sys.executable, "-m", "PyInstaller", *PYINSTALLER_ARGS, str(spec_path)]
    logger.debug("Running PyInstaller: {}", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _build_macos_installer(config: BuildConfig, platform: PlatformConfig) -> None:
    app_bundle = platform.output_dir / f"{config.app_name.replace(' ', '_')}.app"
    dmg_path = platform.output_dir / f"{config.app_name.replace(' ', '_')}-{config.version}.dmg"
    create_dmg = shutil.which("create-dmg")
    if create_dmg:
        subprocess.run(
            [
                create_dmg,
                "--overwrite",
                str(dmg_path),
                str(app_bundle),
            ],
            check=True,
        )
    else:
        logger.warning("create-dmg not found; skipping DMG creation")


def _build_windows_installer(config: BuildConfig, platform: PlatformConfig) -> None:
    nsis = shutil.which("makensis")
    script_template = platform.installer_template
    if not nsis or not script_template or not script_template.exists():
        logger.warning("NSIS not configured; skipping Windows installer build")
        return
    script = script_template.read_text(encoding="utf-8").format(
        APP_NAME=config.app_name,
        VERSION=config.version,
        SOURCE_DIR=platform.output_dir,
    )
    temp_script = platform.output_dir / "installer.nsi"
    temp_script.write_text(script, encoding="utf-8")
    subprocess.run([nsis, str(temp_script)], check=True)


def _generate_update_manifest(config: BuildConfig) -> None:
    manifest_path = config.base_dir / "packaging" / "update_manifest.json"
    manifest = {
        "app": config.app_name,
        "version": config.version,
        "checksum": "<to-be-filled-during-release>",
        "download_urls": {
            key: f"https://example.com/downloads/{config.app_name.replace(' ', '_')}-{config.version}-{key}.zip"
            for key in config.platforms
        },
        "release_notes": "https://example.com/releases/notes/{config.version}",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


