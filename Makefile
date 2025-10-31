SHELL := /bin/bash
PACKAGE := quantum_portfolio_optimizer
PYTHON := python3

.PHONY: install test format lint clean

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	$(PYTHON) -m pip install -e .[dev]

test:
	$(PYTHON) -m pytest

format:
	$(PYTHON) -m black $(PACKAGE) tests scripts
	$(PYTHON) -m isort $(PACKAGE) tests scripts

lint:
	$(PYTHON) -m flake8 $(PACKAGE) scripts tests
	$(PYTHON) -m mypy $(PACKAGE) scripts

clean:
	rm -rf build dist .pytest_cache .mypy_cache .ruff_cache
	rm -rf $(PACKAGE)/__pycache__ tests/__pycache__ scripts/__pycache__
	find . -name "*.pyc" -delete


