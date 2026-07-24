# repo-analyzer

> Professional GitHub repository analyzer: static analysis, security audit, architecture review and AI-enriched technical reports — all in a single CLI tool.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linter: ruff](https://img.shields.io/badge/linter-ruff-261230.svg)](https://github.com/astral-sh/ruff)
[![Type checker: mypy](https://img.shields.io/badge/type%20checker-mypy-673ab7.svg)](https://mypy-lang.org/)

---

## Overview

`repo-analyzer` analyzes any GitHub repository — public, private, SSH-accessible, or token-based — performing professional-grade static analysis, security auditing, architecture review, and producing AI-enriched technical reports.

It unifies the capabilities of **SonarQube**, **CodeClimate**, **GitHub Insights**, **Bandit**, and the kind of code review a senior software architect would do — in a single tool.

## Architecture

The project follows the architecture described in the
[Software Design Document](docs/SDD-github-repo-analyzer.md):

- **Hexagonal Architecture** (Ports & Adapters) at the core
- **Plugin Architecture** for extensible analysis engines
- **Modular Monolith** organization for a single-process CLI
- **Pipeline-based** analysis orchestration

### High-level data flow

```
GitHub URL → Clone (cached) → Language Detect → Analyzer Pipeline (parallel)
          → Aggregation → AI Review → Report (MD / JSON / HTML / PDF)
```

## Project layout

```
repo-analyzer-py/
├── src/repo_analyzer/
│   ├── cli/                # Typer CLI commands
│   ├── core/               # Hexagonal core: domain models + ports
│   │   ├── domain/         # Pydantic models (Repository, Finding, Report...)
│   │   └── ports/          # Abstract interfaces (VCS, Analyzer, LLM, Output, Cache)
│   ├── adapters/           # Port implementations (vcs, llm, output, cache)
│   ├── analyzers/          # Built-in analysis engines (plugins)
│   ├── plugins/            # Plugin manager, registry, discovery
│   ├── reports/            # Report generators (MD/JSON/HTML/PDF)
│   ├── infrastructure/     # Cross-cutting: config, logging, errors, security
│   └── utils/              # Pure utility functions
├── tests/                  # unit / integration / e2e tests
├── docs/                   # Software Design Document + ADRs
└── .github/workflows/      # CI pipelines
```

## Installation

### From source (development)

```bash
git clone <repository-url>
cd repo-analyzer-py
make dev-install
```

### With pip

```bash
pip install -e .
```

### With Docker

```bash
docker build -t repo-analyzer .
docker run --rm repo-analyzer --help
```

## Quick start

```bash
# Verify the installation and environment
repo-analyzer doctor

# Show the version banner
repo-analyzer version

# Analyze a repository (pipeline initialization only at this stage)
repo-analyzer analyze https://github.com/owner/repo

# Inspect the cache
repo-analyzer cache list

# Clear the cache
repo-analyzer cache clear

# View / edit configuration
repo-analyzer config
```

## Configuration

`repo-analyzer` merges configuration from four sources, in increasing priority:

1. Built-in defaults
2. `~/.config/repo-analyzer/config.yaml` (or `--config <path>`)
3. Environment variables prefixed with `GRA_`
4. CLI arguments

Example `config.yaml`:

```yaml
log_level: INFO
cache:
  enabled: true
  dir: ~/.cache/repo-analyzer
  ttl_days: 7
  max_size_gb: 2
reports:
  output_dir: ./reports
  formats: [markdown, json]
```

## CLI reference

| Command | Description |
|---------|-------------|
| `repo-analyzer analyze <url>` | Initialize the analysis pipeline for a repository. |
| `repo-analyzer version` | Print the version and build banner. |
| `repo-analyzer doctor` | Run environment health checks. |
| `repo-analyzer cache list` | List cached repository entries. |
| `repo-analyzer cache clear` | Remove all cache entries. |
| `repo-analyzer config` | Show the resolved configuration. |
| `repo-analyzer update` | Check for a newer release. |

## Development

```bash
make help          # list all available commands
make lint          # ruff
make format        # black + ruff format
make typecheck     # mypy --strict
make test          # pytest with coverage (>= 90% enforced)
make coverage      # generate HTML coverage report
```

Pre-commit hooks:

```bash
pre-commit install
pre-commit run --all-files
```

## Code standards

- Python 3.12+
- 100% type hints (`mypy --strict`)
- Google-style docstrings
- SOLID / DRY / KISS
- `black` + `ruff` formatted
- ≥ 90% test coverage

## License

[MIT](LICENSE)
