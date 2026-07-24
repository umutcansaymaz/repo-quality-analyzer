# repo-analyzer

> Professional GitHub repository analyzer: static analysis, security audit, architecture review, AI-enriched technical reports — all in a single CLI tool and REST API.

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Linter: ruff](https://img.shields.io/badge/linter-ruff-261230.svg)](https://github.com/astral-sh/ruff)
[![Type checker: mypy](https://img.shields.io/badge/type%20checker-mypy-673ab7.svg)](https://mypy-lang.org/)

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [CLI Usage](#cli-usage)
- [Examples](#examples)
- [Private Repository](#private-repository)
- [GitHub Token](#github-token)
- [Docker](#docker)
- [REST API](#rest-api)
- [Plugins](#plugins)
- [AI Provider](#ai-provider)
- [Configuration](#configuration)
- [Development](#development)
- [Contributing](#contributing)
- [FAQ](#faq)
- [Roadmap](#roadmap)

---

## Overview

`repo-analyzer` analyzes any GitHub repository — public, private, SSH-accessible, or token-based — performing:

- **Static analysis** (AST, metrics, complexity, imports, dependencies)
- **Security auditing** (Bandit, detect-secrets, 28+ custom rules, OWASP Top 10)
- **Architecture review** (SOLID, DRY, KISS, YAGNI, layer separation, coupling/cohesion)
- **AI-enriched commentary** (LLM-generated engineering review with 6 provider backends)

It unifies the capabilities of **SonarQube**, **CodeClimate**, **GitHub Insights**, **Bandit**, and the kind of code review a senior software architect would do — in a single tool.

## Architecture

The project follows a **Hexagonal (Ports & Adapters)** architecture with a **Plugin** extension model and **Modular Monolith** organization. See the full [Software Design Document](docs/SDD-github-repo-analyzer.md).

```
GitHub URL → Clone (cached) → Language Detect → Analyzer Pipeline (parallel)
          → Review Engines → AI Synthesis → Report (MD / JSON / HTML / PDF)
```

### Key components

| Layer | Responsibility |
|-------|---------------|
| `cli/` | Typer CLI commands, Rich terminal UI |
| `core/` | Hexagonal core: domain models, ports, orchestrator |
| `adapters/` | VCS (git), LLM (6 providers), output (MD/JSON/HTML/PDF), cache (SQLite) |
| `analyzers/` | 12 built-in analysis engines (filesystem, AST, metrics, complexity, ...) |
| `review/` | 10+ review engines (security, quality, architecture, risk, debt, refactor, AI) |
| `reports/` | Report renderers + visualization engine (matplotlib) |
| `api/` | FastAPI REST API |
| `infrastructure/` | Config, logging, errors, DI container, progress |

## Installation

### From PyPI

```bash
pip install github-repo-analyzer
```

### From source

```bash
git clone <repository-url>
cd repo-analyzer-py
pip install -e ".[dev]"
```

### With Docker

```bash
docker build -t repo-analyzer .
docker run --rm repo-analyzer --help
```

## CLI Usage

```bash
# Verify the environment
repo-analyzer doctor

# Show version
repo-analyzer version

# Analyze a repository (prints summary + AI review)
repo-analyzer analyze https://github.com/octocat/Hello-World

# Save the JSON analysis result
repo-analyzer analyze https://github.com/octocat/Hello-World --output result.json

# Generate reports (MD, JSON, HTML, PDF)
repo-analyzer analyze https://github.com/octocat/Hello-World --report md --report json --report html --report pdf

# Specify output directory for reports
repo-analyzer analyze https://github.com/octocat/Hello-World --report md --reports-dir ./my-reports

# Bypass the clone cache
repo-analyzer analyze https://github.com/octocat/Hello-World --no-cache

# Cache management
repo-analyzer cache list
repo-analyzer cache clear

# Show resolved configuration
repo-analyzer config
```

## Examples

### Example output (terminal)

```
Repository Health
╭──────────────────────────╮
│ A  92 / 100              │
╰──────────────────────────╯

Critical Issues
┌──────────┬───────┐
│ Level    │ Count │
├──────────┼───────┤
│ Critical │ 2     │
│ High     │ 7     │
│ Medium   │ 14    │
│ Low      │ 32    │
└──────────┴───────┘
```

### Example report sections

The Markdown report includes 17 sections: Executive Summary, Repository Overview, Statistics, File System Analysis, Language Analysis, Complexity Analysis, Dependency Analysis, Git Analysis, Security Findings, Architecture Review, Technical Debt, Risk Assessment, AI Review, Quick Wins, Refactor Roadmap, Overall Health, and Appendix.

## Private Repository

Private repositories are supported via HTTPS with a token or SSH keys.

```bash
# Using a GitHub token (via environment variable)
export GRA_GITHUB_TOKEN=ghp_your_token_here
repo-analyzer analyze https://github.com/your-org/private-repo

# Using SSH
repo-analyzer analyze git@github.com:your-org/private-repo.git
```

## GitHub Token

Set your GitHub Personal Access Token via:

1. **Environment variable** (recommended for CI/CD):
   ```bash
   export GRA_GITHUB_TOKEN=ghp_xxx
   ```

2. **Config file** (`~/.config/repo-analyzer/config.yaml`):
   ```yaml
   # Token is read from env; never hardcode it here.
   ```

3. **SSH agent**: Ensure `ssh-agent` is running with your key loaded.

> **Security:** Tokens are never logged. The logging system includes a redaction filter that masks any `token`, `password`, `secret`, or `api_key` fields.

## Docker

```bash
# Build
docker build -t repo-analyzer .

# Run analysis
docker run --rm -v $(pwd)/reports:/reports repo-analyzer \
    analyze https://github.com/octocat/Hello-World --report md --reports-dir /reports

# Using docker-compose
docker-compose run repo-analyzer analyze https://github.com/octocat/Hello-World
```

The Dockerfile uses a **multi-stage build** to keep the final image small (~150 MB).

## REST API

`repo-analyzer` ships with a FastAPI REST API:

```bash
# Start the API server
python -m repo_analyzer.api --port 8000

# Or via uvicorn
uvicorn repo_analyzer.api.app:app --port 8000
```

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/status` | Service status + available providers |
| `POST` | `/analyze` | Start an analysis (returns job_id + result) |
| `GET` | `/result/{job_id}` | Fetch a stored result as JSON |
| `POST` | `/report` | Render a result into md/json/html/pdf |

### Example

```bash
# Analyze
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{"repository_url": "https://github.com/octocat/Hello-World"}'

# Get result
curl http://localhost:8000/result/{job_id}

# Generate PDF report
curl -X POST http://localhost:8000/report \
  -H "Content-Type: application/json" \
  -d '{"job_id": "{job_id}", "format": "pdf"}' --output report.pdf
```

## Plugins

`repo-analyzer` has a fully functional plugin system. All 12 built-in analyzers are registered through the same `PluginManager` that third-party plugins use — there is no separate "built-in" code path.

### How it works

1. On startup, the `Orchestrator` creates a `PluginManager`.
2. Built-in analyzers (filesystem, AST, metrics, etc.) are registered via `_register_builtin_analyzers()`.
3. Third-party plugins are discovered via Python entry points (`repo_analyzer.plugins` group) or directory scanning.
4. All analyzers run through the same phase-based pipeline.

### Creating a plugin

```python
# my_plugin/analyzer.py
from repo_analyzer.core.ports.analyzer_port import AnalyzerPort

class MyAnalyzer(AnalyzerPort):
    @property
    def name(self) -> str:
        return "my-analyzer"

    @property
    def version(self) -> str:
        return "1.0.0"

    def metadata(self) -> dict:
        return {"name": self.name, "version": self.version, "phase": 2}

    def initialize(self, config: dict) -> None:
        pass

    def can_run(self, repository, workspace) -> bool:
        return True

    def run(self, repository, workspace) -> dict:
        return {"custom_findings": []}

    def dispose(self) -> None:
        pass
```

Register via `pyproject.toml` entry points:

```toml
[project.entry-points."repo_analyzer.plugins"]
my-analyzer = "my_plugin.analyzer:MyAnalyzer"
```

## AI Provider

The AI comment engine supports 6 LLM providers via a pluggable abstraction:

| Provider | Name | SDK |
|----------|------|-----|
| Mock (offline) | `mock` | — |
| OpenAI | `openai` | `openai` |
| Anthropic | `anthropic` | `anthropic` |
| Google Gemini | `gemini` | `google-generativeai` |
| OpenRouter | `openrouter` | `openai` |
| Ollama (local) | `ollama` | — (HTTP) |

**Current behavior:** The CLI and API use the `mock` provider by default (offline, deterministic). This produces a canned engineering review so the full pipeline can run without network access.

To use a real provider programmatically:

```python
from repo_analyzer.adapters.llm import LLMProviderFactory
from repo_analyzer.core.orchestrator import Orchestrator

llm = LLMProviderFactory.create("openai", "gpt-4", api_key="sk-...")
orchestrator = Orchestrator(cache, llm=llm)
```

> **Note:** CLI flag `--llm-provider` for switching providers from the command line is planned but not yet implemented.

## Configuration

Configuration is merged from four sources (lowest → highest priority):

1. **Built-in defaults**
2. **YAML file** (`~/.config/repo-analyzer/config.yaml` or `--config <path>`)
3. **Environment variables** (prefixed with `GRA_`)
4. **CLI arguments**

```yaml
# config.yaml
log_level: INFO
cache:
  enabled: true
  dir: ~/.cache/repo-analyzer
  ttl_days: 7
reports:
  output_dir: ./reports
  formats: [markdown, json]
ai:
  enabled: false
  provider: mock
```

Environment variables:

```bash
GRA_LOG_LEVEL=DEBUG
GRA_CACHE_DIR=/tmp/cache
GRA_VCS_CLONE_DEPTH=1
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src tests

# Format
ruff format src tests
black src tests

# Type check
mypy --config-file mypy.ini

# Pre-commit hooks
pre-commit install
pre-commit run --all-files
```

## Contributing

1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/amazing-feature`).
3. Commit your changes (`git commit -m 'Add amazing feature'`).
4. Push to the branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request.

### Guidelines

- Follow the existing architecture (Hexagonal + Plugin).
- 100% type hints required (`mypy --strict`).
- Add tests for new features (≥ 80% coverage).
- Use Google-style docstrings.
- Run `ruff check`, `black`, and `mypy` before committing.

## FAQ

**Q: Can I analyze private repositories?**
A: Yes. Set the `GRA_GITHUB_TOKEN` environment variable or use SSH access.

**Q: Does it work offline?**
A: The AI review uses a `MockLLMProvider` by default (offline). All other analysis engines work offline once the repository is cloned.

**Q: How big a repository can it handle?**
A: It has been tested on repositories up to ~1M LOC. Shallow clone + partial clone + streaming file I/O keep memory usage reasonable.

**Q: Can I add my own analyzer?**
A: Yes, via the plugin system. See [Plugins](#plugins).

**Q: What languages are supported?**
A: 17 languages for detection (Python, JavaScript, TypeScript, Go, Rust, Java, Kotlin, Swift, C, C++, C#, PHP, Ruby, Shell, YAML, JSON, Markdown). AST parsing supports Python, JS/TS, Go, Rust, Java, Kotlin, C, C++, C#.

## Roadmap

### Implemented

- [x] Core analysis engines (filesystem, AST, metrics, complexity, imports, dependencies, git, documentation, tests, graphs)
- [x] Security review (Bandit, detect-secrets, 17 custom rules, OWASP Top 10)
- [x] Code quality review (20+ smells)
- [x] Architecture review (SOLID, DRY, KISS, YAGNI, coupling/cohesion)
- [x] Health score (10 sub-scores, A+ to F grade)
- [x] Risk engine + technical debt analysis + refactor plan
- [x] AI comment engine (6 LLM providers, mock by default)
- [x] Report generation (Markdown, JSON, HTML, PDF)
- [x] REST API (FastAPI, with auth, rate limit, SSRF protection)
- [x] Plugin system (built-in analyzers registered via PluginManager)
- [x] Secure token handling (GIT_ASKPASS, no credential in .git/config)
- [x] CLI with signal handling, correct exit codes, report generation

### Planned

- [ ] CLI `--llm-provider` flag for switching LLM from the command line
- [ ] Incremental analysis (only re-analyze changed files)
- [ ] SARIF output (GitHub Code Scanning integration)
- [ ] Web dashboard
- [ ] Plugin marketplace
- [ ] Monorepo support (package-based analysis)
- [ ] Diff analysis (compare two commits)
- [ ] Trend tracking (multi-commit history)
- [ ] Config migration system
- [ ] cProfile / flamegraph support

See the [full SDD roadmap](docs/SDD-github-repo-analyzer.md#18-geliştirme-yol-haritası).

## License

[MIT](LICENSE)
