# Phase 0: Project Setup & Infrastructure

**Status**: Not Started
**Duration**: 1-2 weeks
**Team Size**: 2-3 engineers (1 DevOps, 1-2 backend)
**Prerequisites**: None (Critical Path - Blocks All Phases)
**Start Date**: TBD
**Target Completion**: TBD

---

## Overview

Phase 0 establishes the foundational infrastructure and development environment for the OctoLLM project. This phase must be completed before any implementation work begins, as it provides the repository structure, CI/CD pipeline, development tooling, and cloud infrastructure needed for all subsequent phases.

**Key Deliverables**:
1. Repository structure and Git workflow
2. Development environment (Docker Compose, VS Code devcontainer)
3. CI/CD pipeline (linting, testing, security scanning, image building)
4. Cloud infrastructure (Kubernetes cluster, managed databases, secrets management)
5. Project documentation and governance

**Success Criteria**:
- ✅ Developer can run `docker-compose up` and have full environment
- ✅ CI/CD pipeline passes on all checks
- ✅ Infrastructure provisioned with single command
- ✅ Secrets never committed to repository
- ✅ 2+ developers verify setup works on their machines

---

## Sprint 0.1: Repository Structure & Git Workflow [Week 1, Days 1-2]

**Duration**: 2 days
**Owner**: Lead Engineer
**Reference**: `docs/guides/development-workflow.md`, `docs/engineering/coding-standards.md`

### Task 0.1.1: Initialize Monorepo Structure [CRITICAL]

**Priority**: CRITICAL
**Effort**: 4 hours
**Dependencies**: None

**Implementation**:

```bash
# Create root directory structure
mkdir -p octollm/{orchestrator,reflex-layer,arms,common,k8s,tests,docs}
cd octollm

# Create subdirectories for each arm
mkdir -p arms/{planner,executor,coder,judge,guardian,retriever}

# Create common libraries
mkdir -p common/{python,rust}

# Create Kubernetes manifests directories
mkdir -p k8s/{base,dev,staging,prod,databases,monitoring}

# Create test directories
mkdir -p tests/{unit,integration,e2e,performance,security}

# Keep existing docs
# docs/ already exists with 56 comprehensive markdown files
```

**Directory Structure**:
```
octollm/
├── README.md                      # Project overview
├── LICENSE                        # Apache 2.0
├── .gitignore                     # Python, Rust, secrets
├── .env.example                   # Environment template
├── docker-compose.yml             # Local development
├── docker-compose.dev.yml         # Dev overrides
├── docker-compose.prod.yml        # Production overrides
├── orchestrator/                  # Python FastAPI service
│   ├── Dockerfile
│   ├── pyproject.toml             # Poetry config
│   ├── main.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/                   # FastAPI routes
│   │   ├── core/                  # Planning, routing, integration
│   │   ├── models/                # Pydantic models
│   │   └── utils/
│   └── tests/
├── reflex-layer/                  # Rust Actix-web service
│   ├── Dockerfile
│   ├── Cargo.toml
│   ├── src/
│   │   ├── main.rs
│   │   ├── pii_detector.rs
│   │   ├── injection_detector.rs
│   │   ├── cache.rs
│   │   └── rate_limiter.rs
│   └── tests/
├── arms/                          # Specialized arm services
│   ├── planner/                   # Python service
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── main.py
│   │   └── tests/
│   ├── executor/                  # Rust service
│   │   ├── Dockerfile
│   │   ├── Cargo.toml
│   │   ├── src/main.rs
│   │   └── tests/
│   ├── coder/                     # Python service
│   ├── judge/                     # Python service
│   ├── guardian/                  # Python service
│   └── retriever/                 # Python service
├── common/                        # Shared libraries
│   ├── python/
│   │   ├── octollm_common/
│   │   │   ├── models.py          # Shared Pydantic models
│   │   │   ├── db.py              # Database clients
│   │   │   ├── llm.py             # LLM abstraction
│   │   │   └── metrics.py         # Prometheus metrics
│   │   └── pyproject.toml
│   └── rust/
│       ├── octollm_common/
│       │   ├── Cargo.toml
│       │   └── src/lib.rs
├── k8s/                           # Kubernetes manifests
│   ├── base/                      # Base configs (kustomize)
│   ├── dev/                       # Dev environment overlays
│   ├── staging/                   # Staging overlays
│   ├── prod/                      # Production overlays
│   ├── databases/                 # Database StatefulSets
│   └── monitoring/                # Prometheus, Grafana
├── tests/                         # Integration and E2E tests
│   ├── unit/                      # (Tests live with code)
│   ├── integration/               # Multi-service tests
│   ├── e2e/                       # End-to-end workflows
│   ├── performance/               # Load tests (k6, Locust)
│   └── security/                  # Security tests
├── docs/                          # Comprehensive documentation (56 files)
│   ├── README.md
│   ├── architecture/
│   ├── components/
│   ├── implementation/
│   ├── operations/
│   ├── security/
│   ├── api/
│   ├── guides/
│   └── adr/
└── to-dos/                        # This directory
    ├── MASTER-TODO.md
    ├── PHASE-0-PROJECT-SETUP.md
    └── ...
```

