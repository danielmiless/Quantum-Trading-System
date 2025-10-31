"""Application update checker."""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import requests
from loguru import logger


@dataclass(slots=True)
class UpdateInfo:
    version: str
    download_url: str
    checksum: str
    release_notes: str


class UpdateChecker:
    """Check remote manifest for updates and optionally download them."""

    def __init__(
        self,
        manifest_url: str,
        current_version: str,
        download_dir: Path,
        notifier: Optional[Callable[[UpdateInfo], None]] = None,
    ) -> None:
        self.manifest_url = manifest_url
        self.current_version = current_version
        self.download_dir = download_dir
        self.notifier = notifier

    def check_async(self) -> None:
        thread = threading.Thread(target=self._run, name="UpdateChecker", daemon=True)
        thread.start()

    def _run(self) -> None:
        try:
            response = requests.get(self.manifest_url, timeout=10)
            response.raise_for_status()
            manifest = response.json()
            info = self._parse_manifest(manifest)
            if info and self._is_newer(info.version) and self.notifier:
                self.notifier(info)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Update check failed: {}", exc)

    def download_update(self, info: UpdateInfo) -> Path:
        self.download_dir.mkdir(parents=True, exist_ok=True)
        target = self.download_dir / f"update-{info.version}.bin"
        with requests.get(info.download_url, stream=True, timeout=30) as response:
            response.raise_for_status()
            with open(target, "wb") as handle:
                for chunk in response.iter_content(chunk_size=8192):
                    handle.write(chunk)
        if not self._verify_checksum(target, info.checksum):
            target.unlink(missing_ok=True)
            raise ValueError("Downloaded file checksum mismatch")
        return target

    def _parse_manifest(self, manifest: dict) -> Optional[UpdateInfo]:
        download_urls = manifest.get("download_urls", {})
        platform_key = "macos" if sys.platform == "darwin" else "windows" if sys.platform.startswith("win") else "linux"
        download = download_urls.get(platform_key)
        if not download:
            return None
        return UpdateInfo(
            version=str(manifest.get("version", "0.0.0")),
            download_url=str(download),
            checksum=str(manifest.get("checksum", "")),
            release_notes=str(manifest.get("release_notes", "")),
        )

    def _is_newer(self, remote_version: str) -> bool:
        def parse(version: str) -> tuple[int, ...]:
            return tuple(int(part) for part in version.split("."))

        try:
            return parse(remote_version) > parse(self.current_version)
        except ValueError:
            return False

    def _verify_checksum(self, file_path: Path, checksum: str) -> bool:
        if not checksum:
            return True
        digest = hashlib.sha256()
        with open(file_path, "rb") as handle:
            for chunk in iter(lambda: handle.read(8192), b""):
                digest.update(chunk)
        return digest.hexdigest() == checksum


import sys  # noqa: E402  - imported late to avoid circular imports


