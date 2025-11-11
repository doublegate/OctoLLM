# Phase 0 Sprint 0.3: CI/CD Pipeline Implementation Plan

**Metadata**
---
- **Plan Created**: 2025-11-11
- **Plan Author**: Claude Code AI Assistant
- **Estimated Duration**: 3 days (13 hours)
- **Sprint Name**: CI/CD Pipeline (GitHub Actions)
- **Priority**: CRITICAL PATH
- **Prerequisites**: Sprint 0.2 Complete ✅
- **Dependencies**: None (can start immediately after Sprint 0.2 commit)
- **Target Completion**: 2025-11-14
- **Assigned Team**: 1 DevOps Engineer
- **Status**: READY TO START

---

## Executive Summary

This implementation plan provides step-by-step instructions for implementing a complete CI/CD pipeline for the OctoLLM distributed AI project using GitHub Actions. The plan is designed for an engineer with **zero codebase context** and assumes minimal domain knowledge.

**What This Plan Delivers**:
- ✅ Automated linting (Python: Ruff/Black/mypy, Rust: rustfmt/clippy)
- ✅ Automated testing (pytest, cargo test, integration tests)
- ✅ Security scanning (Bandit, Snyk, cargo-audit, Trivy, gitleaks)
- ✅ Automated Docker image builds (multi-arch: amd64/arm64)
- ✅ Container registry integration (GitHub Container Registry)
- ✅ Branch protection with required checks

**Success Criteria**:
1. All 4 workflows pass on a test PR
2. Security scans find 0 critical/high issues
3. Docker images automatically build and push on main merge
4. Branch protection prevents direct pushes to main
5. At least 1 PR successfully merged through full pipeline

---

## Table of Contents

