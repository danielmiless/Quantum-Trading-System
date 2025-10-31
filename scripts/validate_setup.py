"""Validation script to verify the development environment."""

from __future__ import annotations

import importlib
import platform
import sys
from dataclasses import dataclass

from loguru import logger

REQUIRED_PYTHON = (3, 11)
REQUIRED_PACKAGES = {
    "qiskit": "0.46.0",
    "qiskit_aer": "0.13.3",
    "qiskit_ibm_runtime": "0.20.0",
    "qiskit_algorithms": "0.3.0",
    "PySide6": "6.7.2",
    "pandas": "2.0.3",
    "numpy": "1.24.4",
    "matplotlib": "3.7.1",
    "yfinance": "0.2.18",
    "dotenv": "1.0.0",
    "loguru": "0.7.0",
}


@dataclass(slots=True)
class ValidationResult:
    label: str
    success: bool
    detail: str


def check_python_version() -> ValidationResult:
    current = sys.version_info
    logger.debug("Detected Python version: {}", platform.python_version())
    if current < REQUIRED_PYTHON:
        return ValidationResult(
            label="Python Version",
            success=False,
            detail=(
                "Python 3.11 or newer is required. "
                f"Detected {platform.python_version()}"
            ),
        )
    return ValidationResult(
        label="Python Version",
        success=True,
        detail=f"Python {platform.python_version()} meets requirement",
    )


def import_package(module: str, expected_version: str) -> ValidationResult:
    try:
        imported = importlib.import_module(module)
    except ImportError as exc:
        return ValidationResult(
            label=f"Import {module}",
            success=False,
            detail=f"Failed to import {module}: {exc}",
        )

    actual_version = getattr(imported, "__version__", None)
    if actual_version is None:
        detail = f"Imported {module} but could not determine version"
        logger.warning(detail)
        return ValidationResult(label=f"Import {module}", success=True, detail=detail)

    if actual_version != expected_version:
        return ValidationResult(
            label=f"Import {module}",
            success=False,
            detail=(
                f"Version mismatch for {module}. "
                f"Expected {expected_version}, found {actual_version}"
            ),
        )

    return ValidationResult(
        label=f"Import {module}",
        success=True,
        detail=f"Imported {module} {actual_version}",
    )


def check_qiskit_circuit() -> ValidationResult:
    try:
        from qiskit import QuantumCircuit
        from qiskit_aer import AerSimulator
    except ImportError as exc:
        return ValidationResult(
            label="Qiskit Circuit",
            success=False,
            detail=f"Failed to import Qiskit components: {exc}",
        )

    try:
        circuit = QuantumCircuit(2)
        circuit.h(0)
        circuit.cx(0, 1)
        circuit.measure_all()

        simulator = AerSimulator()
        job = simulator.run(circuit, shots=512)
        result = job.result()
        counts = result.get_counts(0)
        detail = f"Circuit executed successfully with counts: {counts}"
        logger.debug(detail)
        return ValidationResult(label="Qiskit Circuit", success=True, detail=detail)
    except Exception as exc:  # noqa: BLE001 - we want to capture all issues
        return ValidationResult(
            label="Qiskit Circuit",
            success=False,
            detail=f"Quantum circuit execution failed: {exc}",
        )


def run_validation() -> int:
    logger.info("Starting environment validation...")
    results: list[ValidationResult] = []

    results.append(check_python_version())

    for module, version in REQUIRED_PACKAGES.items():
        results.append(import_package(module, version))

    results.append(check_qiskit_circuit())

    failures = [result for result in results if not result.success]

    for result in results:
        log_method = logger.success if result.success else logger.error
        log_method("{}: {}", result.label, result.detail)

    if failures:
        for failed in failures:
            logger.error("Failure -> {}: {}", failed.label, failed.detail)
        logger.error("Validation failed with {} issues", len(failures))
        return 1

    logger.success("Environment validation completed successfully")
    return 0


if __name__ == "__main__":
    raise SystemExit(run_validation())


