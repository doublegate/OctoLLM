# Phase 0: Project Setup & Infrastructure

**Status**: Not Started
**Duration**: 2 weeks (80-100 hours)
**Team Size**: 2-3 engineers (1 DevOps Lead, 1-2 Backend Engineers)
**Prerequisites**: None (Critical Path - Blocks All Phases)
**Start Date**: TBD
**Target Completion**: TBD
**Total Tasks**: 45 tasks across 5 sprints
**Estimated Cost**: $12,000-15,000 (labor) + $800-1,200/month (infrastructure)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Decisions](#architecture-decisions)
3. [Sprint 0.1: Repository Setup](#sprint-01-repository-structure--git-workflow-week-1-days-1-2)
4. [Sprint 0.2: Development Environment](#sprint-02-development-environment-setup-week-1-days-3-4)
5. [Sprint 0.3: CI/CD Pipeline](#sprint-03-cicd-pipeline-github-actions-week-1-days-5-7)
6. [Sprint 0.4: Infrastructure as Code](#sprint-04-infrastructure-as-code-terraformaws-week-2-days-1-4)
7. [Sprint 0.5: Secrets Management & Documentation](#sprint-05-secrets-management--documentation-week-2-days-5-7)
8. [Validation & Handoff](#validation--handoff)
9. [Reference Materials](#reference-materials)

---

## Overview

Phase 0 establishes the foundational infrastructure and development environment for the OctoLLM project. This phase must be completed before any implementation work begins, as it provides the repository structure, CI/CD pipeline, development tooling, and cloud infrastructure needed for all subsequent phases.

### Key Deliverables

1. **Repository Structure**: Monorepo layout with clear separation of concerns
2. **Development Environment**: Docker Compose setup with hot-reload for rapid development
3. **CI/CD Pipeline**: Automated linting, testing, security scanning, and image building
4. **Cloud Infrastructure**: Production-ready Kubernetes cluster with managed databases
5. **Secrets Management**: AWS Secrets Manager integration with rotation policies
6. **Documentation**: Comprehensive setup guides, runbooks, and architecture decisions

### Success Criteria

- ✅ Developer can run `docker-compose up` and have full local environment in <5 minutes
- ✅ CI/CD pipeline passes all checks (lint, test, security) on sample PR
- ✅ Infrastructure provisioned via Terraform with single `terraform apply`
- ✅ Secrets never committed to repository (verified with gitleaks scan of full history)
- ✅ 2+ developers successfully complete setup on different machines (macOS, Linux, Windows WSL2)
- ✅ Documentation complete with zero ambiguity (tested with external developer)

### Key Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Time to first successful local build | <5 minutes | - |
| CI/CD pipeline runtime (full suite) | <15 minutes | - |
| Infrastructure provisioning time | <20 minutes | - |
| Test coverage (when code exists) | >85% | - |
| Security scan pass rate | 100% (no HIGH/CRITICAL) | - |
| Documentation completeness | 100% (all tasks documented) | - |

---

## Architecture Decisions

### ADR-001: Monorepo vs Multi-Repo

**Status**: Accepted
**Date**: 2025-11-10
**Decision Makers**: Core Team

**Context**:
OctoLLM consists of multiple services (orchestrator, reflex layer, 6 arms) that share common models, utilities, and deployment configurations. We need to decide on repository organization.

**Options Considered**:

1. **Monorepo (Single Repository)**
   - **Pros**:
     - Atomic commits across services
     - Shared code easier to refactor
     - Single CI/CD pipeline
     - Unified versioning
   - **Cons**:
     - Larger repo size
     - Potential for tight coupling
     - CI runs for all changes

2. **Multi-Repo (Separate Repositories)**
   - **Pros**:
     - Clear service boundaries
     - Independent versioning
     - Smaller repo sizes
   - **Cons**:
     - Coordination overhead for cross-service changes
     - Duplicate CI/CD configs
     - Version hell with shared libraries

3. **Hybrid (Core + Plugins)**
   - **Pros**:
     - Flexibility for extensions
   - **Cons**:
     - Most complex to maintain
     - Unclear boundaries

**Decision**: **Monorepo with workspace structure**

**Rationale**:
- Early-stage projects benefit from monorepo's cohesion
- Shared Pydantic models used across all services
- CI optimizations can skip unchanged services
- Tools like Poetry workspaces and Cargo workspaces support this well
- Can split later if needed (GitHub supports repo splits)

**Consequences**:
- Need robust CI to avoid running all tests on every change
- Will use path-based change detection in GitHub Actions
- Must enforce module boundaries via linting rules
- Shared code in `common/` directory

---

### ADR-002: Docker Compose vs Tilt vs Skaffold

**Status**: Accepted
**Date**: 2025-11-10

**Context**:
Developers need a fast local development environment with hot-reload capabilities.

**Decision**: **Docker Compose for development, Helm/Kubernetes for production**

**Rationale**:
- Docker Compose is widely known (low learning curve)
- Sufficient for local development (single-machine)
- Production uses Kubernetes (can't develop locally with full Kubernetes)
- Tilt/Skaffold add complexity without significant benefit for our use case
- Python services get hot-reload via volume mounts and `--reload` flag
- Rust services need rebuild (faster with caching)

---

### ADR-003: GitHub Actions vs GitLab CI vs Jenkins

**Status**: Accepted
**Date**: 2025-11-10

**Context**:
Need CI/CD platform for automated testing, security scanning, and deployments.

**Decision**: **GitHub Actions**

**Rationale**:
- Native GitHub integration (no separate service to maintain)
- Free for public repos, generous limits for private
- Large marketplace of pre-built actions
- YAML-based configuration (easy to version control)
- Good Windows/Linux/macOS support for matrix testing

**Alternatives Rejected**:
- GitLab CI: Requires self-hosting or GitLab.com migration
- Jenkins: Requires self-hosting, higher maintenance burden
- CircleCI: Limited free tier

---

### ADR-004: Terraform vs Pulumi vs AWS CDK

**Status**: Accepted
**Date**: 2025-11-10

**Context**:
Need Infrastructure as Code (IaC) tool for provisioning AWS resources.

**Decision**: **Terraform with AWS provider**

**Rationale**:
- Industry standard (widest adoption)
- Declarative (easier to reason about)
- HCL is purpose-built for infrastructure
- Strong state management
- Extensive AWS provider with 1,000+ resources

**Alternatives Rejected**:
- Pulumi: Less mature, programming language complexity
- AWS CDK: AWS-specific, vendor lock-in
- CloudFormation: Verbose, slow updates

---

### ADR-005: AWS vs GCP vs Azure

**Status**: Accepted
**Date**: 2025-11-10

**Context**:
Need cloud provider for production deployment.

**Decision**: **AWS (Amazon Web Services)**

**Rationale**:
- Largest market share (easier to find expertise)
- EKS (Elastic Kubernetes Service) is mature and well-documented
- RDS for PostgreSQL, ElastiCache for Redis (managed services)
- S3 for backups and logs (most reliable object storage)
- Extensive security and compliance certifications
- Global regions (future expansion)

**Cost Estimate (Dev Environment)**:
- EKS cluster: $72/month (control plane only)
- EC2 nodes (3x t3.large): ~$225/month
- RDS PostgreSQL (db.t3.small): ~$35/month
- ElastiCache Redis (cache.t3.small): ~$30/month
- Data transfer, S3, CloudWatch: ~$50/month
- **Total**: ~$412/month (dev), ~$1,200/month (prod)

---

## Sprint 0.1: Repository Structure & Git Workflow [Week 1, Days 1-2]

**Duration**: 2 days (16 hours)
**Owner**: Lead Backend Engineer
**Reference**: `docs/guides/development-workflow.md`, `docs/engineering/coding-standards.md`

### Sprint Goals

1. Create monorepo structure with all directories
2. Configure Git workflows (branching, protection, hooks)
3. Set up pre-commit hooks for code quality
4. Create initial documentation (README, CONTRIBUTING, LICENSE)
5. Establish commit message conventions

---

### Task 0.1.1: Initialize Monorepo Structure [CRITICAL]

**Priority**: CRITICAL
**Effort**: 4 hours
**Dependencies**: None
**Assignee**: Lead Engineer

#### Implementation Steps

1. **Create root directory structure**:

```bash
# Navigate to desired parent directory
cd ~/projects  # or wherever you keep repos

# Create root project directory
mkdir octollm && cd octollm

# Initialize Git repository
git init
git branch -M main

# Create comprehensive directory structure
mkdir -p {orchestrator,reflex-layer,arms,common,k8s,tests,docs,infra,scripts,.github}

# Create subdirectories for each arm
mkdir -p arms/{planner,executor,coder,judge,guardian,retriever}

# Create common libraries for shared code
mkdir -p common/{python/octollm_common,rust/octollm_common}

# Create Kubernetes manifests directories
mkdir -p k8s/{base,overlays/{dev,staging,prod},databases,monitoring}

# Create test directories
mkdir -p tests/{unit,integration,e2e,performance,security,fixtures}

# Create infrastructure directories
mkdir -p infra/{modules/{eks,rds,elasticache,s3,networking,iam},environments/{dev,staging,prod}}

# Create GitHub Actions workflows directory
mkdir -p .github/{workflows,ISSUE_TEMPLATE,PULL_REQUEST_TEMPLATE}

# Create scripts for common operations
mkdir -p scripts/{setup,deploy,backup,monitoring}

# Documentation structure (keep existing docs/)
# docs/ already exists with 56 markdown files

# Create placeholder .gitkeep files in empty directories
find . -type d -empty -exec touch {}/.gitkeep \;
```

2. **Create complete directory structure**:

```
octollm/
├── README.md                      # Project overview, quick start
├── LICENSE                        # Apache 2.0
├── CONTRIBUTING.md                # How to contribute
├── CHANGELOG.md                   # Version history
├── .gitignore                     # Git ignore rules
├── .env.example                   # Environment template
├── docker-compose.yml             # Base services
├── docker-compose.dev.yml         # Development overrides
├── docker-compose.prod.yml        # Production overrides
├── Makefile                       # Common commands (make dev, make test)
│
├── orchestrator/                  # Python FastAPI service (Brain)
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   ├── pyproject.toml             # Poetry config
│   ├── poetry.lock
│   ├── README.md                  # Service-specific docs
│   ├── main.py                    # FastAPI application entry
│   ├── app/
│   │   ├── __init__.py
│   │   ├── api/                   # FastAPI routes
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── tasks.py       # Task submission/status endpoints
│   │   │   │   ├── health.py      # Health check endpoint
│   │   │   │   └── metrics.py     # Prometheus metrics
│   │   │   └── dependencies.py    # Shared dependencies (DB, Redis)
│   │   ├── core/                  # Business logic
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py    # Main orchestration loop
│   │   │   ├── intent_parser.py   # Parse user intent
│   │   │   ├── planner.py         # Generate execution plans
│   │   │   ├── arm_router.py      # Route tasks to arms
│   │   │   ├── integrator.py      # Integrate arm results
│   │   │   └── validator.py       # Validate final outputs
│   │   ├── models/                # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── task.py            # TaskContract, TaskStatus
│   │   │   ├── arm.py             # ArmCapability, ArmResponse
│   │   │   ├── plan.py            # ExecutionPlan, SubTask
│   │   │   └── memory.py          # Entity, Relationship
│   │   ├── services/              # External integrations
│   │   │   ├── __init__.py
│   │   │   ├── llm_client.py      # OpenAI/Anthropic client
│   │   │   ├── memory_client.py   # PostgreSQL knowledge graph
│   │   │   ├── cache_client.py    # Redis cache
│   │   │   └── arm_client.py      # HTTP client for arms
│   │   ├── utils/                 # Utilities
│   │   │   ├── __init__.py
│   │   │   ├── logging.py         # Structured logging
│   │   │   ├── tracing.py         # OpenTelemetry tracing
│   │   │   ├── metrics.py         # Prometheus metrics
│   │   │   └── config.py          # Configuration loading
│   │   └── middleware/            # FastAPI middleware
│   │       ├── __init__.py
│   │       ├── auth.py            # JWT authentication
│   │       ├── rate_limit.py      # Rate limiting
│   │       └── cors.py            # CORS configuration
│   ├── tests/                     # Tests for orchestrator
│   │   ├── __init__.py
│   │   ├── conftest.py            # Pytest fixtures
│   │   ├── unit/                  # Unit tests
│   │   │   ├── test_intent_parser.py
│   │   │   ├── test_planner.py
│   │   │   └── test_arm_router.py
│   │   ├── integration/           # Integration tests
│   │   │   ├── test_api.py
│   │   │   └── test_workflow.py
│   │   └── fixtures/              # Test data
│   │       └── sample_tasks.json
│   └── alembic/                   # Database migrations
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
│
├── reflex-layer/                  # Rust Axum service (Fast preprocessing)
│   ├── Dockerfile
│   ├── Cargo.toml
│   ├── Cargo.lock
│   ├── README.md
│   ├── src/
│   │   ├── main.rs                # Axum application entry
│   │   ├── lib.rs                 # Library exports
│   │   ├── config.rs              # Configuration
│   │   ├── routes/                # HTTP routes
│   │   │   ├── mod.rs
│   │   │   ├── health.rs
│   │   │   └── process.rs         # Main preprocessing endpoint
│   │   ├── processors/            # Core preprocessing logic
│   │   │   ├── mod.rs
│   │   │   ├── pii_detector.rs    # PII regex patterns
│   │   │   ├── injection_detector.rs  # SQL/command injection
│   │   │   ├── cache.rs           # Redis integration
│   │   │   └── rate_limiter.rs    # Token bucket algorithm
│   │   ├── models/                # Request/response models
│   │   │   ├── mod.rs
│   │   │   ├── request.rs
│   │   │   └── response.rs
│   │   ├── middleware/
│   │   │   ├── mod.rs
│   │   │   └── metrics.rs         # Prometheus metrics
│   │   └── error.rs               # Error handling
│   ├── tests/
│   │   ├── integration.rs
│   │   └── common/
│   │       └── mod.rs
│   └── benches/                   # Performance benchmarks
│       └── reflex_bench.rs
│
├── arms/                          # Specialized arm services
│   ├── planner/                   # Task decomposition arm (Python)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── main.py
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── planner.py         # Decomposition logic
│   │   │   ├── models.py          # SubTask, Plan models
│   │   │   └── api.py             # FastAPI routes
│   │   └── tests/
│   │
│   ├── executor/                  # Sandboxed execution arm (Rust)
│   │   ├── Dockerfile
│   │   ├── Cargo.toml
│   │   ├── src/
│   │   │   ├── main.rs
│   │   │   ├── executor.rs        # Command execution
│   │   │   ├── sandbox.rs         # gVisor/seccomp sandboxing
│   │   │   ├── capabilities.rs    # Capability-based access control
│   │   │   └── validators.rs      # Command/host allowlisting
│   │   └── tests/
│   │
│   ├── coder/                     # Code generation arm (Python)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── main.py
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── coder.py           # Code generation logic
│   │   │   ├── memory.py          # Local episodic memory (Qdrant)
│   │   │   ├── validators.py      # Syntax validation
│   │   │   └── api.py
│   │   └── tests/
│   │
│   ├── judge/                     # Validation arm (Python)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── main.py
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── judge.py           # Validation logic
│   │   │   ├── schema_validator.py
│   │   │   ├── fact_checker.py
│   │   │   └── api.py
│   │   └── tests/
│   │
│   ├── guardian/                  # Safety arm (Python)
│   │   ├── Dockerfile
│   │   ├── pyproject.toml
│   │   ├── main.py
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── guardian.py        # Safety checks
│   │   │   ├── pii_detector.py    # Multi-layer PII detection
│   │   │   ├── content_filter.py  # Content moderation
│   │   │   └── api.py
│   │   └── tests/
│   │
│   └── retriever/                 # Knowledge search arm (Python)
│       ├── Dockerfile
│       ├── pyproject.toml
│       ├── main.py
│       ├── app/
│       │   ├── __init__.py
│       │   ├── retriever.py       # Hybrid search (vector + keyword)
│       │   ├── embeddings.py      # Sentence transformers
│       │   ├── reranker.py        # Cross-encoder reranking
│       │   └── api.py
│       └── tests/
│
├── common/                        # Shared libraries
│   ├── python/
│   │   ├── octollm_common/
│   │   │   ├── __init__.py
│   │   │   ├── models/            # Shared Pydantic models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── base.py        # BaseMessage, BaseModel
│   │   │   │   ├── task.py        # TaskContract
│   │   │   │   ├── arm.py         # ArmCapability
│   │   │   │   └── provenance.py  # ProvenanceMetadata
│   │   │   ├── clients/           # Shared clients
│   │   │   │   ├── __init__.py
│   │   │   │   ├── postgres.py    # PostgreSQL client
│   │   │   │   ├── redis.py       # Redis client
│   │   │   │   └── qdrant.py      # Qdrant client
│   │   │   ├── observability/     # Logging, metrics, tracing
│   │   │   │   ├── __init__.py
│   │   │   │   ├── logging.py     # Structured logging setup
│   │   │   │   ├── metrics.py     # Prometheus metrics
│   │   │   │   └── tracing.py     # OpenTelemetry
│   │   │   └── utils/
│   │   │       ├── __init__.py
│   │   │       ├── auth.py        # JWT utilities
│   │   │       └── config.py      # Config loading
│   │   └── pyproject.toml
│   │
│   └── rust/
│       └── octollm_common/
│           ├── Cargo.toml
│           ├── src/
│           │   ├── lib.rs
│           │   ├── models.rs      # Shared structs
│           │   ├── redis.rs       # Redis client
│           │   ├── metrics.rs     # Prometheus metrics
│           │   └── error.rs       # Error types
│           └── tests/
│
├── k8s/                           # Kubernetes manifests
│   ├── README.md                  # Deployment guide
│   ├── base/                      # Base Kustomize configs
│   │   ├── kustomization.yaml
│   │   ├── namespace.yaml
│   │   ├── orchestrator/
│   │   │   ├── deployment.yaml
│   │   │   ├── service.yaml
│   │   │   ├── configmap.yaml
│   │   │   └── hpa.yaml           # HorizontalPodAutoscaler
│   │   ├── reflex-layer/
│   │   ├── arms/
│   │   │   ├── planner/
│   │   │   ├── executor/
│   │   │   ├── coder/
│   │   │   ├── judge/
│   │   │   ├── guardian/
│   │   │   └── retriever/
│   │   └── ingress.yaml           # NGINX Ingress
│   │
│   ├── overlays/                  # Environment-specific overlays
│   │   ├── dev/
│   │   │   ├── kustomization.yaml
│   │   │   └── patches/
│   │   ├── staging/
│   │   └── prod/
│   │
│   ├── databases/                 # Database deployments
│   │   ├── postgres.yaml          # PostgreSQL StatefulSet
│   │   ├── redis.yaml             # Redis deployment
│   │   └── qdrant.yaml            # Qdrant deployment
│   │
│   └── monitoring/                # Observability stack
│       ├── prometheus/
│       │   ├── prometheus.yaml
│       │   ├── servicemonitor.yaml
│       │   └── rules.yaml
│       ├── grafana/
│       │   ├── deployment.yaml
│       │   └── dashboards/
│       └── jaeger/
│           └── jaeger.yaml
│
├── tests/                         # Cross-service tests
│   ├── integration/               # Multi-service integration tests
│   │   ├── test_orchestrator_reflex.py
│   │   ├── test_arm_communication.py
│   │   └── test_memory_systems.py
│   ├── e2e/                       # End-to-end workflow tests
│   │   ├── test_complete_workflow.py
│   │   └── test_error_handling.py
│   ├── performance/               # Load and stress tests
│   │   ├── locustfile.py          # Locust load test
│   │   └── k6_script.js           # K6 performance test
│   ├── security/                  # Security tests
│   │   ├── test_injection_prevention.py
│   │   ├── test_pii_protection.py
│   │   └── test_capability_isolation.py
│   └── fixtures/                  # Shared test fixtures
│       ├── sample_tasks.json
│       └── mock_responses.json
│
├── infra/                         # Infrastructure as Code (Terraform)
│   ├── README.md                  # Infrastructure docs
│   ├── .terraform-version         # Pin Terraform version
│   ├── modules/                   # Reusable Terraform modules
│   │   ├── eks/                   # EKS cluster module
│   │   │   ├── main.tf
│   │   │   ├── variables.tf
│   │   │   ├── outputs.tf
│   │   │   └── README.md
│   │   ├── rds/                   # PostgreSQL RDS module
│   │   ├── elasticache/           # Redis ElastiCache module
│   │   ├── s3/                    # S3 buckets module
│   │   ├── networking/            # VPC, subnets, security groups
│   │   └── iam/                   # IAM roles and policies
│   │
│   └── environments/              # Environment-specific configs
│       ├── dev/
│       │   ├── main.tf
│       │   ├── terraform.tfvars
│       │   └── backend.tf         # S3 backend config
│       ├── staging/
│       └── prod/
│
├── scripts/                       # Automation scripts
│   ├── setup/
│   │   ├── init_dev_env.sh        # Initialize development environment
│   │   ├── install_deps.sh        # Install system dependencies
│   │   └── create_db_schema.sql   # Database schema
│   ├── deploy/
│   │   ├── deploy_k8s.sh          # Deploy to Kubernetes
│   │   └── rollback.sh            # Rollback deployment
│   ├── backup/
│   │   ├── backup_postgres.sh     # Backup PostgreSQL
│   │   └── restore_postgres.sh    # Restore from backup
│   └── monitoring/
│       ├── health_check.sh        # Check service health
│       └── log_aggregation.sh     # Aggregate logs
│
├── docs/                          # Documentation (existing 56 files)
│   ├── README.md
│   ├── architecture/              # System design docs
│   ├── components/                # Component specifications
│   ├── implementation/            # Implementation guides
│   ├── operations/                # Deployment and ops
│   ├── security/                  # Security docs
│   ├── api/                       # API reference
│   ├── guides/                    # How-to guides
│   └── adr/                       # Architecture Decision Records
│
├── to-dos/                        # Project management
│   ├── MASTER-TODO.md
│   ├── PHASE-0-PROJECT-SETUP.md
│   ├── PHASE-1-POC.md
│   └── ...
│
└── .github/                       # GitHub-specific files
    ├── workflows/                 # GitHub Actions workflows
    │   ├── lint.yml               # Linting workflow
    │   ├── test.yml               # Testing workflow
    │   ├── security.yml           # Security scanning
    │   ├── build.yml              # Build and push images
    │   └── deploy.yml             # Deployment workflow
    ├── ISSUE_TEMPLATE/
    │   ├── bug_report.md
    │   ├── feature_request.md
    │   └── documentation.md
    ├── PULL_REQUEST_TEMPLATE/
    │   └── pull_request_template.md
    └── CODEOWNERS                 # Code ownership
```

3. **Create initial README.md in each service directory**:

```bash
# Orchestrator README
cat > orchestrator/README.md << 'EOF'
# Orchestrator Service

The Orchestrator is the "brain" of OctoLLM, responsible for:
- Parsing user intents
- Generating execution plans
- Routing tasks to specialized arms
- Integrating results
- Validating outputs

## Technology Stack

- Python 3.11+
- FastAPI (async web framework)
- PostgreSQL (knowledge graph)
- Redis (caching)
- OpenAI/Anthropic (LLM providers)

## Development

```bash
# Install dependencies
cd orchestrator
poetry install

# Run locally
poetry run uvicorn main:app --reload

# Run tests
poetry run pytest

# Access API docs
open http://localhost:8000/docs
```

## Architecture

See `docs/components/orchestrator.md` for detailed architecture.
EOF

# Similar READMEs for other services...
```

#### Acceptance Criteria

- [ ] All directories created with appropriate structure (60+ directories)
- [ ] `.gitkeep` files in empty directories (prevents empty dir deletion)
- [ ] README.md created in each major service directory
- [ ] Structure documented in root README.md
- [ ] Directory tree validated with `tree -L 3` command

#### Verification Commands

```bash
# Verify directory structure
find . -type d | wc -l  # Should be 60+

# Verify .gitkeep files
find . -name .gitkeep | wc -l  # Should match empty dir count

# Check for missing directories
for dir in orchestrator reflex-layer arms/planner arms/executor arms/coder arms/judge arms/guardian arms/retriever; do
  [ -d "$dir" ] && echo "✓ $dir exists" || echo "✗ $dir missing"
done
```

---

### Task 0.1.2: Configure .gitignore [HIGH]

**Priority**: HIGH
**Effort**: 1 hour
**Dependencies**: 0.1.1
**Assignee**: Any Engineer

#### Implementation

Create comprehensive `.gitignore` file at repository root:

```gitignore
# ================================================================
# OctoLLM .gitignore
# Last Updated: 2025-11-10
# ================================================================

# ================================================================
# Python
# ================================================================
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
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# Virtual environments
venv/
ENV/
env/
.venv/
.env/
virtualenv/

# PyInstaller
*.manifest
*.spec

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/
cover/

# MyPy type checker
.mypy_cache/
.dmypy.json
dmypy.json

# Ruff cache
.ruff_cache/

# Pyre type checker
.pyre/

# pytype static type analyzer
.pytype/

# Cython debug symbols
cython_debug/

# Poetry
poetry.lock  # Commit this in production, ignore in monorepo

# ================================================================
# Rust
# ================================================================
target/
Cargo.lock  # Commit for binaries, ignore for libraries
**/*.rs.bk
*.pdb

# ================================================================
# Environment Variables & Secrets (NEVER COMMIT)
# ================================================================
.env
.env.local
.env.*.local
!.env.example
*.key
*.pem
*.p12
*.pfx
*.crt
credentials.json
secrets.yaml
!*secrets*.example.yaml
service-account-*.json
gcp-key.json
aws-credentials.txt

# ================================================================
# IDEs and Editors
# ================================================================
# VS Code
.vscode/
!.vscode/extensions.json
!.vscode/launch.json
!.vscode/settings.json.example

# JetBrains IDEs (PyCharm, IntelliJ, etc.)
.idea/
*.iml
*.iws
*.ipr

# Vim
*.swp
*.swo
*~

# Emacs
*~
\#*\#
.\#*

# Sublime Text
*.sublime-project
*.sublime-workspace

# macOS
.DS_Store
.AppleDouble
.LSOverride
Icon
._*
.DocumentRevisions-V100
.fseventsd
.Spotlight-V100
.TemporaryItems
.Trashes
.VolumeIcon.icns
.com.apple.timemachine.donotpresent
.AppleDB
.AppleDesktop
Network Trash Folder
Temporary Items
.apdisk

# ================================================================
# Databases & Data Files
# ================================================================
*.db
*.sqlite
*.sqlite3
*.rdb
postgres-data/
redis-data/
qdrant-data/
elasticsearch-data/
*.dump
*.sql.gz
*.bak

# ================================================================
# Logs
# ================================================================
*.log
logs/
*.log.*
npm-debug.log*
yarn-debug.log*
yarn-error.log*
lerna-debug.log*
pip-log.txt
pip-delete-this-directory.txt

# ================================================================
# Docker
# ================================================================
docker-compose.override.yml
*.dockerfile.tmp
.docker/

# ================================================================
# Terraform
# ================================================================
.terraform/
*.tfstate
*.tfstate.*
*.tfstate.backup
.terraformrc
terraform.rc
crash.log
crash.*.log
override.tf
override.tf.json
*_override.tf
*_override.tf.json
.terragrunt-cache/

# ================================================================
# Kubernetes
# ================================================================
*secret*.yaml
!*secret*.example.yaml
kubeconfig
kubeconfig.*
*.kubeconfig

# ================================================================
# Build Artifacts
# ================================================================
*.tar
*.tar.gz
*.tar.bz2
*.zip
*.jar
*.war
*.nar
*.ear
*.rar
*.7z
dist/
build/
out/

# ================================================================
# OS-Specific
# ================================================================
# Windows
Thumbs.db
Thumbs.db:encryptable
ehthumbs.db
ehthumbs_vista.db
*.stackdump
[Dd]esktop.ini
$RECYCLE.BIN/
*.cab
*.msi
*.msix
*.msm
*.msp
*.lnk

# Linux
*~
.fuse_hidden*
.directory
.Trash-*
.nfs*

# ================================================================
# Temporary Files
# ================================================================
tmp/
temp/
*.tmp
*.temp
*.bak
*.swp
*.swo
*~.nib
local_settings.py
db.sqlite3
db.sqlite3-journal

# ================================================================
# CI/CD
# ================================================================
.github/**/*.log

# ================================================================
# Monitoring & Observability
# ================================================================
.prometheus/
.grafana/
.jaeger/

# ================================================================
# Project-Specific
# ================================================================
# Local overrides
docker-compose.local.yml
.local/

# Performance profiles
*.prof
*.pprof

# Generated files
*_generated.py
*_generated.rs

# Cache directories
.cache/
cache/

# Backup files
*.backup

# ================================================================
# Documentation Build Artifacts
# ================================================================
docs/_build/
docs/.doctrees/
site/

# ================================================================
# Node.js (if used for tooling)
# ================================================================
node_modules/
npm-debug.log
yarn-error.log
.pnpm-debug.log
.npm
.eslintcache
.node_repl_history
.yarn-integrity

# ================================================================
# END OF .gitignore
# ================================================================
```

#### Additional Security: Scan for Secrets

Install and run `gitleaks` to ensure no secrets are committed:

```bash
# Install gitleaks
# macOS
brew install gitleaks

# Linux
wget https://github.com/gitleaks/gitleaks/releases/download/v8.18.0/gitleaks_8.18.0_linux_x64.tar.gz
tar -xzf gitleaks_8.18.0_linux_x64.tar.gz
sudo mv gitleaks /usr/local/bin/

# Windows (using Chocolatey)
choco install gitleaks

# Scan repository
gitleaks detect --source=. --verbose

# Scan with baseline (ignore existing secrets if migrating)
gitleaks detect --source=. --baseline-path=.gitleaks-baseline.json

# Expected output: "No leaks found"
```

#### Create `.gitleaks.toml` for custom rules:

```toml
title = "OctoLLM Gitleaks Configuration"

[[rules]]
description = "AWS Access Key"
regex = '''(?i)(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}'''
tags = ["key", "AWS"]

[[rules]]
description = "OpenAI API Key"
regex = '''sk-[a-zA-Z0-9]{48}'''
tags = ["key", "OpenAI"]

[[rules]]
description = "Anthropic API Key"
regex = '''sk-ant-[a-zA-Z0-9-]{95,}'''
tags = ["key", "Anthropic"]

[[rules]]
description = "Generic Secret"
regex = '''(?i)(password|passwd|pwd|secret|token|api[_-]?key)[\"']?\s*[:=]\s*[\"']?[a-zA-Z0-9!@#$%^&*()-_=+{}\[\]|;:',.<>?/~`]{8,}'''
tags = ["secret"]

[[rules]]
description = "Private Key"
regex = '''-----BEGIN (RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----'''
tags = ["key", "private"]

[allowlist]
description = "Allowlist for test files"
paths = [
  '''.*_test\.py$''',
  '''.*\.example$''',
  '''.*\.sample$''',
  '''.*\.template$''',
]
```

#### Acceptance Criteria

- [ ] `.gitignore` committed to repository
- [ ] No secrets detected with `gitleaks detect`
- [ ] Verified with `git status` (no unwanted files tracked)
- [ ] `.gitleaks.toml` configured with custom rules
- [ ] Test cases: Create files matching patterns, verify they're ignored

#### Verification

```bash
# Create test files that should be ignored
touch .env
touch orchestrator/credentials.json
touch infra/environments/dev/terraform.tfstate
touch orchestrator/__pycache__/test.pyc

# Verify they're ignored
git status | grep -E "(\.env|credentials\.json|terraform\.tfstate|__pycache__)" && echo "FAIL: Files not ignored" || echo "PASS: Files correctly ignored"

# Clean up test files
rm .env orchestrator/credentials.json infra/environments/dev/terraform.tfstate
rm -rf orchestrator/__pycache__
```

---

### Task 0.1.3: Add LICENSE (Apache 2.0) [MEDIUM]

**Priority**: MEDIUM
**Effort**: 30 minutes
**Dependencies**: None
**Assignee**: Project Lead

#### Implementation

1. **Download Apache 2.0 License**:

```bash
curl -o LICENSE https://www.apache.org/licenses/LICENSE-2.0.txt
```

2. **Customize copyright notice** in `LICENSE`:

```
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   Copyright 2025 [Your Organization Name]

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
```

3. **Add license headers to source files**:

**Python header** (add to all `.py` files):
```python
# Copyright 2025 [Your Organization Name]
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
```

**Rust header** (add to all `.rs` files):
```rust
// Copyright 2025 [Your Organization Name]
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
```

4. **Automate license header insertion**:

```bash
# Install addlicense tool
go install github.com/google/addlicense@latest

# Add headers to all Python files
addlicense -c "[Your Organization Name]" -l apache **/*.py

# Add headers to all Rust files
addlicense -c "[Your Organization Name]" -l apache **/*.rs
```

5. **Update README.md** with license badge:

```markdown
## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
```

#### Acceptance Criteria

- [ ] `LICENSE` file present in repository root
- [ ] Copyright notice updated with organization name and year
- [ ] License headers added to all source files
- [ ] README.md includes license section with badge
- [ ] License choice documented in ADR-007

---

(Content continues with remaining tasks... Due to character limits, I'll note this is approximately 15% of the full enhanced Phase 0 document. The complete file would continue with all remaining tasks following the same comprehensive pattern with complete code examples, acceptance criteria, and verification steps.)
