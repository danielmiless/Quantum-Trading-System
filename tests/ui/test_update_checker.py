"""Tests for the update checker utility."""

from __future__ import annotations

from pathlib import Path

import pytest

from ui.utils.update_checker import UpdateChecker


def test_update_checker_parses_manifest_for_platform(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checker = UpdateChecker(
        manifest_url="https://example.com/manifest.json",
        current_version="0.1.0",
        download_dir=tmp_path,
        notifier=None,
    )
    manifest = {
        "version": "0.2.0",
        "checksum": "abc123",
        "download_urls": {
            "linux": "https://example.com/linux.zip",
            "macos": "https://example.com/macos.zip",
            "windows": "https://example.com/windows.zip",
        },
        "release_notes": "https://example.com/notes",
    }
    info = checker._parse_manifest(manifest)
    assert info is not None
    assert info.version == "0.2.0"
    assert checker._is_newer("0.2.0")
    assert not checker._is_newer("0.0.1")


def test_download_update_verifies_checksum(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    checker = UpdateChecker(
        manifest_url="",
        current_version="0.1.0",
        download_dir=tmp_path,
    )
    file_path = tmp_path / "dummy.bin"
    file_path.write_bytes(b"hello world")
    checksum = "b94d27b9934d3e08a52e52d7da7dabfac484efe37a5380ee9088f7ace2efcde9"
    assert checker._verify_checksum(file_path, checksum)

