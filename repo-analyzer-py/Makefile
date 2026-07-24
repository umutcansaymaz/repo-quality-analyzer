.PHONY: help install dev-install lint format typecheck test test-unit test-integration test-e2e coverage clean build docker-build doctor hooks run

PYTHON ?= python3
PACKAGE := repo_analyzer
CLI := repo-analyzer

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Install the package in editable mode
	$(PYTHON) -m pip install -e .

dev-install: ## Install package plus development dependencies
	$(PYTHON) -m pip install -e ".[dev]"
	pre-commit install

lint: ## Run ruff linter
	ruff check src tests

format: ## Format code with black and ruff
	ruff format src tests
	ruff check --fix src tests
	black src tests

typecheck: ## Run mypy type checker
	mypy --config-file mypy.ini

test: ## Run the full test suite with coverage
	pytest

test-unit: ## Run only unit tests
	pytest tests/unit -m "unit"

test-integration: ## Run only integration tests
	pytest tests/integration -m "integration"

test-e2e: ## Run only end-to-end tests
	pytest tests/e2e -m "e2e"

coverage: ## Generate coverage report
	pytest --cov=$(PACKAGE) --cov-report=html
	@echo "HTML coverage report: htmlcov/index.html"

clean: ## Remove build artifacts and caches
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache htmlcov coverage.xml .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name "*.egg-info" -exec rm -rf {} +

build: ## Build source and wheel distributions
	$(PYTHON) -m build

docker-build: ## Build the docker image
	docker build -t repo-analyzer:latest .

doctor: ## Run the doctor command to verify environment
	$(CLI) doctor

hooks: ## Install pre-commit hooks
	pre-commit install

run: ## Run the CLI with --help
	$(CLI) --help
