# Development Environment Setup

**Estimated Time**: 30-45 minutes
**Target Audience**: Developers contributing to OctoLLM
**Prerequisites**: Basic command-line and Git knowledge

## Overview

This guide walks you through setting up a complete development environment for OctoLLM, including all tools, dependencies, and IDE configurations for both Python and Rust components.

---

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Core Dependencies](#core-dependencies)
3. [Python Development Setup](#python-development-setup)
4. [Rust Development Setup](#rust-development-setup)
5. [Database Setup](#database-setup)
6. [IDE Configuration](#ide-configuration)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 4 cores | 8+ cores |
| **RAM** | 8 GB | 16+ GB |
| **Disk** | 20 GB free | 50+ GB SSD |
| **OS** | Linux, macOS 11+, Windows 10+ | Linux or macOS |

### Supported Operating Systems

- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 36+, Arch Linux
- **macOS**: 11 (Big Sur) or later (Intel or Apple Silicon)
- **Windows**: Windows 10/11 with WSL2 (Ubuntu 20.04+)

---

## Core Dependencies

### 1. Git (Version Control)

**Linux (Debian/Ubuntu)**:
```bash
sudo apt update
sudo apt install -y git
```

**Linux (Fedora)**:
```bash
sudo dnf install -y git
```

**macOS**:
```bash
# Xcode Command Line Tools (includes git)
xcode-select --install

# Or via Homebrew
brew install git
```

**Windows (WSL2)**:
```bash
# Inside WSL2 Ubuntu
sudo apt update
sudo apt install -y git
```

**Verify**:
```bash
git --version
# Should show: git version 2.30+
```

**Configure Git**:
```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
git config --global init.defaultBranch main
```

### 2. Docker and Docker Compose

**Linux (Ubuntu/Debian)**:
```bash
# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (logout/login after)
sudo usermod -aG docker $USER

# Install Docker Compose
sudo apt install -y docker-compose-plugin

# Verify
docker --version  # Should show 24.0+
docker compose version  # Should show 2.20+
```

**macOS**:
```bash
# Install Docker Desktop
# Download from: https://www.docker.com/products/docker-desktop/

# Or via Homebrew
brew install --cask docker

# Start Docker Desktop from Applications
# Verify in terminal
docker --version
docker compose version
```

**Windows (WSL2)**:
```bash
# Install Docker Desktop for Windows with WSL2 backend
# Download from: https://www.docker.com/products/docker-desktop/

# In WSL2, verify:
docker --version
docker compose version
```

### 3. Make (Build Automation)

**Linux**:
```bash
# Debian/Ubuntu
sudo apt install -y build-essential

# Fedora
sudo dnf install -y make gcc
```

**macOS**:
```bash
# Included in Xcode Command Line Tools
xcode-select --install
```

**Verify**:
```bash
make --version
# Should show: GNU Make 4.0+
```

---

## Python Development Setup

### 1. Install Python 3.11+

**Linux (Ubuntu/Debian)**:
```bash
# Add deadsnakes PPA for latest Python
sudo apt install -y software-properties-common
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Install Python 3.11 and tools
sudo apt install -y python3.11 python3.11-venv python3.11-dev
sudo apt install -y python3-pip

# Set as default (optional)
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

**macOS**:
```bash
# Via Homebrew
brew install python@3.11

# Verify
python3.11 --version
```

**Verify**:
```bash
python3.11 --version
# Should show: Python 3.11.x

pip3 --version
# Should show: pip 23.x+
```

### 2. Install pipx (For Global Tools)

```bash
python3.11 -m pip install --user pipx
python3.11 -m pipx ensurepath

# Restart shell or:
source ~/.bashrc  # or ~/.zshrc on macOS
```

### 3. Install Poetry (Dependency Management)

```bash
pipx install poetry

# Configure Poetry to create venvs in project directory
poetry config virtualenvs.in-project true

# Verify
poetry --version
# Should show: Poetry (version 1.6.0+)
```

### 4. Install Development Tools

```bash
# Code formatting
pipx install black
pipx install isort

# Linting
pipx install ruff
pipx install mypy

# Testing
pipx install pytest
pipx install pytest-cov

# Documentation
pipx install mkdocs
pipx install mkdocs-material

# Verify all tools
black --version
ruff --version
mypy --version
pytest --version
```

### 5. Clone and Setup OctoLLM

```bash
# Clone repository
git clone https://github.com/your-org/octollm.git
cd octollm

# Install Python dependencies for orchestrator
cd orchestrator
poetry install

# Activate virtual environment
poetry shell

# Install pre-commit hooks
poetry run pre-commit install

# Verify installation
poetry run python -c "import fastapi; print(fastapi.__version__)"
```

### 6. Configure Python Tools

**Create `pyproject.toml` (already in repo)**:
```toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'
extend-exclude = '''
/(
  # directories
  \.eggs
  | \.git
  | \.hg
  | \.mypy_cache
  | \.tox
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100
known_first_party = ["orchestrator", "common"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_generics = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --cov=orchestrator --cov-report=html --cov-report=term"

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W", "UP"]
ignore = ["E501"]
```

**Create `.pre-commit-config.yaml` (already in repo)**:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-json
      - id: check-toml
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.10.0
    hooks:
      - id: black
        language_version: python3.11

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
        language_version: python3.11

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.3
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.6.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        exclude: ^tests/
```

---

## Rust Development Setup

### 1. Install Rust Toolchain

```bash
# Install rustup (Rust installer)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Choose: 1) Proceed with installation (default)

# Load Rust environment
source "$HOME/.cargo/env"

# Verify
rustc --version  # Should show: rustc 1.75+
cargo --version  # Should show: cargo 1.75+
```

### 2. Install Rust Components

```bash
# Install nightly toolchain (for some features)
rustup toolchain install nightly

# Install clippy (linter)
rustup component add clippy

# Install rustfmt (formatter)
rustup component add rustfmt

# Install rust-analyzer (LSP)
rustup component add rust-analyzer

# Verify
cargo clippy --version
cargo fmt --version
```

### 3. Install Rust Development Tools

```bash
# cargo-watch: Auto-rebuild on file changes
cargo install cargo-watch

# cargo-edit: Manage dependencies from CLI
cargo install cargo-edit

# cargo-audit: Security vulnerability scanner
cargo install cargo-audit

# cargo-outdated: Check for outdated dependencies
cargo install cargo-outdated

# bacon: Background code checker
cargo install bacon
```

### 4. Build Rust Components

```bash
# Build reflex layer
cd reflex-layer
cargo build

# Run tests
cargo test

# Check for issues
cargo clippy -- -D warnings

# Format code
cargo fmt

# Verify
cargo run --release
# Should start on http://0.0.0.0:8000
```

### 5. Configure Rust Tools

**Create `rustfmt.toml` (already in repo)**:
```toml
edition = "2021"
max_width = 100
hard_tabs = false
tab_spaces = 4
newline_style = "Unix"
use_small_heuristics = "Default"
indent_style = "Block"
wrap_comments = true
format_code_in_doc_comments = true
normalize_comments = true
normalize_doc_attributes = true
imports_granularity = "Crate"
group_imports = "StdExternalCrate"
```

**Create `.cargo/config.toml`**:
```toml
[build]
jobs = 4

[target.x86_64-unknown-linux-gnu]
rustflags = ["-C", "link-arg=-fuse-ld=lld"]

[alias]
b = "build"
c = "check"
t = "test"
r = "run"
```

---

## Database Setup

### 1. PostgreSQL

**Start with Docker**:
```bash
docker run -d \
  --name octollm-postgres \
  -e POSTGRES_USER=octollm \
  -e POSTGRES_PASSWORD=dev-password \
  -e POSTGRES_DB=octollm \
  -p 5432:5432 \
  postgres:15-alpine

# Wait for startup
sleep 5

# Initialize schema
docker cp db/schema.sql octollm-postgres:/tmp/
docker exec octollm-postgres psql -U octollm -d octollm -f /tmp/schema.sql
```

**Or install locally (Linux)**:
```bash
sudo apt install -y postgresql postgresql-contrib

# Start service
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Create user and database
sudo -u postgres psql <<EOF
CREATE USER octollm WITH PASSWORD 'dev-password';
CREATE DATABASE octollm OWNER octollm;
EOF

# Initialize schema
psql -U octollm -d octollm -f db/schema.sql
```

**Verify**:
```bash
psql -U octollm -d octollm -c "\dt"
# Should show: entities, relationships, task_history, action_log
```

### 2. Redis

**Start with Docker**:
```bash
docker run -d \
  --name octollm-redis \
  -p 6379:6379 \
  redis:7-alpine
```

**Or install locally (Linux)**:
```bash
sudo apt install -y redis-server

# Start service
sudo systemctl start redis-server
sudo systemctl enable redis-server
```

**Verify**:
```bash
redis-cli ping
# Should return: PONG
```

### 3. Qdrant (Vector Database)

**Start with Docker**:
```bash
docker run -d \
  --name octollm-qdrant \
  -p 6333:6333 \
  -p 6334:6334 \
  qdrant/qdrant:latest
```

**Verify**:
```bash
curl http://localhost:6333/collections
# Should return: {"result":{"collections":[]},"status":"ok","time":0.000123}
```

---

## IDE Configuration

### Visual Studio Code

#### 1. Install VS Code

**Linux**:
```bash
# Download .deb from https://code.visualstudio.com/
sudo dpkg -i code_*.deb
sudo apt install -f  # Fix dependencies
```

**macOS**:
```bash
brew install --cask visual-studio-code
```

#### 2. Install Extensions

```bash
# Python extensions
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension ms-python.black-formatter
code --install-extension ms-python.isort
code --install-extension ms-toolsai.jupyter

# Rust extensions
code --install-extension rust-lang.rust-analyzer
code --install-extension tamasfe.even-better-toml
code --install-extension serayuzgur.crates

# Docker and Kubernetes
code --install-extension ms-azuretools.vscode-docker
code --install-extension ms-kubernetes-tools.vscode-kubernetes-tools

# General development
code --install-extension eamodio.gitlens
code --install-extension mhutchie.git-graph
code --install-extension editorconfig.editorconfig
code --install-extension yzhang.markdown-all-in-one
```

#### 3. Configure Workspace Settings

**Create `.vscode/settings.json`**:
```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/orchestrator/.venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.ruffEnabled": true,
  "python.formatting.provider": "black",
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"],
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/.pytest_cache": true,
    "**/.mypy_cache": true,
    "**/target": true,
    "**/.venv": true
  },
  "rust-analyzer.cargo.allFeatures": true,
  "rust-analyzer.checkOnSave.command": "clippy",
  "rust-analyzer.inlayHints.enable": true,
  "[rust]": {
    "editor.defaultFormatter": "rust-lang.rust-analyzer",
    "editor.formatOnSave": true
  },
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  }
}
```

**Create `.vscode/launch.json`**:
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Orchestrator",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["orchestrator.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"],
      "cwd": "${workspaceFolder}/orchestrator",
      "env": {
        "PYTHONPATH": "${workspaceFolder}/orchestrator"
      },
      "console": "integratedTerminal",
      "justMyCode": false
    },
    {
      "name": "Rust: Reflex Layer",
      "type": "lldb",
      "request": "launch",
      "program": "${workspaceFolder}/reflex-layer/target/debug/reflex-layer",
      "args": [],
      "cwd": "${workspaceFolder}/reflex-layer",
      "env": {
        "RUST_LOG": "debug",
        "REDIS_URL": "redis://localhost:6379"
      }
    },
    {
      "name": "Python: Current File",
      "type": "python",
      "request": "launch",
      "program": "${file}",
      "console": "integratedTerminal",
      "justMyCode": false
    }
  ]
}
```

**Create `.vscode/tasks.json`**:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Run Tests (Python)",
      "type": "shell",
      "command": "poetry run pytest",
      "group": {
        "kind": "test",
        "isDefault": true
      },
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Run Tests (Rust)",
      "type": "shell",
      "command": "cargo test",
      "group": "test",
      "presentation": {
        "reveal": "always",
        "panel": "new"
      }
    },
    {
      "label": "Format Code (Python)",
      "type": "shell",
      "command": "poetry run black . && poetry run isort .",
      "group": "build"
    },
    {
      "label": "Format Code (Rust)",
      "type": "shell",
      "command": "cargo fmt",
      "group": "build"
    },
    {
      "label": "Lint (Python)",
      "type": "shell",
      "command": "poetry run ruff check . && poetry run mypy .",
      "group": "build"
    },
    {
      "label": "Lint (Rust)",
      "type": "shell",
      "command": "cargo clippy -- -D warnings",
      "group": "build"
    }
  ]
}
```

### PyCharm (Alternative)

#### 1. Install PyCharm Professional

**Linux**:
```bash
# Via JetBrains Toolbox
# Download from: https://www.jetbrains.com/toolbox-app/
```

**macOS**:
```bash
brew install --cask pycharm
```

#### 2. Configure Project

1. Open `octollm` folder as project
2. **File > Settings > Project > Python Interpreter**
   - Add interpreter: Poetry Environment
   - Poetry executable: `~/.local/bin/poetry`
   - Select: `orchestrator/.venv`

3. **File > Settings > Tools > Python Integrated Tools**
   - Default test runner: pytest
   - Docstring format: Google

4. **File > Settings > Editor > Code Style > Python**
   - Line length: 100
   - Use Black formatter

#### 3. Run Configurations

**Create run configuration for Orchestrator**:
- Name: Orchestrator
- Script path: `uvicorn`
- Parameters: `orchestrator.main:app --reload --host 0.0.0.0 --port 8000`
- Working directory: `$PROJECT_DIR$/orchestrator`
- Environment variables: `PYTHONPATH=$PROJECT_DIR$/orchestrator`

---

## Verification

### 1. Verify Python Environment

```bash
cd orchestrator
poetry shell

# Run type checking
mypy .

# Run linting
ruff check .

# Run formatting check
black --check .
isort --check .

# Run tests
pytest

# Check coverage
pytest --cov=orchestrator --cov-report=term
# Should show >80% coverage
```

### 2. Verify Rust Environment

```bash
cd reflex-layer

# Run tests
cargo test

# Run linting
cargo clippy -- -D warnings

# Check formatting
cargo fmt -- --check

# Build release binary
cargo build --release

# Run
cargo run --release
# Should start on http://0.0.0.0:8000
```

### 3. Verify Integration

```bash
# Start all services
docker-compose up -d

# Wait for startup
sleep 10

# Run health checks
curl http://localhost:8000/health  # Reflex
curl http://localhost:8001/health  # Orchestrator

# Submit test task
curl -X POST http://localhost:8001/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal": "Echo hello world", "priority": "low"}'

# Should return task_id
```

### 4. Verify Database Connections

```bash
# PostgreSQL
psql -U octollm -d octollm -c "SELECT version();"

# Redis
redis-cli ping

# Qdrant
curl http://localhost:6333/collections
```

---

## Troubleshooting

### Python Issues

**Issue**: `poetry install` fails with SSL error

**Solution**:
```bash
# Update certificates (Linux)
sudo apt install -y ca-certificates

# Update certificates (macOS)
/Applications/Python\ 3.11/Install\ Certificates.command

# Retry
poetry install
```

**Issue**: `ModuleNotFoundError` when running tests

**Solution**:
```bash
# Ensure you're in poetry shell
poetry shell

# Or use poetry run
poetry run pytest

# Check PYTHONPATH
echo $PYTHONPATH
export PYTHONPATH="${PWD}:${PYTHONPATH}"
```

**Issue**: `mypy` reports errors in third-party packages

**Solution**:
```bash
# Install type stubs
poetry add --group dev types-requests types-redis types-psycopg2

# Or ignore in mypy.ini
echo "[mypy-third_party_package.*]
ignore_missing_imports = True" >> mypy.ini
```

### Rust Issues

**Issue**: `cargo build` fails with linker error

**Solution**:
```bash
# Install linker (Linux)
sudo apt install -y build-essential lld

# Install linker (macOS)
xcode-select --install
```

**Issue**: `rust-analyzer` not working in VS Code

**Solution**:
```bash
# Update rust-analyzer
rustup component add rust-analyzer --toolchain stable

# Reload VS Code
# Cmd+Shift+P (Mac) or Ctrl+Shift+P (Linux)
# > Reload Window
```

**Issue**: Slow compilation times

**Solution**:
```bash
# Enable parallel compilation
export CARGO_BUILD_JOBS=8

# Use sccache for caching
cargo install sccache
export RUSTC_WRAPPER=sccache

# Add to ~/.bashrc or ~/.zshrc
```

### Database Issues

**Issue**: Can't connect to PostgreSQL

**Solution**:
```bash
# Check if running
docker ps | grep postgres

# Check logs
docker logs octollm-postgres

# Restart
docker restart octollm-postgres

# Test connection
psql -h localhost -U octollm -d octollm
```

**Issue**: Redis connection refused

**Solution**:
```bash
# Check if running
docker ps | grep redis

# Check port
netstat -tlnp | grep 6379

# Restart
docker restart octollm-redis
```

---

## Environment Variables Reference

Create `.env` in project root:

```bash
# LLM API Keys
OPENAI_API_KEY=sk-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Database URLs
POSTGRES_URL=postgresql://octollm:dev-password@localhost:5432/octollm
REDIS_URL=redis://localhost:6379
QDRANT_URL=http://localhost:6333

# System Configuration
LOG_LEVEL=DEBUG  # DEBUG, INFO, WARNING, ERROR
ENVIRONMENT=development  # development, staging, production
PYTHONPATH=${PWD}/orchestrator:${PYTHONPATH}

# Optional: Rust
RUST_LOG=debug  # trace, debug, info, warn, error
RUST_BACKTRACE=1  # Enable backtraces
```

---

## Next Steps

1. **[Getting Started](./getting-started.md)** - Run your first OctoLLM task
2. **[Local Development Workflow](./local-development.md)** - Day-to-day development practices
3. **[Creating Custom Arms](./custom-arms.md)** - Build specialized components
4. **[Testing Guide](./testing-guide.md)** - Write comprehensive tests
5. **[Debugging Guide](./debugging.md)** - Advanced debugging techniques

---

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Maintained By**: OctoLLM Documentation Team
