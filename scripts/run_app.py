"""Helper script to bootstrap the Qt desktop application."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from loguru import logger


def ensure_conda_active() -> None:
    conda_env = os.getenv("CONDA_DEFAULT_ENV")
    if not conda_env:
        logger.warning("No active Conda environment detected; ensure dependencies are installed")
    else:
        logger.info("Running within Conda environment: {}", conda_env)


def run_validation() -> None:
    validation_script = Path(__file__).resolve().parents[1] / "scripts" / "validate_setup.py"
    if not validation_script.exists():
        logger.error("Validation script not found at {}", validation_script)
        return

    result = subprocess.run([sys.executable, str(validation_script)], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error("Environment validation failed:\n{}\n{}", result.stdout, result.stderr)
        raise SystemExit(1)
    logger.info("Environment validation passed")


def launch_app(args: list[str] | None = None) -> None:
    ui_entry = Path(__file__).resolve().parents[1] / "src" / "ui" / "main.py"
    if not ui_entry.exists():
        logger.error("UI entry point not found at {}", ui_entry)
        raise SystemExit(1)

    cmd = [sys.executable, str(ui_entry)]
    if args:
        cmd.extend(args)

    logger.info("Starting Qt application: {}", " ".join(cmd))
    raise SystemExit(subprocess.call(cmd))


def main() -> None:
    ensure_conda_active()
    run_validation()
    launch_app(sys.argv[1:])


if __name__ == "__main__":
    main()

