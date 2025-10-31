# Packaging & Distribution Guide

This document outlines the desktop packaging workflow for the Quantum Portfolio Optimizer.

## Build Overview

- Entrypoint: `scripts/build_release.py`
- Build system: PyInstaller with platform-specific post-processing
- Installers:
  - macOS DMG (requires `create-dmg` and optional codesigning identity)
  - Windows NSIS installer (requires `makensis`)
- Icons generated via `packaging/icons/generate_icons.py`

## Prerequisites

- Python 3.11 virtual environment with `pip install -r requirements.txt`
- Platform tooling:
  - macOS: Xcode command line tools, `create-dmg`, optional codesign certificates
  - Windows: NSIS (Makensis) in PATH, optional code-signing certificates

## Build Steps

```bash
python scripts/build_release.py --platforms macos windows
```

Artifacts are written to `dist/<platform>/`. Update manifests are regenerated in `packaging/update_manifest.json`.

## Auto Updates

- The application fetches `https://example.com/quantum-portfolio/updates.json` on startup.
- Update manifest fields:
  - `version`: semantic version string
  - `checksum`: SHA256 digest of downloadable package
  - `download_urls`: mapping per-platform
  - `release_notes`: URL to release notes

## Code Signing

Configure signing identities in `packaging/build_config.py` or via environment variables. The build script is structured to integrate `codesign` and `signtool` commands where required.

## Release Automation

- Update `build_config.py` with new version
- Run icon generation if branding changes
- Build platforms
- Upload installers and update manifest to CDN
- Tag release in version control


