# Quantum Portfolio Optimizer

Quantum Portfolio Optimizer is a desktop application that explores quantum-enhanced techniques for portfolio construction and risk management. It combines classical analytics, live trading simulators, and a Qiskit-based quantum engine (Terra 0.46 + Algorithms 0.3) to prototype next-generation investment tooling. The PySide6 desktop client provides an interactive workspace for configuring datasets, launching optimizations, reviewing analytics, and packaging releases.

## Features

- Hybrid quantum-classical optimization workflows for portfolio allocation (QAOA-powered)
- Seamless fallbacks between IBM Quantum Runtime, Aer simulators, and reference samplers
- Market data ingestion from Yahoo Finance and Alpha Vantage with configurable constraints
- Advanced analytics: backtesting, risk, attribution, Monte-Carlo, benchmarking, and reporting
- Paper-trading pipeline with Alpaca integration, smart execution, risk monitoring, and notifications
- Desktop packaging (PyInstaller) with cross-platform release scripts, icon generation, and updater support
- Developer tooling for automated formatting, linting, type checking, coverage, and environment validation

## Prerequisites (macOS)

- macOS 12.0 (Monterey) or newer
- Homebrew package manager (recommended)
- Python 3.11 or newer (`brew install python@3.11`)
- Xcode Command Line Tools (`xcode-select --install`)
- Optional: Conda or virtualenv for environment isolation

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

   | Variable | Description |
   | --- | --- |
   | `IBM_QUANTUM_TOKEN` | IBM Cloud API token for authenticated runtime access |
   | `ALPHA_VANTAGE_API_KEY` | Alpha Vantage REST key for market data |
   | `YAHOO_FINANCE_ENABLED` | Toggle Yahoo data collection (`true/false`) |
   | `LOG_LEVEL` | Runtime log level (e.g. `INFO`, `DEBUG`) |
   | `QPO_ENABLE_AER` | Set to `true` to force Aer simulator fallback in production |
   | `QPO_SYNC_QUANTUM` | Set to `true` for synchronous quantum execution (CI/testing) |

## Development Setup

1. **Install editable assets**
   ```bash
   pip install -e '.[dev]'
   ```
2. **Automated quality gates**
   ```bash
   make format     # black + isort
   make lint       # flake8 + mypy
   make test       # pytest + coverage (QPO_SYNC_QUANTUM=1 applied automatically)
   ```
3. **Environment validation**
   ```bash
   python scripts/validate_setup.py
   ```
   The script confirms Python ≥ 3.11, verifies the pinned Qiskit 0.46 toolchain (Terra/Aer/Algorithms/Runtime), and smoke-tests circuit execution using AerSimulator.
4. **Running targeted suites**
   ```bash
   python -m pytest tests/analytics/test_backtesting.py
   python -m pytest tests/ui/test_widgets.py -k portfolio
   ```
   When executing GUI tests locally you can keep the headless Qt backend by exporting `QT_QPA_PLATFORM=offscreen`.

## Packaging & Releases

- Generate application icons
  ```bash
  python qpo_packaging/icons/generate_icons.py
  ```
- Build platform-specific bundles (PyInstaller + DMG/NSIS automation)
  ```bash
  python scripts/build_release.py --platforms macos windows
  ```
- Review pipeline details, code-signing placeholders, and update manifests in `docs/packaging.md`.
- The update checker in the desktop client reads `QPO_UPDATE_URL`; leave it unset during development to skip network calls.

## Usage

1. Ensure the `.env` file contains the required credentials and toggles.
2. Start the desktop client:
   ```bash
   python -m quantum_portfolio_optimizer.app
   ```
3. Configure data feeds, optimization parameters, and analytics from the tabbed interface (Portfolio, Market Data, Quantum Computing, Results, Analytics, Trading).
4. Use the quantum tab to select a backend, adjust QAOA parameters, and launch optimizations. Progress and results are streamed via the signal bus and logged with structured payloads.
5. Export reports, benchmark comparisons, or trading dashboards as needed.

## Project Structure

```
├── quantum_portfolio_optimizer/
│   ├── __init__.py
│   └── app.py                        # PySide6 application bootstrap
├── src/
│   ├── analytics/                    # Backtester, risk, performance, benchmark, Monte Carlo, reporting
│   ├── notifications/                # Notification dispatcher
│   ├── quantum_engine/               # Backend manager, QAOA optimizer, QUBO generation
│   ├── trading/                      # Alpaca client, live portfolio manager, execution engine, scheduler
│   ├── ui/                           # PySide6 widgets, controllers, workers, dialogs, styles, utils
│   └── utils/                        # Shared logging utilities
├── qpo_packaging/                    # Build configuration, icon generator, installer templates
├── scripts/
│   ├── run_app.py
│   ├── validate_setup.py
│   └── build_release.py
├── tests/
│   ├── analytics/
│   ├── integration/
│   ├── trading/
│   ├── ui/
│   ├── unit/
│   └── qpo_packaging/
├── docs/
│   └── packaging.md                  # Packaging and release walkthrough
├── Makefile                          # install/test/format/lint/clean helpers
├── requirements.txt
├── pyproject.toml                    # metadata, dependencies, tooling, mypy/pytest configs
└── .env.template
```

## Contributing

1. Fork the repository and create a feature branch.
2. Install editable dependencies and run the full toolchain (`make format lint test`).
3. Keep commit messages descriptive; attach screenshots or logs for UI changes when possible.
4. Reference related issues or tickets and document any new environment variables when submitting PRs.

## License

This project is released under the MIT License.