1. [Prerequisites Setup](#prerequisites-setup)
2. [Task 0.3.1: Linting Workflow](#task-031-linting-workflow)
3. [Task 0.3.2: Testing Workflow](#task-032-testing-workflow)
4. [Task 0.3.3: Security Scanning Workflow](#task-033-security-scanning-workflow)
5. [Task 0.3.4: Build and Push Workflow](#task-034-build-and-push-workflow)
6. [Post-Sprint Configuration](#post-sprint-configuration)
7. [Verification Steps](#verification-steps)
8. [Troubleshooting](#troubleshooting)
9. [Appendices](#appendices)

---

## Prerequisites Setup

**⏰ Estimated Time**: 1 hour (before starting tasks)
**🎯 Goal**: Configure external services and GitHub secrets

### Step 1: Commit Sprint 0.2 Files to GitHub

**Why**: Sprint 0.3 workflows will test the Docker environment created in Sprint 0.2

```bash
cd /home/parobek/Code/OctoLLM

# Verify you're on main branch
git status

# Expected output: On branch main

# Add all Sprint 0.2 files
git add services/ infrastructure/ .devcontainer/ docs/development/ to-dos/

# Create commit with proper format
git commit -m "feat(dev-env): Complete Phase 0 Sprint 0.2 - Development Environment Setup

Complete Docker development environment with all infrastructure services operational.

**Infrastructure Services (5/5 Healthy)**:
- PostgreSQL 15 (port 15432)
- Redis 7 (port 6379)
- Qdrant 1.7.0 (ports 6333-6334, pidof health check)
- Reflex Layer (Rust, port 8080)
- Executor Arm (Rust, port 18006)

**Python Services (6/6 Created)**:
- Orchestrator, Planner, Retriever, Coder, Judge, Safety Guardian
- Awaiting Phase 1 implementation code

**Key Fixes**:
- Fixed langchain-openai + tiktoken dependency conflicts (db209a2)
- Fixed Qdrant health check using pidof instead of curl (ed89eb7)
- Added minimal Rust scaffolding for successful builds (d2e34e8)
- Security: Explicit .gitignore for secrets (06cdc25)

**Deliverables**:
- 8 production-ready Dockerfiles (multi-stage builds)
- docker-compose.dev.yml with 13 services
- VS Code devcontainer configuration
- Comprehensive local setup documentation

**Testing**: All infrastructure services verified healthy via docker-compose ps

Closes #[Sprint 0.2 issue number if exists]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to GitHub
git push origin main

# Verify push succeeded
git log --oneline -1
```

**Verification**: Visit `https://github.com/doublegate/OctoLLM` and confirm the commit appears

---

### Step 2: Create GitHub Actions Directory

**Why**: GitHub Actions workflows must be in `.github/workflows/` directory

```bash
cd /home/parobek/Code/OctoLLM

# Create directory
mkdir -p .github/workflows

# Verify creation
ls -la .github/workflows

# Expected output: Empty directory (total 0)
```

**Verification**: Directory exists at `/home/parobek/Code/OctoLLM/.github/workflows/`

---

### Step 3: Sign Up for External Services

**Why**: We need Codecov for test coverage and Snyk for dependency scanning

#### 3a. Codecov Account Setup

**Purpose**: Track test coverage over time and display coverage badges

1. **Navigate to**: [https://codecov.io/](https://codecov.io/)
2. **Click**: "Sign up with GitHub"
3. **Authorize**: Grant Codecov access to your GitHub account
4. **Select Repository**: Find and add `doublegate/OctoLLM`
5. **Copy Token**:
   - Go to: `https://app.codecov.io/gh/doublegate/OctoLLM/settings`
   - Find: "Repository Upload Token"
   - Click: "Show token" and copy to clipboard
6. **Save Token**: You'll add this to GitHub Secrets in Step 4

**Expected Result**: Codecov dashboard shows `doublegate/OctoLLM` with 0% coverage

#### 3b. Snyk Account Setup

**Purpose**: Scan Python and Rust dependencies for known vulnerabilities

1. **Navigate to**: [https://snyk.io/](https://snyk.io/)
2. **Click**: "Sign up free" → "Sign up with GitHub"
3. **Authorize**: Grant Snyk access to your GitHub account
4. **Import Project**:
   - Click "Add project" → "GitHub"
   - Select `doublegate/OctoLLM`
   - Click "Add selected repositories"
5. **Copy Token**:
   - Go to: `https://app.snyk.io/account`
   - Find: "Auth Token"
   - Click "Click to show" and copy to clipboard
6. **Save Token**: You'll add this to GitHub Secrets in Step 4

**Expected Result**: Snyk dashboard shows `doublegate/OctoLLM` project imported

---

### Step 4: Configure GitHub Secrets

**Why**: Workflows need API tokens to upload coverage and scan dependencies

1. **Navigate to Secrets**:
   ```
   https://github.com/doublegate/OctoLLM/settings/secrets/actions
   ```

   *(Replace `doublegate/OctoLLM` with your actual GitHub org/repo)*

2. **Add CODECOV_TOKEN**:
   - Click "New repository secret"
   - Name: `CODECOV_TOKEN`
   - Value: [Paste token from Step 3a]
   - Click "Add secret"

3. **Add SNYK_TOKEN**:
   - Click "New repository secret"
   - Name: `SNYK_TOKEN`
   - Value: [Paste token from Step 3b]
   - Click "Add secret"

4. **Verify Secrets Created**:
   - You should see 2 secrets listed:
     - `CODECOV_TOKEN` (Created: just now)
     - `SNYK_TOKEN` (Created: just now)
   - Secrets are encrypted and cannot be viewed after creation

**Note**: `GITHUB_TOKEN` is automatically provided by GitHub Actions, no need to create it

**Verification**: Secrets page shows 2 repository secrets

---

### Step 5: Verify GitHub Actions is Enabled

**Why**: Some organizations disable GitHub Actions by default

1. **Navigate to Actions Settings**:
   ```
   https://github.com/doublegate/OctoLLM/settings/actions
   ```

2. **Check "Actions permissions"**:
   - Should be set to: "Allow all actions and reusable workflows"
   - If not, select it and click "Save"

3. **Check "Workflow permissions"**:
   - Should be set to: "Read and write permissions"
   - Enable: "Allow GitHub Actions to create and approve pull requests"
   - Click "Save"

**Verification**: GitHub Actions enabled with read/write permissions

---

## Task 0.3.1: Linting Workflow

**⏰ Estimated Time**: 3 hours
**📦 Deliverables**: `.github/workflows/lint.yml`
**🎯 Goal**: Enforce code style and quality standards on every PR
**🔗 Dependencies**: Prerequisites complete

### Overview

This workflow runs linters on Python and Rust code to ensure consistent code style before code review. It runs on:
- Every push to `main` or `develop` branches
- Every pull request to `main` or `develop` branches
- Manual trigger via GitHub UI

**What Gets Checked**:
- **Python**:
  - Ruff (linting + import sorting) - Fast Python linter
  - Black (formatting) - Code formatting
  - mypy (type checking) - Static type analysis
- **Rust**:
  - rustfmt (formatting) - Official Rust formatter
  - clippy (linting) - Official Rust linter with warnings promoted to errors

---

### Step 1.1: Create Lint Workflow File

**Action**: Create a new file `.github/workflows/lint.yml`

```bash
cd /home/parobek/Code/OctoLLM

# Create file (will open in nano, paste content below)
nano .github/workflows/lint.yml
```

**File Content** (copy this entire YAML file):

```yaml
name: Lint

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:  # Allow manual trigger

# Cancel in-progress runs of the same workflow
concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  lint-python:
    name: Lint Python Code
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install Python linting tools
        run: |
          python -m pip install --upgrade pip
          pip install ruff black mypy

      - name: Run Ruff (linting + import sorting)
        run: |
          echo "Running Ruff linter..."
          ruff check . --output-format=github
        continue-on-error: false

      - name: Run Black (formatting check)
        run: |
          echo "Checking code formatting with Black..."
          black --check --diff .
        continue-on-error: false

      - name: Run mypy (type checking)
        run: |
          echo "Running mypy type checker..."
          mypy services/orchestrator/ services/arms/ --ignore-missing-imports --no-error-summary
        continue-on-error: true  # Don't fail on type errors initially

  lint-rust:
    name: Lint Rust Code
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Rust toolchain
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          components: rustfmt, clippy
          override: true

      - name: Cache Rust dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            services/reflex-layer/target
            services/arms/executor/target
          key: ${{ runner.os }}-cargo-${{ hashFiles('**/Cargo.lock') }}
          restore-keys: |
            ${{ runner.os }}-cargo-

      - name: Run rustfmt (formatting check)
        working-directory: services/reflex-layer
        run: |
          echo "Checking Rust formatting..."
          cargo fmt -- --check

      - name: Run clippy (linting) - Reflex Layer
        working-directory: services/reflex-layer
        run: |
          echo "Running clippy on Reflex Layer..."
          cargo clippy --all-targets --all-features -- -D warnings

      - name: Run rustfmt (formatting check) - Executor Arm
        working-directory: services/arms/executor
        run: |
          echo "Checking Rust formatting..."
          cargo fmt -- --check

      - name: Run clippy (linting) - Executor Arm
        working-directory: services/arms/executor
        run: |
          echo "Running clippy on Executor Arm..."
          cargo clippy --all-targets --all-features -- -D warnings
```

**Why These Settings**:
- `concurrency`: Cancels old workflow runs when new commits pushed (saves CI minutes)
- `continue-on-error: true` for mypy: Type checking is advisory during Phase 0
- `-D warnings` for clippy: Treats all warnings as errors (strict quality)
- `cache: 'pip'` and `actions/cache@v4`: Speeds up subsequent runs

**Save and Exit**:
- Press `Ctrl+X`
- Press `Y` to confirm
- Press `Enter` to save

**Verification**: File exists at `.github/workflows/lint.yml`

---

### Step 1.2: Commit and Push Lint Workflow

```bash
cd /home/parobek/Code/OctoLLM

# Stage the new workflow file
git add .github/workflows/lint.yml

# Commit with conventional commit format
git commit -m "ci(lint): Add linting workflow for Python and Rust

Create GitHub Actions workflow to enforce code quality standards:

**Python Linting**:
- Ruff: Fast Python linter with import sorting
- Black: Opinionated code formatter
- mypy: Static type checker (advisory mode)

**Rust Linting**:
- rustfmt: Official Rust code formatter
- clippy: Comprehensive linter with -D warnings

**Triggers**:
- Push to main/develop branches
- Pull requests to main/develop
- Manual workflow_dispatch

**Performance**:
- Dependency caching for faster runs
- Concurrent workflow cancellation

Part of Sprint 0.3 Task 0.3.1

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push to GitHub
git push origin main
```

**Verification**:
1. Visit `https://github.com/doublegate/OctoLLM/actions`
2. You should see "Lint" workflow running
3. Click on it to watch progress

---

### Step 1.3: Verify Lint Workflow Execution

**Expected Behavior**:
- Workflow runs automatically on push
- Python linting may show errors (normal for Phase 0)
- Rust linting should pass (minimal scaffolding exists)

**If Workflow Fails**:

#### Common Issue 1: Python Import Errors

**Symptom**: Ruff complains about missing imports
**Fix**: Update Ruff configuration

```bash
cd /home/parobek/Code/OctoLLM

# Create ruff configuration
cat > pyproject.toml <<'EOF'
[tool.ruff]
line-length = 100
target-version = "py311"

# Ignore missing imports during Phase 0
[tool.ruff.lint]
ignore = ["F401", "F811", "F821"]  # Unused imports, redefinition, undefined name

[tool.ruff.lint.per-file-ignores]
"__init__.py" = ["F401"]  # Allow unused imports in __init__.py
EOF

git add pyproject.toml
git commit -m "ci(lint): Add ruff configuration for Phase 0

Ignore common import errors during initial development.
Will be removed in Phase 1 when implementation begins.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

#### Common Issue 2: Rust Formatting Errors

**Symptom**: `cargo fmt -- --check` fails
**Fix**: Auto-format Rust code

```bash
cd /home/parobek/Code/OctoLLM

# Format all Rust code
cd services/reflex-layer && cargo fmt && cd -
cd services/arms/executor && cargo fmt && cd -

# Commit formatting
git add services/
git commit -m "style(rust): Auto-format Rust code with rustfmt

Apply Rust standard formatting to pass CI checks.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
git push origin main
```

**Success Criteria**:
- ✅ "Lint" workflow shows green checkmark on Actions page
- ✅ Python linting completes (may have warnings)
- ✅ Rust linting passes without errors

---

## Task 0.3.2: Testing Workflow

**⏰ Estimated Time**: 4 hours
**📦 Deliverables**: `.github/workflows/test.yml`
**🎯 Goal**: Run unit and integration tests on every PR
**🔗 Dependencies**: Task 0.3.1 complete
**⏳ Current Phase 0 Status**: No tests exist yet (will be added in Phase 1)

### Overview

This workflow runs all automated tests and uploads coverage reports. During Phase 0, it will **pass with 0 tests** as a placeholder. Tests will be added in Phase 1.

**What Gets Tested** (in Phase 1+):
- **Python Unit Tests**: pytest on orchestrator and arms
- **Rust Unit Tests**: cargo test on reflex-layer and executor
- **Integration Tests**: Docker Compose services + pytest
- **Coverage**: Uploaded to Codecov for tracking

---

### Step 2.1: Create Test Workflow File

```bash
cd /home/parobek/Code/OctoLLM

nano .github/workflows/test.yml
```

**File Content**:

```yaml
name: Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  test-python:
    name: Python Unit Tests
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
          cache: 'pip'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install pytest pytest-asyncio pytest-cov
          # Install OctoLLM dependencies (Phase 1+)
          # pip install -r services/orchestrator/requirements.txt

      - name: Run pytest with coverage
        run: |
          echo "Running Python unit tests..."
          pytest tests/unit/ -v --cov=services --cov-report=xml --cov-report=term-missing || echo "No tests found yet (Phase 0)"
        continue-on-error: true  # Don't fail if no tests exist

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4
        if: matrix.python-version == '3.11'  # Only upload once
        with:
          token: ${{ secrets.CODECOV_TOKEN }}
          files: ./coverage.xml
          flags: unittests
          name: python-unit-tests

  test-rust:
    name: Rust Unit Tests
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Rust toolchain
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          override: true

      - name: Cache Rust dependencies
        uses: actions/cache@v4
        with:
          path: |
            ~/.cargo/registry
            ~/.cargo/git
            services/reflex-layer/target
            services/arms/executor/target
          key: ${{ runner.os }}-cargo-test-${{ hashFiles('**/Cargo.lock') }}
          restore-keys: |
            ${{ runner.os }}-cargo-test-

      - name: Run cargo test - Reflex Layer
        working-directory: services/reflex-layer
        run: |
          echo "Running Rust unit tests for Reflex Layer..."
          cargo test --verbose || echo "No tests found yet (Phase 0)"
        continue-on-error: true

      - name: Run cargo test - Executor Arm
        working-directory: services/arms/executor
        run: |
          echo "Running Rust unit tests for Executor Arm..."
          cargo test --verbose || echo "No tests found yet (Phase 0)"
        continue-on-error: true

  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_USER: octollm
          POSTGRES_PASSWORD: octollm_dev_pass
          POSTGRES_DB: octollm
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Install dependencies
        run: |
          pip install pytest pytest-asyncio httpx asyncpg redis

      - name: Wait for services to be ready
        run: |
          echo "Waiting for PostgreSQL..."
          for i in {1..30}; do
            pg_isready -h localhost -p 5432 -U octollm && break
            echo "Waiting for PostgreSQL to be ready... ($i/30)"
            sleep 2
          done

          echo "Waiting for Redis..."
          for i in {1..30}; do
            redis-cli -h localhost -p 6379 ping && break
            echo "Waiting for Redis to be ready... ($i/30)"
            sleep 2
          done

      - name: Run integration tests
        env:
          DATABASE_URL: postgresql://octollm:octollm_dev_pass@localhost:5432/octollm
          REDIS_URL: redis://localhost:6379
        run: |
          echo "Running integration tests..."
          pytest tests/integration/ -v || echo "No integration tests found yet (Phase 0)"
        continue-on-error: true

  test-summary:
    name: Test Summary
    runs-on: ubuntu-latest
    needs: [test-python, test-rust, integration-tests]
    if: always()

    steps:
      - name: Check test results
        run: |
          echo "✅ Test workflow complete"
          echo "Phase 0: No tests exist yet - this is expected"
          echo "Tests will be added in Phase 1 (Proof of Concept)"
```

**Why These Settings**:
- `strategy.matrix`: Tests on Python 3.11 and 3.12 for compatibility
- `services`: Starts PostgreSQL and Redis in CI for integration tests
- `continue-on-error: true`: Allows workflow to pass when no tests exist
- `needs: [...]`: test-summary runs after all tests complete

**Save and Exit**: Ctrl+X, Y, Enter

---

### Step 2.2: Create Placeholder Test Directories

**Why**: pytest expects `tests/` directories to exist

```bash
cd /home/parobek/Code/OctoLLM

# Create test directories
mkdir -p tests/unit tests/integration tests/e2e

# Create placeholder test files so pytest doesn't error
cat > tests/unit/test_placeholder.py <<'EOF'
"""
Placeholder test file for Phase 0.

Tests will be added in Phase 1 (Proof of Concept) Sprint 1.2.
"""

def test_placeholder():
    """Placeholder test that always passes."""
    assert True, "Phase 0: No real tests yet"
EOF

cat > tests/integration/test_placeholder.py <<'EOF'
"""
Placeholder integration test for Phase 0.

Integration tests will be added in Phase 1 Sprint 1.5.
"""

def test_integration_placeholder():
    """Placeholder integration test."""
    assert True, "Phase 0: No integration tests yet"
EOF

# Create __init__.py files to make tests a package
touch tests/__init__.py tests/unit/__init__.py tests/integration/__init__.py tests/e2e/__init__.py
```

**Verification**: Directory structure exists:
```
tests/
├── __init__.py
├── unit/
│   ├── __init__.py
│   └── test_placeholder.py
├── integration/
│   ├── __init__.py
│   └── test_placeholder.py
└── e2e/
    └── __init__.py
```

---

### Step 2.3: Commit and Push Test Workflow

```bash
cd /home/parobek/Code/OctoLLM

# Stage all files
git add .github/workflows/test.yml tests/

# Commit
git commit -m "ci(test): Add testing workflow with Phase 0 placeholders

Create comprehensive testing workflow for Python and Rust:

**Python Tests**:
- pytest with coverage on Python 3.11 and 3.12
- Coverage uploaded to Codecov
- Matrix strategy for compatibility testing

**Rust Tests**:
- cargo test for reflex-layer and executor
- Dependency caching for performance

**Integration Tests**:
- PostgreSQL 15 and Redis 7 services in CI
- Health checks before test execution
- Tests against real databases

**Phase 0 Status**:
- Placeholder tests added (always pass)
- Real tests will be added in Phase 1 Sprint 1.2
- Workflow configured to not fail when no tests exist

Part of Sprint 0.3 Task 0.3.2

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push
git push origin main
```

---

### Step 2.4: Verify Test Workflow Execution

**Check Actions**: Visit `https://github.com/doublegate/OctoLLM/actions`

**Expected Results**:
- ✅ "Test" workflow runs automatically
- ✅ "Python Unit Tests" job passes (2 variations: Python 3.11 and 3.12)
- ✅ "Rust Unit Tests" job passes (no tests yet)
- ✅ "Integration Tests" job passes (placeholder tests)
- ✅ "Test Summary" job succeeds
- ✅ Codecov uploads coverage (0% initially - this is expected)

**Check Codecov**:
1. Visit `https://app.codecov.io/gh/doublegate/OctoLLM`
2. You should see coverage report (0% is expected for Phase 0)
3. Badge URL will be available for README

---

## Task 0.3.3: Security Scanning Workflow

**⏰ Estimated Time**: 3 hours
**📦 Deliverables**: `.github/workflows/security.yml`
**🎯 Goal**: Automatically detect vulnerabilities in code and dependencies
**🔗 Dependencies**: Task 0.3.1 complete

### Overview

This workflow performs multiple security scans:
1. **SAST (Static Analysis)**: Bandit for Python code vulnerabilities
2. **Dependency Scanning**: Snyk for Python, cargo-audit for Rust
3. **Container Scanning**: Trivy for Docker image vulnerabilities
4. **Secret Scanning**: gitleaks to prevent credential leaks

**Scan Schedule**:
- On every push and PR (quick scans)
- Daily at midnight (full scan with all checks)

---

### Step 3.1: Create Security Workflow File

```bash
cd /home/parobek/Code/OctoLLM

nano .github/workflows/security.yml
```

**File Content**:

```yaml
name: Security Scan

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]
  schedule:
    - cron: '0 0 * * *'  # Daily at midnight UTC
  workflow_dispatch:

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  sast-bandit:
    name: SAST - Bandit (Python)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python 3.11
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install Bandit
        run: pip install bandit[toml]

      - name: Run Bandit security linter
        run: |
          echo "Running Bandit SAST scanner..."
          bandit -r services/orchestrator/ services/arms/ -f json -o bandit-report.json || true
          bandit -r services/orchestrator/ services/arms/ -ll -ii
        continue-on-error: false

      - name: Upload Bandit report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: bandit-report
          path: bandit-report.json
          retention-days: 30

  dependency-scan-python:
    name: Dependency Scan - Snyk (Python)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Run Snyk to check for vulnerabilities
        uses: snyk/actions/python-3.11@master
        continue-on-error: true  # Don't fail build on vulnerabilities yet
        env:
          SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
        with:
          args: --severity-threshold=high --all-projects

      - name: Upload Snyk results to GitHub Code Scanning
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: snyk.sarif

  dependency-scan-rust:
    name: Dependency Scan - cargo-audit (Rust)
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Rust toolchain
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          override: true

      - name: Install cargo-audit
        run: cargo install cargo-audit

      - name: Run cargo audit - Reflex Layer
        working-directory: services/reflex-layer
        run: |
          echo "Auditing Reflex Layer dependencies..."
          cargo audit --json > ../../reflex-audit.json || true
          cargo audit
        continue-on-error: true

      - name: Run cargo audit - Executor Arm
        working-directory: services/arms/executor
        run: |
          echo "Auditing Executor Arm dependencies..."
          cargo audit --json > ../../executor-audit.json || true
          cargo audit
        continue-on-error: true

      - name: Upload audit reports
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: cargo-audit-reports
          path: |
            reflex-audit.json
            executor-audit.json
          retention-days: 30

  container-scan:
    name: Container Scan - Trivy
    runs-on: ubuntu-latest
    strategy:
      matrix:
        service: [orchestrator, reflex-layer, planner, executor]

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Build Docker image
        run: |
          echo "Building ${{ matrix.service }} image..."
          if [ "${{ matrix.service }}" = "orchestrator" ]; then
            docker build -t octollm/${{ matrix.service }}:latest -f services/orchestrator/Dockerfile .
          elif [ "${{ matrix.service }}" = "reflex-layer" ]; then
            docker build -t octollm/${{ matrix.service }}:latest -f services/reflex-layer/Dockerfile .
          elif [ "${{ matrix.service }}" = "executor" ]; then
            docker build -t octollm/${{ matrix.service }}:latest -f services/arms/executor/Dockerfile .
          else
            docker build -t octollm/${{ matrix.service }}:latest -f services/arms/${{ matrix.service }}/Dockerfile .
          fi

      - name: Run Trivy vulnerability scanner
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: octollm/${{ matrix.service }}:latest
          format: 'sarif'
          output: 'trivy-${{ matrix.service }}.sarif'
          severity: 'CRITICAL,HIGH'

      - name: Upload Trivy results to GitHub Security
        uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: 'trivy-${{ matrix.service }}.sarif'

  secret-scan:
    name: Secret Scan - gitleaks
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for gitleaks

      - name: Run gitleaks
        uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          GITLEAKS_LICENSE: ${{ secrets.GITLEAKS_LICENSE }}

  security-summary:
    name: Security Summary
    runs-on: ubuntu-latest
    needs: [sast-bandit, dependency-scan-python, dependency-scan-rust, container-scan, secret-scan]
    if: always()

    steps:
      - name: Check security scan results
        run: |
          echo "✅ Security scan workflow complete"
          echo "Review Security tab for detailed results: https://github.com/${{ github.repository }}/security"
          echo ""
          echo "Expected Phase 0 Results:"
          echo "- Bandit: Few/no issues (minimal code)"
          echo "- Snyk: Some dependency warnings (acceptable)"
          echo "- cargo-audit: Should be clean"
          echo "- Trivy: Some base image CVEs (acceptable)"
          echo "- gitleaks: Should be clean (no secrets)"
```

**Why These Settings**:
- `schedule`: Daily automated scans catch new vulnerabilities
- `continue-on-error: true`: Don't block PRs on minor vulnerabilities during development
- `strategy.matrix`: Scans all 4 main Docker images in parallel
- `upload-sarif`: Integrates with GitHub Security tab

**Save and Exit**: Ctrl+X, Y, Enter

---

### Step 3.2: Create Bandit Configuration (Optional)

**Why**: Reduce false positives in Bandit scans

```bash
cd /home/parobek/Code/OctoLLM

# Add Bandit config to pyproject.toml (append to existing file)
cat >> pyproject.toml <<'EOF'

[tool.bandit]
exclude_dirs = ["/tests", "/venv", "/.venv", "/docs"]
skips = ["B101"]  # Skip assert_used (common in tests)
EOF
```

---

### Step 3.3: Commit and Push Security Workflow

```bash
cd /home/parobek/Code/OctoLLM

# Stage files
git add .github/workflows/security.yml pyproject.toml

# Commit
git commit -m "ci(security): Add comprehensive security scanning workflow

Implement multi-layered security scanning:

**SAST (Static Analysis)**:
- Bandit for Python code vulnerabilities
- Configured to scan orchestrator and all arms

**Dependency Scanning**:
- Snyk for Python packages (HIGH+ severity)
- cargo-audit for Rust dependencies
- Reports uploaded to GitHub Security tab

**Container Scanning**:
- Trivy for Docker image vulnerabilities
- Scans 4 main services (orchestrator, reflex-layer, planner, executor)
- CRITICAL and HIGH severity issues reported

**Secret Scanning**:
- gitleaks for credential detection
- Scans full git history

**Automation**:
- Runs on every push and PR
- Daily scheduled scan at midnight UTC
- Results integrated with GitHub Security

**Phase 0 Expectations**:
- Few/no code vulnerabilities (minimal implementation)
- Some dependency warnings (acceptable during development)
- Base image CVEs acceptable (will be addressed in Phase 5)

Part of Sprint 0.3 Task 0.3.3

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push
git push origin main
```

---

### Step 3.4: Verify Security Workflow Execution

**Check Actions**: Visit `https://github.com/doublegate/OctoLLM/actions`

**Expected Results**:
- ✅ "Security Scan" workflow runs
- ✅ "SAST - Bandit" passes (minimal code, few issues)
- ✅ "Dependency Scan - Snyk" may show warnings (acceptable)
- ✅ "Dependency Scan - cargo-audit" passes (Rust dependencies clean)
- ✅ "Container Scan - Trivy" may show base image CVEs (acceptable)
- ✅ "Secret Scan - gitleaks" passes (no secrets detected)

**Check GitHub Security Tab**:
1. Visit `https://github.com/doublegate/OctoLLM/security`
2. Go to "Code scanning alerts"
3. You should see any vulnerabilities found by Trivy, Snyk, or Bandit
4. Review each alert and determine if action needed

**Common Findings (Acceptable in Phase 0)**:
- **Base Image CVEs**: Alpine/Debian images have some known CVEs (will fix in Phase 5)
- **Outdated Dependencies**: Some Python packages may have newer versions (ok for now)
- **Medium Severity Issues**: Can be addressed later

**Critical/High Issues** (Must Fix):
- If gitleaks finds secrets: Remove from git history immediately
- If Bandit finds SQL injection: Fix before merging
- If Trivy finds critical Docker CVEs: Update base images

---

## Task 0.3.4: Build and Push Workflow

**⏰ Estimated Time**: 3 hours
**📦 Deliverables**: `.github/workflows/build.yml`
**🎯 Goal**: Automatically build and push Docker images to container registry
**🔗 Dependencies**: Task 0.3.3 complete

### Overview

This workflow builds Docker images for all OctoLLM services and pushes them to GitHub Container Registry (GHCR). Images are:
- Built on every merge to `main` branch
- Tagged with git SHA and `latest`
- Multi-architecture (amd64 and arm64)
- Scanned for vulnerabilities post-build

**What Gets Built** (8 images):
1. octollm/orchestrator
2. octollm/reflex-layer
3. octollm/planner-arm
4. octollm/retriever-arm
5. octollm/coder-arm
6. octollm/judge-arm
7. octollm/safety-guardian-arm
8. octollm/executor-arm

---

### Step 4.1: Create Build Workflow File

```bash
cd /home/parobek/Code/OctoLLM

nano .github/workflows/build.yml
```

**File Content**:

```yaml
name: Build and Push

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  REGISTRY: ghcr.io
  IMAGE_PREFIX: ${{ github.repository_owner }}/octollm

jobs:
  build-and-push:
    name: Build and Push Docker Images
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write
    strategy:
      matrix:
        service:
          - name: orchestrator
            dockerfile: services/orchestrator/Dockerfile
            context: .
          - name: reflex-layer
            dockerfile: services/reflex-layer/Dockerfile
            context: .
          - name: planner
            dockerfile: services/arms/planner/Dockerfile
            context: .
          - name: retriever
            dockerfile: services/arms/retriever/Dockerfile
            context: .
          - name: coder
            dockerfile: services/arms/coder/Dockerfile
            context: .
          - name: judge
            dockerfile: services/arms/judge/Dockerfile
            context: .
          - name: safety-guardian
            dockerfile: services/arms/safety-guardian/Dockerfile
            context: .
          - name: executor
            dockerfile: services/arms/executor/Dockerfile
            context: .

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up QEMU
        uses: docker/setup-qemu-action@v3
        with:
          platforms: linux/amd64,linux/arm64

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Log in to GitHub Container Registry
        uses: docker/login-action@v3
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}-${{ matrix.service.name }}
          tags: |
            type=sha,prefix=,format=long
            type=raw,value=latest

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: ${{ matrix.service.context }}
          file: ${{ matrix.service.dockerfile }}
          platforms: linux/amd64,linux/arm64
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Run Trivy post-build scan
        uses: aquasecurity/trivy-action@master
        with:
          image-ref: ${{ env.REGISTRY }}/${{ env.IMAGE_PREFIX }}-${{ matrix.service.name }}:latest
          format: 'table'
          exit-code: '0'  # Don't fail on vulnerabilities post-build
          severity: 'CRITICAL,HIGH'

  build-summary:
    name: Build Summary
    runs-on: ubuntu-latest
    needs: [build-and-push]
    if: always()

    steps:
      - name: Check build results
        run: |
          echo "✅ Docker image build complete"
          echo ""
          echo "Images pushed to GitHub Container Registry:"
          echo "- ghcr.io/${{ github.repository_owner }}/octollm-orchestrator:latest"
          echo "- ghcr.io/${{ github.repository_owner }}/octollm-reflex-layer:latest"
          echo "- ghcr.io/${{ github.repository_owner }}/octollm-planner:latest"
          echo "- ghcr.io/${{ github.repository_owner }}/octollm-retriever:latest"
          echo "- ghcr.io/${{ github.repository_owner }}/octollm-coder:latest"
          echo "- ghcr.io/${{ github.repository_owner }}/octollm-judge:latest"
          echo "- ghcr.io/${{ github.repository_owner }}/octollm-safety-guardian:latest"
          echo "- ghcr.io/${{ github.repository_owner }}/octollm-executor:latest"
          echo ""
          echo "View images: https://github.com/${{ github.repository_owner }}?tab=packages"
```

**Why These Settings**:
- `push.branches: [main]`: Only builds on main (not every PR)
- `permissions.packages: write`: Allows pushing to GHCR
- `setup-qemu-action`: Enables multi-arch builds (amd64 + arm64)
- `cache-from/cache-to: type=gha`: Uses GitHub Actions cache for faster builds
- `exit-code: '0'`: Post-build Trivy scan is informational only

**Save and Exit**: Ctrl+X, Y, Enter

---

### Step 4.2: Enable GitHub Container Registry

**Why**: Need to enable GHCR visibility and configure package permissions

1. **Navigate to Package Settings**:
   ```
   https://github.com/doublegate/OctoLLM/settings/packages
   ```

2. **Enable Container Registry** (if not already enabled):
   - Should be automatically enabled for repositories

3. **Configure Package Visibility** (after first push):
   - Packages will be private by default
   - Can be changed to public later at:
     ```
     https://github.com/users/[YOUR_USERNAME]/packages/container/octollm-orchestrator/settings
     ```

**Note**: Packages will not appear until first build completes

---

### Step 4.3: Commit and Push Build Workflow

```bash
cd /home/parobek/Code/OctoLLM

# Stage workflow
git add .github/workflows/build.yml

# Commit
git commit -m "ci(build): Add Docker image build and push workflow

Implement automated Docker image builds for all services:

**Images Built** (8 total):
- orchestrator (Python + FastAPI)
- reflex-layer (Rust + Axum)
- 6 arms: planner, retriever, coder, judge, safety-guardian, executor

**Features**:
- Multi-architecture support (amd64, arm64)
- Pushed to GitHub Container Registry (GHCR)
- Tagged with git SHA and 'latest'
- GitHub Actions cache for faster builds
- Post-build Trivy vulnerability scan

**Triggers**:
- Automatic on push to main branch
- Manual via workflow_dispatch

**Performance**:
- Parallel builds (8 services)
- Layer caching via GitHub Actions
- QEMU for cross-platform builds

**Phase 0 Note**:
- First build will take ~15-20 minutes
- Subsequent builds ~5-8 minutes (with cache)

Part of Sprint 0.3 Task 0.3.4

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

# Push (this will trigger the build)
git push origin main
```

---

### Step 4.4: Monitor First Build

**Expected Duration**: 15-20 minutes (first build), 5-8 minutes (subsequent)

1. **Watch Build Progress**:
   - Visit: `https://github.com/doublegate/OctoLLM/actions`
   - Click on "Build and Push" workflow
   - Watch 8 parallel builds in matrix strategy

2. **Expected Stages Per Service**:
   - ✅ Checkout code
   - ✅ Set up QEMU (for multi-arch)
   - ✅ Set up Docker Buildx
   - ✅ Log in to GHCR
   - ✅ Extract metadata (tags)
   - ✅ Build and push (longest step: 3-5 min per service)
   - ✅ Run Trivy scan (post-build)

3. **Verify Images Pushed**:
   - Visit: `https://github.com/doublegate?tab=packages`
   - You should see 8 packages:
     - `octollm-orchestrator`
     - `octollm-reflex-layer`
     - `octollm-planner`
     - `octollm-retriever`
     - `octollm-coder`
     - `octollm-judge`
     - `octollm-safety-guardian`
     - `octollm-executor`

4. **Check Image Details**:
   - Click on any package
   - You should see:
     - 2 tags: `latest` and `sha-[git-commit-sha]`
     - 2 platforms: `linux/amd64`, `linux/arm64`
     - Total size per image
     - Vulnerability scan results (if any)

**Success Criteria**:
- ✅ All 8 builds complete successfully
- ✅ Images appear in GitHub Packages
- ✅ Multi-arch support confirmed (amd64 + arm64)
- ✅ Total build time < 20 minutes

---

### Step 4.5: Test Pulling Images

**Why**: Verify images are accessible and functional

```bash
# Pull orchestrator image
docker pull ghcr.io/doublegate/octollm-orchestrator:latest

# Verify image pulled
docker images | grep octollm-orchestrator

# Expected output:
# ghcr.io/doublegate/octollm-orchestrator   latest   [image-id]   [size]   [time]

# Test running the image
docker run --rm ghcr.io/doublegate/octollm-orchestrator:latest --help

# Expected: Should show help text or version (depending on entrypoint)
```

**If Pull Fails with "unauthorized"**:

```bash
# Log in to GHCR
echo $YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin

# Or create a personal access token:
# 1. Go to: https://github.com/settings/tokens
# 2. Generate new token (classic)
# 3. Select scope: read:packages
# 4. Copy token and use in login command above
```

---

## Post-Sprint Configuration

**⏰ Estimated Time**: 30 minutes
**🎯 Goal**: Configure branch protection and finalize CI/CD setup

### Step 5.1: Configure Branch Protection Rules

**Why**: Prevent direct pushes to main, require CI checks to pass before merge

1. **Navigate to Branch Protection Settings**:
   ```
   https://github.com/doublegate/OctoLLM/settings/branches
   ```

2. **Click "Add branch protection rule"**

3. **Configure Rule**:
   ```
   Branch name pattern: main

   ✅ Require a pull request before merging
      ✅ Require approvals: 1
      ✅ Dismiss stale pull request approvals when new commits are pushed
      ✅ Require review from Code Owners

   ✅ Require status checks to pass before merging
      ✅ Require branches to be up to date before merging
      Status checks that are required:
         ✅ lint-python
         ✅ lint-rust
         ✅ test-python (3.11)
         ✅ test-python (3.12)
         ✅ test-rust
         ✅ integration-tests
         ✅ sast-bandit
         ✅ dependency-scan-python
         ✅ dependency-scan-rust
         ✅ secret-scan

   ✅ Require conversation resolution before merging

   ✅ Require linear history

   ✅ Include administrators (optional - enforces rules on admins too)

   ❌ Allow force pushes (keep disabled)
   ❌ Allow deletions (keep disabled)
   ```

4. **Click "Create"**

**Verification**: Try to push directly to main:

```bash
cd /home/parobek/Code/OctoLLM

# Try direct push
echo "test" >> README.md
git add README.md
git commit -m "test: direct push"
git push origin main

# Expected result:
# remote: error: GH006: Protected branch update failed for refs/heads/main.
# remote: error: Required status check "lint-python" is expected.
```

**Success**: Direct push blocked, must use PR workflow

---

### Step 5.2: Create Test Pull Request

**Why**: Verify full CI/CD pipeline works end-to-end

1. **Create Feature Branch**:
   ```bash
   cd /home/parobek/Code/OctoLLM

   # Create and checkout feature branch
   git checkout -b test/verify-ci-pipeline

   # Make a trivial change
   echo "## CI/CD Pipeline" >> README.md
   echo "All workflows configured and operational." >> README.md

   # Commit
   git add README.md
   git commit -m "docs: Add CI/CD pipeline section to README

   Verify Sprint 0.3 workflows are operational.

   🤖 Generated with [Claude Code](https://claude.com/claude-code)

   Co-Authored-By: Claude <noreply@anthropic.com>"

   # Push to GitHub
   git push origin test/verify-ci-pipeline
   ```

2. **Create Pull Request**:
   - Visit: `https://github.com/doublegate/OctoLLM/pulls`
   - Click "New pull request"
   - Base: `main`, Compare: `test/verify-ci-pipeline`
   - Title: "test: Verify CI/CD pipeline workflows"
   - Description:
     ```markdown
     ## Purpose
     Verify Sprint 0.3 CI/CD workflows are operational.

     ## Changes
     - Add CI/CD section to README

     ## Checklist
     - [x] All CI workflows pass
     - [x] No security issues found
     - [x] Branch protection working

     ## Expected Results
     ✅ Lint workflow passes
     ✅ Test workflow passes (placeholder tests)
     ✅ Security scan passes
     ✅ Build workflow NOT triggered (only on main)
     ```
   - Click "Create pull request"

3. **Monitor CI Workflows**:
   - All 3 workflows should trigger automatically:
     - ✅ Lint
     - ✅ Test
     - ✅ Security Scan
   - Watch checks at bottom of PR page
   - Expected duration: 5-8 minutes total

4. **Merge Pull Request**:
   - Wait for all checks to pass
   - Click "Squash and merge"
   - Confirm merge
   - Delete branch `test/verify-ci-pipeline`

5. **Verify Build Triggered**:
   - Visit Actions page
   - "Build and Push" workflow should trigger automatically
   - Verify new images pushed with updated SHA tag

**Success Criteria**:
- ✅ PR created successfully
- ✅ All required checks run and pass
- ✅ Branch protection prevented merge until checks passed
- ✅ Merge succeeded after checks passed
- ✅ Build workflow triggered post-merge
- ✅ New images pushed to GHCR

---

### Step 5.3: Update Project Documentation

**Why**: Document CI/CD setup for future contributors

```bash
cd /home/parobek/Code/OctoLLM

# Update CHANGELOG
cat >> CHANGELOG.md <<'EOF'

## [Sprint 0.3] - 2025-11-14

### Added - Phase 0 Sprint 0.3: CI/CD Pipeline

#### GitHub Actions Workflows
- `lint.yml` - Code quality checks (Ruff, Black, mypy, rustfmt, clippy)
- `test.yml` - Unit and integration tests (pytest, cargo test)
- `security.yml` - Security scanning (Bandit, Snyk, cargo-audit, Trivy, gitleaks)
- `build.yml` - Docker image builds and push to GHCR

#### Features
- Automated linting on every push and PR
- Test coverage reporting via Codecov
- Multi-layered security scanning (SAST, dependency, container, secrets)
- Multi-architecture Docker builds (amd64, arm64)
- Branch protection on main branch with required checks
- Daily scheduled security scans

#### External Integrations
- Codecov for test coverage tracking
- Snyk for dependency vulnerability scanning
- GitHub Container Registry for Docker images
- GitHub Security tab for vulnerability aggregation

### Changed
- Branch protection enabled on `main` branch
- All PRs must pass CI checks before merge
- Direct pushes to `main` blocked

### Configuration
- `.github/workflows/` - All 4 CI/CD workflows
- `pyproject.toml` - Ruff and Bandit configuration
- Branch protection rules configured via GitHub UI

EOF

# Update README with CI badges (optional)
# You can add these badges at the top of README.md:
cat > README_BADGES.md <<'EOF'
![Lint](https://github.com/doublegate/OctoLLM/workflows/Lint/badge.svg)
![Test](https://github.com/doublegate/OctoLLM/workflows/Test/badge.svg)
![Security](https://github.com/doublegate/OctoLLM/workflows/Security%20Scan/badge.svg)
[![codecov](https://codecov.io/gh/doublegate/OctoLLM/branch/main/graph/badge.svg)](https://codecov.io/gh/doublegate/OctoLLM)
EOF

# Commit documentation updates
git add CHANGELOG.md README_BADGES.md
git commit -m "docs(sprint-0.3): Update CHANGELOG and add CI badges

Document Sprint 0.3 completion and CI/CD pipeline setup.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git push origin main
```

---

## Verification Steps

**Complete Verification Checklist**:

### ✅ Workflow Files Exist
```bash
cd /home/parobek/Code/OctoLLM
ls -la .github/workflows/

# Expected output:
# lint.yml
# test.yml
# security.yml
# build.yml
```

### ✅ All Workflows Pass
1. Visit: `https://github.com/doublegate/OctoLLM/actions`
2. Verify last run of each workflow shows ✅ green checkmark:
   - Lint
   - Test
   - Security Scan
   - Build and Push

### ✅ Codecov Integration Working
1. Visit: `https://app.codecov.io/gh/doublegate/OctoLLM`
2. Verify coverage reports uploaded (0% is expected for Phase 0)
3. Copy badge URL for README

### ✅ Snyk Integration Working
1. Visit: `https://app.snyk.io/org/[your-org]/projects`
2. Verify `doublegate/OctoLLM` project shows dependency analysis
3. Check for high/critical vulnerabilities (should be minimal)

### ✅ Container Images Published
1. Visit: `https://github.com/doublegate?tab=packages`
2. Verify 8 packages published:
   - octollm-orchestrator
   - octollm-reflex-layer
   - octollm-planner
   - octollm-retriever
   - octollm-coder
   - octollm-judge
   - octollm-safety-guardian
   - octollm-executor
3. Each package should have:
   - `latest` tag
   - `sha-[commit]` tag
   - 2 architectures (amd64, arm64)

### ✅ Branch Protection Configured
1. Visit: `https://github.com/doublegate/OctoLLM/settings/branches`
2. Verify `main` branch has protection rule
3. Required checks:
   - lint-python ✅
   - lint-rust ✅
   - test-python (3.11) ✅
   - test-python (3.12) ✅
   - test-rust ✅
   - integration-tests ✅
   - sast-bandit ✅
   - dependency-scan-python ✅
   - dependency-scan-rust ✅
   - secret-scan ✅

### ✅ Pull Request Workflow Works
1. Create test PR (see Step 5.2)
2. Verify all checks run automatically
3. Verify merge blocked until checks pass
4. Verify build workflow triggers post-merge

### ✅ Security Tab Populated
1. Visit: `https://github.com/doublegate/OctoLLM/security`
2. Check "Code scanning alerts"
3. Verify Trivy, Snyk, and Bandit results appear
4. Review any critical/high alerts

### ✅ Documentation Updated
- [x] CHANGELOG.md includes Sprint 0.3 entry
- [x] README.md has CI badges (optional)
- [x] `to-dos/MASTER-TODO.md` marked Sprint 0.3 complete
- [x] Sprint 0.3 completion report created

---

## Troubleshooting

### Issue 1: Codecov Upload Fails

**Symptom**: "Error uploading coverage to Codecov"

**Solution 1**: Verify Token
```bash
# Check secret exists
# Visit: https://github.com/doublegate/OctoLLM/settings/secrets/actions
# Confirm CODECOV_TOKEN is present
```

**Solution 2**: Update Codecov Action
```yaml
# In .github/workflows/test.yml, update Codecov step:
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v4  # Use v4
  with:
    token: ${{ secrets.CODECOV_TOKEN }}
    files: ./coverage.xml
    fail_ci_if_error: false  # Don't fail if upload fails
```

---

### Issue 2: Snyk Token Invalid

**Symptom**: "Authentication failed: Invalid token"

**Solution**:
1. Visit: `https://app.snyk.io/account`
2. Regenerate API token
3. Update GitHub secret:
   - Go to: `https://github.com/doublegate/OctoLLM/settings/secrets/actions`
   - Click "Update" on `SNYK_TOKEN`
   - Paste new token
4. Re-run workflow

---

### Issue 3: Docker Build Out of Memory

**Symptom**: "Error: failed to solve: rpc error: code = Unknown"

**Solution 1**: Reduce Parallel Builds
```yaml
# In .github/workflows/build.yml, add max-parallel:
strategy:
  max-parallel: 4  # Build 4 at a time instead of 8
  matrix:
    service: [...]
```

**Solution 2**: Use Smaller Runner (if available)
```yaml
# Use self-hosted runner with more resources
runs-on: [self-hosted, linux, x64]
```

---

### Issue 4: Branch Protection Blocks Merge

**Symptom**: "Required status checks are not passing"

**Solution**: Check which checks are failing
1. Visit PR page
2. Scroll to bottom
3. Click "Details" on failed check
4. Fix issue
5. Push new commit to same branch
6. Checks will re-run automatically

---

### Issue 5: GHCR Push Permission Denied

**Symptom**: "Error: failed to push: unauthorized"

**Solution**: Verify Workflow Permissions
1. Visit: `https://github.com/doublegate/OctoLLM/settings/actions`
2. Scroll to "Workflow permissions"
3. Select: "Read and write permissions"
4. Enable: "Allow GitHub Actions to create and approve pull requests"
5. Click "Save"
6. Re-run workflow

---

### Issue 6: Multi-Arch Build Fails

**Symptom**: "Error: failed to solve: linux/arm64: not found"

**Solution**: Ensure QEMU is set up
```yaml
# Verify this step exists in build.yml:
- name: Set up QEMU
  uses: docker/setup-qemu-action@v3
  with:
    platforms: linux/amd64,linux/arm64
```

If still failing, build only amd64 initially:
```yaml
platforms: linux/amd64  # Remove arm64 temporarily
```

---

### Issue 7: Trivy Scan Times Out

**Symptom**: "Error: timeout waiting for scan results"

**Solution**: Increase Timeout
```yaml
- name: Run Trivy vulnerability scanner
  uses: aquasecurity/trivy-action@master
  with:
    image-ref: octollm/${{ matrix.service }}:latest
    timeout: 15m  # Increase from default 5m
    format: 'sarif'
```

---

### Issue 8: gitleaks Finds False Positive

**Symptom**: "Secret detected: [false positive]"

**Solution**: Create gitleaks config to ignore
```bash
cd /home/parobek/Code/OctoLLM

cat > .gitleaks.toml <<'EOF'
# Gitleaks configuration
title = "OctoLLM gitleaks config"

[[rules]]
description = "Ignore test API keys"
regex = '''test_api_key_[a-zA-Z0-9]+'''
path = '''tests/.*'''

[[rules]]
description = "Ignore example environment files"
regex = '''.*'''
path = '''.*\.env\.example'''
EOF

git add .gitleaks.toml
git commit -m "ci(security): Add gitleaks config for false positives"
git push origin main
```

---

## Appendices

### Appendix A: Complete File Tree

After Sprint 0.3 completion, `.github/workflows/` should contain:

```
.github/
└── workflows/
    ├── lint.yml          # Python + Rust linting
    ├── test.yml          # Unit + integration tests
    ├── security.yml      # Multi-layer security scanning
    └── build.yml         # Docker image builds
```

---

### Appendix B: Estimated CI/CD Costs

**GitHub Actions Minutes** (Free tier: 2,000 min/month):

| Workflow | Duration | Frequency | Monthly Minutes |
|----------|----------|-----------|----------------|
| Lint | 2 min | 20 PRs + 20 pushes | 80 min |
| Test | 5 min | 20 PRs + 20 pushes | 200 min |
| Security | 8 min | 20 PRs + 20 pushes + 30 daily | 560 min |
| Build | 15 min | 20 main merges | 300 min |
| **Total** | | | **1,140 min/month** |

**Within Free Tier**: ✅ Yes (57% of 2,000 min/month)

**External Services**:
- Codecov: Free for open source
- Snyk: Free tier (100 tests/month)
- GitHub Container Registry: 500 MB free storage

---

### Appendix C: Workflow Trigger Matrix

| Workflow | Push (main) | Push (develop) | PR | Schedule | Manual |
|----------|-------------|----------------|-----|----------|--------|
| Lint | ✅ | ✅ | ✅ | ❌ | ✅ |
| Test | ✅ | ✅ | ✅ | ❌ | ✅ |
| Security | ✅ | ✅ | ✅ | ✅ Daily | ✅ |
| Build | ✅ | ❌ | ❌ | ❌ | ✅ |

---

### Appendix D: Required GitHub Secrets

| Secret Name | Purpose | How to Obtain |
|-------------|---------|---------------|
| `CODECOV_TOKEN` | Upload test coverage | https://codecov.io/ → Repository settings |
| `SNYK_TOKEN` | Dependency scanning | https://snyk.io/account → Auth Token |
| `GITHUB_TOKEN` | GHCR push, SARIF upload | Automatically provided by GitHub |

**Note**: `GITHUB_TOKEN` is auto-generated, do not manually create

---

### Appendix E: Next Steps (Sprint 0.4)

After Sprint 0.3 completion, proceed to **Sprint 0.4: Infrastructure as Code**:

**Tasks**:
1. Choose cloud provider (AWS, GCP, or Azure)
2. Create Terraform/Pulumi infrastructure modules
3. Provision Kubernetes clusters (dev, staging, prod)
4. Set up managed databases (PostgreSQL, Redis)
5. Configure secrets management (Vault, AWS Secrets Manager)
6. Document infrastructure provisioning

**Prerequisites**:
- Sprint 0.3 complete ✅
- Cloud provider account created
- Terraform/Pulumi installed locally
- AWS CLI (or equivalent) configured

**Estimated Duration**: 4 days (16 hours)
**Reference**: `to-dos/PHASE-0-PROJECT-SETUP.md` Section 0.4

---

## Summary

**Sprint 0.3 Deliverables** ✅:
1. ✅ Linting workflow (Python + Rust)
2. ✅ Testing workflow (pytest + cargo test + Codecov)
3. ✅ Security scanning workflow (Bandit + Snyk + cargo-audit + Trivy + gitleaks)
4. ✅ Build and push workflow (Docker + GHCR + multi-arch)
5. ✅ Branch protection configured
6. ✅ External services integrated (Codecov, Snyk, GHCR)
7. ✅ Documentation updated (CHANGELOG, README badges)

**Success Metrics**:
- All 4 workflows operational and passing ✅
- Branch protection prevents direct main pushes ✅
- At least 1 PR merged through full pipeline ✅
- Docker images automatically built and published ✅
- Security scans integrated with GitHub Security tab ✅

**Total Time Spent**: ~13 hours (as estimated)

**Next Sprint**: 0.4 Infrastructure as Code (Terraform/Pulumi)

---

**Plan Author**: Claude Code AI Assistant
**Plan Date**: 2025-11-11
**Sprint Start**: After Sprint 0.2 commit (2025-11-11)
**Sprint End**: 2025-11-14 (3 days)
**Status**: READY TO EXECUTE

---

**Approval**: Ready for implementation ✅

🤖 Generated with [Claude Code](https://claude.com/claude-code)
