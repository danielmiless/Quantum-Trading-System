# Quantum Portfolio Optimizer

Quantum Portfolio Optimizer is a desktop application that explores quantum-enhanced techniques for portfolio construction and risk management. It combines classical financial data pipelines with Qiskit-based quantum algorithms to prototype next-generation investment tooling. The PySide6 desktop client provides an interactive interface for configuring market data, building optimization experiments, and visualizing results.

## Features

- Hybrid quantum-classical optimization workflows for portfolio allocation
- Integration with IBM Quantum services and local Qiskit simulators
- Market data ingestion from Yahoo Finance and Alpha Vantage
- Rich logging and environment management with `python-dotenv` and `loguru`
- Developer tooling for formatting, linting, testing, and static type checking

## Prerequisites (macOS)

- macOS 12.0 (Monterey) or newer
- Homebrew package manager (recommended)
- Python 3.11 or newer (`brew install python@3.11`)
- Xcode Command Line Tools (`xcode-select --install`)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-org/quantum-portfolio-optimizer.git
   cd quantum-portfolio-optimizer
   ```
2. Create and activate a virtual environment:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Copy the environment template and configure secrets:
   ```bash
   cp .env.template .env
   # Edit .env with your credentials
   ```

## Development Setup

1. Install developer dependencies:
   ```bash
   pip install -e .[dev]
   ```
2. Run formatting and linting:
   ```bash
   make format
   make lint
   ```
3. Execute the test suite with coverage:
   ```bash
   make test
   ```
4. Launch the validation script to verify your environment:
   ```bash
   python scripts/validate_setup.py
   ```

## Packaging & Releases

- Generate application icons: `python packaging/icons/generate_icons.py`
- Build installers: `python scripts/build_release.py --platforms macos windows`
- Update packaging workflow details: see `docs/packaging.md`

## Usage

1. Ensure the `.env` file is configured with IBM Quantum and Alpha Vantage credentials.
2. Start the desktop application (placeholder command until UI implementation is complete):
   ```bash
   python -m quantum_portfolio_optimizer.app
   ```
3. Configure market data sources and quantum optimization parameters within the UI.
4. Analyze optimization outputs using built-in charts and export reports as needed.

## Project Structure (Initial)

```
quantum_portfolio_optimizer/
    __init__.py
    app.py              # Entry point for the PySide6 application
    optimization/
        __init__.py
        quantum_solver.py
scripts/
    validate_setup.py
tests/
    __init__.py
    test_placeholder.py
```

> **Note:** The modules listed above illustrate the intended layout. Implementations will come in future iterations as the application evolves.

## Contributing

1. Fork the repository and create a feature branch.
2. Ensure all checks pass before opening a pull request (`make format lint test`).
3. Provide clear descriptions and reference related issues or tickets when submitting PRs.

## License

This project is released under the MIT License.