**Acceptance Criteria**:
- [ ] All directories created with appropriate structure
- [ ] `.gitkeep` files in empty directories
- [ ] Structure documented in README.md

---

### Task 0.1.2: Configure .gitignore [HIGH]

**Priority**: HIGH
**Effort**: 1 hour
**Dependencies**: 0.1.1

**Implementation**:

Create `.gitignore`:
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
venv/
ENV/
.venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/

# Rust
target/
Cargo.lock
**/*.rs.bk

# Environment files (NEVER COMMIT SECRETS)
.env
.env.local
.env.*.local
*.key
*.pem
*.p12
*.pfx
credentials.json
secrets.yaml

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Databases
*.db
*.sqlite
*.sqlite3
postgres-data/
redis-data/
qdrant-data/

# Logs
*.log
logs/

# Build artifacts
*.tar.gz
*.zip

# Terraform
.terraform/
*.tfstate
*.tfstate.backup

# Kubernetes secrets
*secret*.yaml
!*secret*.example.yaml
```

**Acceptance Criteria**:
- [ ] `.gitignore` committed
- [ ] No secrets in repository history (scan with gitleaks)
- [ ] Verified with `git status` (no unwanted files)

---

### Task 0.1.3: Add LICENSE (Apache 2.0) [MEDIUM]

**Priority**: MEDIUM
**Effort**: 15 minutes
**Dependencies**: None

**Implementation**:
- Download Apache 2.0 license from https://www.apache.org/licenses/LICENSE-2.0.txt
- Add to `LICENSE` file in repository root
- Update README.md with license badge

**Acceptance Criteria**:
- [ ] LICENSE file present
- [ ] Copyright notice updated with organization name
- [ ] README.md includes license section

---

### Task 0.1.4: Create Initial README.md [HIGH]

**Priority**: HIGH
**Effort**: 2 hours
**Dependencies**: 0.1.1

**Implementation**:

Create `README.md`:
```markdown
# OctoLLM

**Distributed AI Architecture for Offensive Security and Developer Tooling**

![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)
![Status](https://img.shields.io/badge/status-pre--implementation-yellow)
![Docs](https://img.shields.io/badge/docs-comprehensive-green)

## What is OctoLLM?

OctoLLM is a distributed AI system inspired by octopus neurobiology, where:
- **Central Brain (Orchestrator)**: Strategic planning and coordination
- **Autonomous Arms (Specialists)**: Domain-specific execution with local decision-making
- **Reflex Layer**: Fast preprocessing for common patterns
- **Distributed Memory**: Global semantic memory + local episodic stores

### Key Features

- 🧠 **Intelligent Orchestration**: Multi-arm task decomposition and coordination
- ⚡ **Low Latency**: <10ms preprocessing, <30s P99 task completion
- 🔒 **Security-First**: Capability isolation, PII protection, defense-in-depth
- 📊 **Cost-Optimized**: <50% cost vs. monolithic LLM via specialized routing
- 🔍 **Transparent**: Complete provenance tracking and audit logging
- 🚀 **Scalable**: Kubernetes-native with autoscaling

## Quick Start

Get OctoLLM running locally in 15 minutes:

```bash
# Clone and configure
git clone https://github.com/your-org/octollm.git
cd octollm
cp .env.example .env
# Edit .env with your API keys

# Start services
docker-compose up -d

# Verify health
curl http://localhost:8000/health

# Submit first task
curl -X POST http://localhost:8000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal": "Write a Python function to calculate fibonacci numbers"}'
```

See [Quick Start Guide](docs/guides/quickstart.md) for detailed instructions.

## Documentation

📚 **Comprehensive documentation** available in `docs/` (56 files, ~77,300 lines):

- **[Architecture](docs/architecture/)** - System design and data flows
- **[Components](docs/components/)** - Orchestrator, Arms, Reflex Layer specs
- **[Implementation](docs/implementation/)** - Getting started, dev environment, custom arms
- **[Operations](docs/operations/)** - Deployment, monitoring, troubleshooting
- **[Security](docs/security/)** - Threat model, compliance, testing
- **[API Reference](docs/api/)** - REST API contracts and schemas
- **[Guides](docs/guides/)** - Contributing, development workflow, migration

### Quick Links

- [System Overview](docs/architecture/system-overview.md)
- [Getting Started](docs/implementation/getting-started.md)
- [Development Environment Setup](docs/implementation/dev-environment.md)
- [Creating Custom Arms](docs/implementation/custom-arms.md)
- [Kubernetes Deployment](docs/operations/kubernetes-deployment.md)
- [Contributing](docs/guides/contributing.md)

## Project Status

**Current Phase**: Phase 0 - Project Setup (In Progress)
**Implementation Status**: Pre-Implementation (Documentation Complete)

See [MASTER-TODO.md](to-dos/MASTER-TODO.md) for complete project roadmap.

## Technology Stack

- **Languages**: Python 3.11+, Rust 1.75+
- **Databases**: PostgreSQL 15+, Redis 7+, Qdrant 1.7+
- **Frameworks**: FastAPI, Axum
- **Deployment**: Docker, Kubernetes 1.28+
- **LLM Providers**: OpenAI (GPT-4), Anthropic (Claude 3)
- **Monitoring**: Prometheus, Grafana, Loki, Jaeger

See [ADR-001: Technology Stack](docs/adr/001-technology-stack.md) for rationale.

## Contributing

We welcome contributions! Please see:
- [Contributing Guide](docs/guides/contributing.md)
- [Development Workflow](docs/guides/development-workflow.md)
- [Code Review Checklist](docs/engineering/code-review.md)
- [Coding Standards](docs/engineering/coding-standards.md)

## Community

- **Discord**: https://discord.gg/octollm
- **GitHub Issues**: https://github.com/your-org/octollm/issues
- **Documentation**: https://docs.octollm.io
- **Email**: team@octollm.io

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by octopus nervous system research (Hochner et al.)
- Built on FastAPI, LangChain, Kubernetes
- Community contributors and early adopters

---

**Maintained by**: OctoLLM Core Team
**Last Updated**: 2025-11-10
```

**Acceptance Criteria**:
- [ ] README.md committed
- [ ] All links valid (test with link checker)
- [ ] Badges display correctly on GitHub

---

### Task 0.1.5: Set Up Git Branch Protection [CRITICAL]

**Priority**: CRITICAL
**Effort**: 1 hour
**Dependencies**: Repository created on GitHub

**Implementation**:

1. **Go to GitHub Repository Settings → Branches**

2. **Add Branch Protection Rule for `main`**:
   - **Branch name pattern**: `main`
   - **Require pull request before merging**: ✅
     - Required approvals: 1
     - Dismiss stale reviews: ✅
   - **Require status checks before merging**: ✅
     - Required checks:
       - `lint` (Python/Rust)
       - `test` (Unit + Integration)
       - `security-scan` (Bandit, Trivy)
   - **Require conversation resolution**: ✅
   - **Do not allow bypassing**: ✅
   - **Require linear history**: ✅ (no merge commits, rebase only)
   - **Include administrators**: ✅

3. **Create `develop` branch**:
```bash
git checkout -b develop
git push origin develop
```

4. **Add Branch Protection Rule for `develop`** (same as main but allow force push for team leads)

**Branching Strategy**:
- `main`: Production-ready code only
- `develop`: Integration branch (merge features here first)
- `feature/*`: Feature branches (e.g., `feature/orchestrator-mvp`)
- `bugfix/*`: Bug fix branches
- `hotfix/*`: Urgent production fixes (branch from main)

**Acceptance Criteria**:
- [ ] Branch protection configured on `main`
- [ ] Cannot push directly to `main` (force push blocked)
- [ ] `develop` branch created
- [ ] Branching strategy documented in `docs/guides/development-workflow.md`

---

### Task 0.1.6: Configure Pre-Commit Hooks [HIGH]

**Priority**: HIGH
**Effort**: 2 hours
**Dependencies**: 0.1.1
**Reference**: `docs/engineering/coding-standards.md`

**Implementation**:

1. **Install pre-commit**:
```bash
pip install pre-commit
```

2. **Create `.pre-commit-config.yaml`**:
```yaml
repos:
  # Python formatting
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
        language_version: python3.11
        args: [--line-length=88]

  # Python linting
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.5
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  # Python type checking
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.0
    hooks:
      - id: mypy
        args: [--strict, --ignore-missing-imports]
        additional_dependencies: [pydantic, fastapi]

  # Rust formatting
  - repo: local
    hooks:
      - id: rustfmt
        name: rustfmt
        entry: cargo fmt --all --
        language: system
        types: [rust]
        pass_filenames: false

  # Rust linting
  - repo: local
    hooks:
      - id: clippy
        name: clippy
        entry: cargo clippy --all-targets --all-features -- -D warnings
        language: system
        types: [rust]
        pass_filenames: false

  # Conventional Commits
  - repo: https://github.com/compwa/commitlint-pre-commit-hook
    rev: 1.0.0
    hooks:
      - id: commitlint
        stages: [commit-msg]
        additional_dependencies: ['@commitlint/config-conventional']

  # Secrets detection
  - repo: https://github.com/gitleaks/gitleaks
    rev: v8.18.0
    hooks:
      - id: gitleaks

  # General
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-toml
      - id: check-added-large-files
        args: [--maxkb=500]
      - id: check-merge-conflict
```

3. **Install hooks**:
```bash
pre-commit install
pre-commit install --hook-type commit-msg
```

4. **Test hooks**:
```bash
# Create dummy Python file with issues
echo "x=1" > test.py
git add test.py
git commit -m "test"
# Should fail and auto-fix formatting
```

5. **Document in CONTRIBUTING.md**

**Acceptance Criteria**:
- [ ] Pre-commit hooks configured
- [ ] Hooks run on every commit
- [ ] Secrets detection working (test with fake API key)
- [ ] Conventional Commits enforced
- [ ] All team members install hooks

---

## Sprint 0.2: Development Environment Setup [Week 1, Days 3-4]

**Duration**: 2 days
**Owner**: DevOps Engineer
**Reference**: `docs/implementation/dev-environment.md` (1,457 lines)

### Task 0.2.1: Create Base Dockerfiles [CRITICAL]

**Priority**: CRITICAL
**Effort**: 4 hours
**Dependencies**: 0.1.1

**Implementation**:

1. **Orchestrator Dockerfile** (`orchestrator/Dockerfile`):
```dockerfile
# Multi-stage build
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.0

# Copy dependency files
WORKDIR /app
COPY pyproject.toml poetry.lock ./

# Install dependencies (no dev dependencies in prod)
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# Runtime stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user
RUN useradd -m -u 1000 octollm

WORKDIR /app
COPY . .

# Set ownership
RUN chown -R octollm:octollm /app

USER octollm

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

2. **Reflex Layer Dockerfile** (`reflex-layer/Dockerfile`):
```dockerfile
# Build stage
FROM rust:1.75-slim as builder

WORKDIR /app

# Cache dependencies (separate layer)
COPY Cargo.toml Cargo.lock ./
RUN mkdir src && echo "fn main() {}" > src/main.rs \
    && cargo build --release \
    && rm -rf src

# Build actual application
COPY src ./src
RUN cargo build --release

# Runtime stage
FROM debian:bookworm-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 octollm

WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/target/release/reflex-layer /app/reflex-layer

# Set ownership
RUN chown -R octollm:octollm /app

USER octollm

EXPOSE 8001

CMD ["./reflex-layer"]
```

3. **Arms Base Dockerfile** (`arms/Dockerfile.base`):
```dockerfile
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry
RUN pip install poetry==1.7.0

# Create non-root user
RUN useradd -m -u 1000 octollm

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root --only main

# Copy application
COPY . .
RUN chown -R octollm:octollm /app

USER octollm

EXPOSE 8100

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8100"]
```

**Acceptance Criteria**:
- [ ] Dockerfiles build successfully
- [ ] Images run without errors
- [ ] Non-root user enforced
- [ ] Health checks working

---

### Task 0.2.2: Create docker-compose.dev.yml [CRITICAL]

**Priority**: CRITICAL
**Effort**: 3 hours
**Dependencies**: 0.2.1
**Reference**: `docs/operations/docker-compose-setup.md` (1,794 lines)

**Implementation**:

Create `docker-compose.yml` (base) and `docker-compose.dev.yml` (development overrides):

**docker-compose.yml**:
```yaml
version: '3.9'

services:
  # Databases
  postgres:
    image: postgres:15-alpine
    container_name: octollm-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-octollm}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-dev-password}
      POSTGRES_DB: ${POSTGRES_DB:-octollm}
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./db/schema.sql:/docker-entrypoint-initdb.d/schema.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U octollm"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: octollm-redis
    command: redis-server --requirepass ${REDIS_PASSWORD:-dev-redis-password}
    volumes:
      - redis-data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.7.0
    container_name: octollm-qdrant
    volumes:
      - qdrant-data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Core Services
  reflex-layer:
    build:
      context: ./reflex-layer
      dockerfile: Dockerfile
    container_name: octollm-reflex
    environment:
      REDIS_URL: redis://:${REDIS_PASSWORD:-dev-redis-password}@redis:6379
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    ports:
      - "8001:8001"
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  orchestrator:
    build:
      context: ./orchestrator
      dockerfile: Dockerfile
    container_name: octollm-orchestrator
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER:-octollm}:${POSTGRES_PASSWORD:-dev-password}@postgres:5432/${POSTGRES_DB:-octollm}
      REDIS_URL: redis://:${REDIS_PASSWORD:-dev-redis-password}@redis:6379
      QDRANT_URL: http://qdrant:6333
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      reflex-layer:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres-data:
  redis-data:
  qdrant-data:

networks:
  default:
    name: octollm-network
```

**docker-compose.dev.yml**:
```yaml
version: '3.9'

services:
  # Development overrides
  orchestrator:
    build:
      context: ./orchestrator
      dockerfile: Dockerfile
      target: builder  # Stay in builder stage for dev tools
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./orchestrator:/app  # Hot reload
    environment:
      ENVIRONMENT: development
      LOG_LEVEL: DEBUG

  reflex-layer:
    volumes:
      - ./reflex-layer/src:/app/src  # Hot reload (rebuild on change)

  # Development tools
  adminer:
    image: adminer:latest
    container_name: octollm-adminer
    ports:
      - "8080:8080"
    environment:
      ADMINER_DEFAULT_SERVER: postgres

  redis-commander:
    image: rediscommander/redis-commander:latest
    container_name: octollm-redis-commander
    environment:
      REDIS_HOSTS: local:redis:6379:0:${REDIS_PASSWORD:-dev-redis-password}
    ports:
      - "8081:8081"
```

**Usage**:
```bash
# Start development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker-compose logs -f orchestrator

# Rebuild after code changes (Rust)
docker-compose build reflex-layer
docker-compose up -d reflex-layer

# Stop all services
docker-compose down

# Reset databases (WARNING: deletes data)
docker-compose down -v
```

**Acceptance Criteria**:
- [ ] All services start successfully
- [ ] Hot reload works for Python services
- [ ] Databases persist data across restarts
- [ ] Health checks passing
- [ ] Adminer accessible at http://localhost:8080

---

### Task 0.2.3: Create .env.example Template [HIGH]

**Priority**: HIGH
**Effort**: 1 hour
**Dependencies**: None
**Reference**: `docs/implementation/getting-started.md`

**Implementation**:

Create `.env.example`:
```bash
# OctoLLM Environment Configuration
# Copy this file to .env and fill in your values
# NEVER commit .env to version control!

# ===========================
# LLM API Keys (Required)
# ===========================
# Get OpenAI key from: https://platform.openai.com/api-keys
OPENAI_API_KEY=sk-your-openai-api-key-here

# Get Anthropic key from: https://console.anthropic.com/
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# ===========================
# Database Configuration
# ===========================
POSTGRES_USER=octollm
POSTGRES_PASSWORD=CHANGE-THIS-IN-PRODUCTION-strong-password-here
POSTGRES_DB=octollm

# Redis
REDIS_PASSWORD=CHANGE-THIS-IN-PRODUCTION-redis-password

# Qdrant (leave empty for local development)
QDRANT_API_KEY=

# ===========================
# Application Configuration
# ===========================
# Environment: development, staging, production
ENVIRONMENT=development

# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# Task timeout (seconds)
TASK_TIMEOUT=300

# Max concurrent tasks
MAX_CONCURRENT_TASKS=10

# ===========================
# Security Configuration
# ===========================
# JWT secret for capability tokens (generate with: openssl rand -hex 32)
JWT_SECRET=your-jwt-secret-here-CHANGE-IN-PRODUCTION

# Allowed origins for CORS (comma-separated)
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8000

# ===========================
# Performance Configuration
# ===========================
# Database connection pool
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20

# Redis connection pool
REDIS_POOL_SIZE=10

# LLM request timeout (seconds)
LLM_TIMEOUT=30

# Cache TTL (seconds)
CACHE_TTL=3600

# ===========================
# Monitoring (Optional)
# ===========================
# Prometheus metrics port
METRICS_PORT=9090

# Jaeger tracing endpoint
JAEGER_ENDPOINT=http://localhost:14268/api/traces

# ===========================
# Cloud Configuration (Production Only)
# ===========================
# AWS_ACCESS_KEY_ID=
# AWS_SECRET_ACCESS_KEY=
# AWS_REGION=us-east-1

# GCP_PROJECT_ID=
# GCP_SERVICE_ACCOUNT_KEY=

# AZURE_SUBSCRIPTION_ID=
# AZURE_CLIENT_ID=
# AZURE_CLIENT_SECRET=
# AZURE_TENANT_ID=
```

**Acceptance Criteria**:
- [ ] `.env.example` committed to repository
- [ ] All required variables documented
- [ ] Security warnings prominent
- [ ] Generation commands provided where applicable

---

### Task 0.2.4: Create VS Code Devcontainer [MEDIUM]

**Priority**: MEDIUM
**Effort**: 2 hours
**Dependencies**: 0.2.2

**Implementation**:

Create `.devcontainer/devcontainer.json`:
```json
{
  "name": "OctoLLM Development",
  "dockerComposeFile": [
    "../docker-compose.yml",
    "../docker-compose.dev.yml"
  ],
  "service": "orchestrator",
  "workspaceFolder": "/app",

  "features": {
    "ghcr.io/devcontainers/features/python:1": {
      "version": "3.11"
    },
    "ghcr.io/devcontainers/features/rust:1": {
      "version": "1.75"
    },
    "ghcr.io/devcontainers/features/docker-in-docker:2": {},
    "ghcr.io/devcontainers/features/kubectl-helm-minikube:1": {
      "kubectl": "1.28",
      "helm": "3.13"
    }
  },

  "customizations": {
    "vscode": {
      "extensions": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "ms-python.black-formatter",
        "charliermarsh.ruff",
        "rust-lang.rust-analyzer",
        "tamasfe.even-better-toml",
        "redhat.vscode-yaml",
        "ms-azuretools.vscode-docker",
        "ms-kubernetes-tools.vscode-kubernetes-tools",
        "GitHub.copilot",
        "eamodio.gitlens"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/usr/local/bin/python",
        "python.linting.enabled": true,
        "python.linting.pylintEnabled": false,
        "python.linting.ruffEnabled": true,
        "python.formatting.provider": "black",
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
          "source.organizeImports": true
        },
        "rust-analyzer.checkOnSave.command": "clippy"
      }
    }
  },

  "forwardPorts": [
    8000,  // Orchestrator
    8001,  // Reflex Layer
    8080,  // Adminer
    8081,  // Redis Commander
    5432,  // PostgreSQL
    6379,  // Redis
    6333   // Qdrant
  ],

  "postCreateCommand": "pre-commit install && poetry install",

  "remoteUser": "octollm"
}
```

**Acceptance Criteria**:
- [ ] Devcontainer builds successfully
- [ ] All extensions installed
- [ ] Python/Rust tooling working
- [ ] Ports forwarded correctly

---

## Sprint 0.3: CI/CD Pipeline (GitHub Actions) [Week 1, Days 5-7]

**Duration**: 3 days
**Owner**: DevOps Engineer
**Reference**: `docs/guides/development-workflow.md`, `docs/testing/strategy.md`

### Task 0.3.1: Create Linting Workflow [CRITICAL]

**Priority**: CRITICAL
**Effort**: 3 hours
**Dependencies**: 0.1.6

**Implementation**:

Create `.github/workflows/lint.yml`:
```yaml
name: Lint

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  python-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install poetry==1.7.0
          poetry install --no-root --only dev

      - name: Run Ruff (linter)
        run: poetry run ruff check .

      - name: Run Black (formatter check)
        run: poetry run black --check .

      - name: Run mypy (type checker)
        run: poetry run mypy orchestrator/ arms/ common/python/
        continue-on-error: true  # Don't fail build yet

  rust-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust 1.75
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: '1.75'
          components: rustfmt, clippy

      - name: Cache Rust dependencies
        uses: actions/cache@v3
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            target/
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}

      - name: Run rustfmt
        run: cargo fmt --all -- --check

      - name: Run clippy
        run: cargo clippy --all-targets --all-features -- -D warnings
```

**Acceptance Criteria**:
- [ ] Workflow runs on PRs to main/develop
- [ ] Python linting detects style issues
- [ ] Rust linting detects style issues
- [ ] Fails CI if issues found

---

### Task 0.3.2: Create Testing Workflow [CRITICAL]

**Priority**: CRITICAL
**Effort**: 4 hours
**Dependencies**: 0.3.1
**Reference**: `docs/testing/strategy.md`

**Implementation**:

Create `.github/workflows/test.yml`:
```yaml
name: Test

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]

jobs:
  python-tests:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    services:
      postgres:
        image: postgres:15-alpine
        env:
          POSTGRES_USER: octollm
          POSTGRES_PASSWORD: test-password
          POSTGRES_DB: octollm_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7-alpine
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install dependencies
        run: |
          pip install poetry==1.7.0
          poetry install --no-root

      - name: Run unit tests
        env:
          DATABASE_URL: postgresql://octollm:test-password@localhost:5432/octollm_test
          REDIS_URL: redis://localhost:6379
        run: |
          poetry run pytest tests/unit/ -v --cov --cov-report=xml --cov-report=term

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          flags: python-${{ matrix.python-version }}
          name: Python ${{ matrix.python-version }}

  rust-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust 1.75
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: '1.75'

      - name: Cache Rust dependencies
        uses: actions/cache@v3
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            target/
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}

      - name: Run tests
        run: cargo test --all-features --workspace

  integration-tests:
    runs-on: ubuntu-latest
    needs: [python-tests, rust-tests]
    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Start services
        run: docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

      - name: Wait for services
        run: |
          timeout 60 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done'

      - name: Run integration tests
        run: |
          pip install poetry==1.7.0
          poetry install --no-root
          poetry run pytest tests/integration/ -v

      - name: Collect logs
        if: failure()
        run: docker-compose logs > docker-compose-logs.txt

      - name: Upload logs
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: docker-compose-logs
          path: docker-compose-logs.txt
```

**Acceptance Criteria**:
- [ ] Unit tests run in CI
- [ ] Integration tests run with Docker Compose
- [ ] Coverage reports uploaded to Codecov
- [ ] Tests run on multiple Python versions
- [ ] Logs collected on failure

---

### Task 0.3.3: Create Security Scanning Workflow [CRITICAL]

**Priority**: CRITICAL
**Effort**: 3 hours
**Dependencies**: 0.3.1
**Reference**: `docs/security/security-testing.md` (4,498 lines)

**Implementation**:

Create `.github/workflows/security.yml`:
```yaml
name: Security Scan

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main, develop]
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight

jobs:
  python-sast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Bandit
        run: pip install bandit[toml]

      - name: Run Bandit (Python SAST)
        run: bandit -r orchestrator/ arms/ common/python/ -f json -o bandit-report.json

      - name: Upload Bandit report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: bandit-report
          path: bandit-report.json

  python-dependency-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run Snyk Python
        uses: snyk/actions/python@master
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high

  rust-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install Rust 1.75
        uses: dtolnay/rust-toolchain@stable
        with:
          toolchain: '1.75'

      - name: Install cargo-audit
        run: cargo install cargo-audit

      - name: Run cargo audit
        run: cargo audit

  container-scan:
    runs-on: ubuntu-latest
    needs: [python-sast, rust-audit]
    steps:
      - uses: actions/checkout@v4

      - name: Build images
        run: |
          docker build -t octollm/orchestrator:test ./orchestrator
          docker build -t octollm/reflex:test ./reflex-layer

      - name: Run Trivy (container scanner)
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: 'octollm/orchestrator:test'
          format: 'sarif'
          output: 'trivy-orchestrator.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-orchestrator.sarif'

  secrets-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for gitleaks

      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

**Acceptance Criteria**:
- [ ] SAST scans run on every PR
- [ ] Dependency scans find vulnerabilities
- [ ] Container scans detect image issues
- [ ] Secret scans prevent accidental commits
- [ ] CI fails on HIGH/CRITICAL findings

---

### Task 0.3.4: Create Build and Push Workflow [HIGH]

**Priority**: HIGH
**Effort**: 3 hours
**Dependencies**: 0.3.3

**Implementation**:

Create `.github/workflows/build.yml`:
```yaml
name: Build and Push Images

on:
  push:
    branches: [main]
    tags:
      - 'v*.*.*'
  pull_request:
    branches: [main]

env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ghcr.io/${{ github.repository_owner }}

jobs:
  build-and-push:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    strategy:
      matrix:
        service:
          - name: orchestrator
            context: ./orchestrator
          - name: reflex-layer
            context: ./reflex-layer
          - name: planner-arm
            context: ./arms/planner
          - name: executor-arm
            context: ./arms/executor

    steps:
      - uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        if: github.event_name != 'pull_request'
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.IMAGE_PREFIX }}/${{ matrix.service.name }}
          tags: |
            type=ref,event=branch
            type=ref,event=pr
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}
            type=sha,prefix={{branch}}-
            type=raw,value=latest,enable={{is_default_branch}}

      - name: Build and push
        uses: docker/build-push-action@v5
        with:
          context: ${{ matrix.service.context }}
          platforms: linux/amd64,linux/arm64
          push: ${{ github.event_name != 'pull_request' }}
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Run Trivy scan on pushed image
        if: github.event_name != 'pull_request'
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: '${{ env.IMAGE_PREFIX }}/${{ matrix.service.name }}:${{ github.sha }}'
          format: 'sarif'
          output: 'trivy-${{ matrix.service.name }}.sarif'

      - name: Upload Trivy results
        if: github.event_name != 'pull_request'
        uses: github/codeql-action/upload-sarif@v2
        with:
          sarif_file: 'trivy-${{ matrix.service.name }}.sarif'
```

**Acceptance Criteria**:
- [ ] Images build on main merge
- [ ] Images tagged with git SHA and `latest`
- [ ] Multi-arch builds (amd64, arm64)
- [ ] Images pushed to GHCR
- [ ] Build cache speeds up subsequent builds

---

## Sprint 0.4: Infrastructure as Code (Terraform/Pulumi) [Week 2, Days 1-4]

**Duration**: 4 days
**Owner**: DevOps Engineer
**Reference**: `docs/operations/deployment-guide.md` (2,863 lines), ADR-005

### Task 0.4.1: Choose Cloud Provider [CRITICAL DECISION]

**Priority**: CRITICAL
**Effort**: 4 hours (research + decision)
**Dependencies**: None

**Options**:

| Provider | Pros | Cons | Monthly Cost (Est) |
|----------|------|------|-------------------|
| **AWS** | Mature ecosystem, EKS widely adopted, global regions | Complex pricing, IAM complexity | $800-1,200 |
| **GCP** | GKE excellent, simple pricing, BigQuery integration | Smaller ecosystem, fewer regions | $700-1,000 |
| **Azure** | Microsoft integration, hybrid cloud, AKS good | Steeper learning curve | $750-1,100 |

**Recommendation**: AWS (EKS) for production
- **Rationale**:
  - Most widely adopted (easier hiring, more community support)
  - EKS mature and stable
  - RDS for PostgreSQL, ElastiCache for Redis
  - S3 for backups and logs
  - Extensive monitoring and security services

**Decision Process**:
1. Create ADR-006: Cloud Provider Selection
2. Document rationale, alternatives, and consequences
3. Get buy-in from team and stakeholders
4. Set up AWS account with Organization structure:
   - Root account (billing only)
   - Dev account
   - Staging account
   - Production account

**Acceptance Criteria**:
- [ ] ADR-006 written and approved
- [ ] AWS accounts created
- [ ] Billing alerts configured (<$1,000/month for dev)
- [ ] IAM structure planned

---

### Task 0.4.2: Create Terraform Project Structure [HIGH]

**Priority**: HIGH
**Effort**: 2 hours
**Dependencies**: 0.4.1

**Implementation**:

```bash
# Create Terraform directory structure
mkdir -p infra/{modules,environments}
mkdir -p infra/modules/{eks,rds,elasticache,s3,networking}
mkdir -p infra/environments/{dev,staging,prod}
```

**Directory Structure**:
```
infra/
├── README.md                    # Infrastructure documentation
├── .terraform-version           # Terraform version pinning
├── modules/                     # Reusable Terraform modules
│   ├── eks/                     # EKS cluster
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── README.md
│   ├── rds/                     # PostgreSQL RDS
│   ├── elasticache/             # Redis cluster
│   ├── s3/                      # Object storage
│   └── networking/              # VPC, subnets, security groups
└── environments/                # Environment-specific configs
    ├── dev/
    │   ├── main.tf
    │   ├── terraform.tfvars
    │   └── backend.tf
    ├── staging/
    └── prod/
```

**infra/.terraform-version**:
```
1.6.4
```

**infra/modules/eks/main.tf** (excerpt):
```hcl
terraform {
  required_version = ">= 1.6.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}

resource "aws_eks_cluster" "main" {
  name     = var.cluster_name
  role_arn = aws_iam_role.cluster.arn
  version  = var.kubernetes_version

  vpc_config {
    subnet_ids              = var.subnet_ids
    endpoint_private_access = true
    endpoint_public_access  = var.enable_public_access
    public_access_cidrs     = var.public_access_cidrs
  }

  encryption_config {
    provider {
      key_arn = var.kms_key_arn
    }
    resources = ["secrets"]
  }

  enabled_cluster_log_types = ["api", "audit", "authenticator", "controllerManager", "scheduler"]

  tags = merge(
    var.tags,
    {
      Name        = var.cluster_name
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  )

  depends_on = [
    aws_iam_role_policy_attachment.cluster_AmazonEKSClusterPolicy,
    aws_iam_role_policy_attachment.cluster_AmazonEKSVPCResourceController,
  ]
}

resource "aws_eks_node_group" "main" {
  cluster_name    = aws_eks_cluster.main.name
  node_group_name = "${var.cluster_name}-nodegroup"
  node_role_arn   = aws_iam_role.node.arn
  subnet_ids      = var.subnet_ids

  scaling_config {
    desired_size = var.node_desired_size
    max_size     = var.node_max_size
    min_size     = var.node_min_size
  }

  instance_types = var.instance_types
  capacity_type  = var.capacity_type  # ON_DEMAND or SPOT

  update_config {
    max_unavailable = 1
  }

  tags = var.tags

  depends_on = [
    aws_iam_role_policy_attachment.node_AmazonEKSWorkerNodePolicy,
    aws_iam_role_policy_attachment.node_AmazonEKS_CNI_Policy,
    aws_iam_role_policy_attachment.node_AmazonEC2ContainerRegistryReadOnly,
  ]
}

# IAM roles and policies for cluster and nodes
# (Full implementation in actual file)
```

**infra/environments/dev/main.tf**:
```hcl
terraform {
  backend "s3" {
    bucket         = "octollm-terraform-state-dev"
    key            = "dev/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-lock-dev"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Environment = "dev"
      Project     = "OctoLLM"
      ManagedBy   = "Terraform"
    }
  }
}

module "networking" {
  source = "../../modules/networking"

  vpc_cidr             = "10.0.0.0/16"
  availability_zones   = ["us-east-1a", "us-east-1b", "us-east-1c"]
  environment          = "dev"
  enable_nat_gateway   = true
  single_nat_gateway   = true  # Cost optimization for dev
}

module "eks" {
  source = "../../modules/eks"

  cluster_name         = "octollm-dev"
  kubernetes_version   = "1.28"
  subnet_ids           = module.networking.private_subnet_ids
  node_desired_size    = 3
  node_min_size        = 2
  node_max_size        = 5
  instance_types       = ["t3.large"]
  capacity_type        = "ON_DEMAND"
  environment          = "dev"
}

module "rds" {
  source = "../../modules/rds"

  identifier           = "octollm-dev"
  engine_version       = "15.4"
  instance_class       = "db.t3.small"
  allocated_storage    = 20
  max_allocated_storage = 100
  database_name        = "octollm"
  master_username      = "octollm"
  subnet_ids           = module.networking.private_subnet_ids
  vpc_security_group_ids = [module.networking.rds_security_group_id]
  backup_retention_period = 7
  multi_az             = false  # Single AZ for dev
  environment          = "dev"
}

module "elasticache" {
  source = "../../modules/elasticache"

  cluster_id           = "octollm-dev"
  engine_version       = "7.0"
  node_type            = "cache.t3.small"
  num_cache_nodes      = 1
  subnet_ids           = module.networking.private_subnet_ids
  security_group_ids   = [module.networking.redis_security_group_id]
  environment          = "dev"
}

module "s3" {
  source = "../../modules/s3"

  bucket_name          = "octollm-dev-backups"
  enable_versioning    = true
  lifecycle_days       = 30
  environment          = "dev"
}
```

**Acceptance Criteria**:
- [ ] Terraform project structure created
- [ ] Modules defined for all infrastructure components
- [ ] Environment separation (dev, staging, prod)
- [ ] State backend configured (S3 + DynamoDB lock)

---

(Due to length, I'll continue with the remaining tasks in the next message. The Phase 0 TODO is comprehensive and follows the same detailed pattern.)

**Phase 0 TODO Status**: 30% complete (6 of 20+ tasks documented)

Would you like me to continue with the remaining Phase 0 tasks and then proceed to create the other phase TODOs?
