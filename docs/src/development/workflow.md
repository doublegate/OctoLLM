# Development Workflow

**Last Updated**: 2025-11-10
**Target Audience**: Contributors, Developers
**Estimated Time**: Reference guide

## Overview

This guide describes the complete development workflow for contributing to OctoLLM, from setting up your environment to getting your changes merged.

## Table of Contents

- [Setup](#setup)
- [Branch Strategy](#branch-strategy)
- [Development Cycle](#development-cycle)
- [Testing Workflow](#testing-workflow)
- [Code Review Process](#code-review-process)
- [Release Process](#release-process)

---

## Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/octollm.git
cd octollm

# Add upstream remote
git remote add upstream https://github.com/octollm/octollm.git

# Verify remotes
git remote -v
# origin    https://github.com/YOUR_USERNAME/octollm.git (fetch)
# origin    https://github.com/YOUR_USERNAME/octollm.git (push)
# upstream  https://github.com/octollm/octollm.git (fetch)
# upstream  https://github.com/octollm/octollm.git (push)
```

### 2. Development Environment

```bash
# Install Python dependencies
cd octollm
poetry install

# Activate virtual environment
poetry shell

# Install Rust (for Reflex Layer)
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Install pre-commit hooks
pre-commit install
```

### 3. Start Development Services

```bash
# Start databases and services
docker compose up -d postgres redis qdrant

# Verify services
docker compose ps
```

---

## Branch Strategy

### Branch Naming

```
feature/<issue-number>-<short-description>
fix/<issue-number>-<short-description>
docs/<issue-number>-<short-description>
refactor/<issue-number>-<short-description>
test/<issue-number>-<short-description>
```

**Examples**:
- `feature/123-parallel-task-execution`
- `fix/456-pii-detection-regex`
- `docs/789-api-reference-update`

### Creating a Branch

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b feature/123-parallel-execution

# Push to your fork
git push -u origin feature/123-parallel-execution
```

---

## Development Cycle

### 1. Pick an Issue

1. Browse [open issues](https://github.com/octollm/octollm/issues)
2. Comment on the issue to claim it
3. Wait for maintainer assignment
4. Create branch from main

### 2. Implement Changes

```bash
# Make changes to code
vim orchestrator/router.py

# Run tests frequently
pytest tests/test_router.py -v

# Check formatting
black . && isort .

# Run linter
ruff check .

# Type check
mypy orchestrator/
```

### 3. Commit Changes

```bash
# Stage changes
git add orchestrator/router.py tests/test_router.py

# Commit with conventional message
git commit -m "feat(orchestrator): implement parallel task execution

Add support for executing multiple independent tasks concurrently
using asyncio.gather(). This reduces total execution time for
multi-step workflows.

- Add concurrent execution in TaskExecutor
- Update tests for parallel execution
- Add documentation for new behavior

Closes #123"

# Push to your fork
git push origin feature/123-parallel-execution
```

### 4. Keep Branch Updated

```bash
# Fetch upstream changes
git fetch upstream

# Rebase on upstream main
git rebase upstream/main

# Resolve conflicts if needed
# ... fix conflicts in files ...
git add <resolved-files>
git rebase --continue

# Force push (rebase changes history)
git push --force-with-lease origin feature/123-parallel-execution
```

---

## Testing Workflow

### Running Tests

**Unit Tests**:
```bash
# Run all unit tests
pytest tests/unit/ -v

# Run specific test file
pytest tests/unit/test_router.py -v

# Run specific test
pytest tests/unit/test_router.py::TestRouter::test_route_task -v

# With coverage
pytest tests/unit/ --cov=orchestrator --cov-report=term-missing
```

**Integration Tests**:
```bash
# Start test services
docker compose -f docker-compose.test.yml up -d

# Run integration tests
pytest tests/integration/ -v

# Cleanup
docker compose -f docker-compose.test.yml down -v
```

**E2E Tests**:
```bash
# Start full stack
docker compose up -d

# Run E2E tests
pytest tests/e2e/ -v

# Cleanup
docker compose down -v
```

### Test Coverage Requirements

- Unit tests: 80-95% coverage for new code
- Integration tests: Critical paths covered
- E2E tests: Key user workflows covered

### Writing Tests

```python
# tests/unit/test_router.py
import pytest
from orchestrator.router import TaskRouter
from octollm.models import TaskContract

class TestTaskRouter:
    """Test task routing functionality."""

    @pytest.fixture
    def router(self):
        """Provide router instance for tests."""
        return TaskRouter()

    @pytest.fixture
    def sample_task(self):
        """Provide sample task for tests."""
        return TaskContract(
            task_id="task-123",
            description="Write Python code to parse JSON",
            priority=5
        )

    async def test_route_task_selects_coder_arm(
        self,
        router,
        sample_task
    ):
        """Test router selects coder arm for code tasks."""
        # Arrange
        task = sample_task

        # Act
        arm = await router.route(task)

        # Assert
        assert arm is not None
        assert arm.name == "coder"
        assert "python" in arm.capabilities

    async def test_route_task_with_no_match_returns_none(
        self,
        router
    ):
        """Test router returns None when no arm matches."""
        # Arrange
        task = TaskContract(
            task_id="task-456",
            description="Impossible task",
            priority=1
        )

        # Act
        arm = await router.route(task)

        # Assert
        assert arm is None
```

---

## Code Review Process

### 1. Create Pull Request

```bash
# Push your branch
git push origin feature/123-parallel-execution

# Open PR on GitHub
# Fill in PR template:
# - Clear title
# - Description of changes
# - Link to issue
# - How to test
# - Screenshots (if UI change)
# - Breaking changes
```

**PR Template**:
```markdown
## Description
Add support for parallel task execution using asyncio.gather()

Closes #123

## Changes
- Add `TaskExecutor.execute_parallel()` method
- Update orchestrator to use parallel execution for independent tasks
- Add unit and integration tests
- Update documentation

## Testing
1. Start development environment: `docker compose up -d`
2. Run tests: `pytest tests/integration/test_parallel_execution.py -v`
3. Verify parallel execution reduces total time

## Breaking Changes
None

## Screenshots
N/A (backend change)
```

### 2. Address Review Comments

```bash
# Make requested changes
vim orchestrator/router.py

# Commit changes
git add orchestrator/router.py
git commit -m "fix: address review comments

- Extract scoring logic to separate function
- Add error handling for edge case
- Improve docstring clarity"

# Push updates
git push origin feature/123-parallel-execution
```

### 3. Merge

Once approved:

```bash
# Ensure branch is up to date
git fetch upstream
git rebase upstream/main
git push --force-with-lease origin feature/123-parallel-execution

# Squash commits if needed (maintainers will do this)
# Merge via GitHub UI
```

---

## Release Process

### Versioning

OctoLLM uses [Semantic Versioning](https://semver.org/):

```
MAJOR.MINOR.PATCH

MAJOR: Breaking changes
MINOR: New features (backward compatible)
PATCH: Bug fixes (backward compatible)
```

**Examples**:
- `0.1.0` → `0.2.0`: New arm added
- `0.1.0` → `0.1.1`: Bug fix in routing
- `1.0.0` → `2.0.0`: API contract changed (breaking)

### Release Workflow

1. **Feature Freeze**: Stop merging new features
2. **Testing**: Run full test suite, manual testing
3. **Documentation**: Update CHANGELOG, version numbers
4. **Tag Release**: Create git tag `v0.2.0`
5. **Build**: Create Docker images, Python packages
6. **Deploy**: Deploy to staging, then production
7. **Announce**: Update release notes, notify users

### Creating a Release (Maintainers)

```bash
# Update version
vim pyproject.toml
# version = "0.2.0"

# Update CHANGELOG
vim CHANGELOG.md

# Commit version bump
git add pyproject.toml CHANGELOG.md
git commit -m "chore: bump version to 0.2.0"

# Create tag
git tag -a v0.2.0 -m "Release version 0.2.0"

# Push tag
git push origin v0.2.0

# GitHub Actions will:
# - Run tests
# - Build Docker images
# - Create GitHub release
# - Publish to PyPI
```

---

## Development Tips

### Running Individual Components

**Orchestrator**:
```bash
cd orchestrator
uvicorn app.main:app --reload --port 8000
```

**Reflex Layer** (Rust):
```bash
cd reflex-layer
cargo run --release
```

**Specific Arm**:
```bash
cd arms/coder
uvicorn app.main:app --reload --port 8102
```

### Hot Reload

```bash
# Python (automatic with --reload)
uvicorn app.main:app --reload

# Rust (use cargo-watch)
cargo install cargo-watch
cargo watch -x run
```

### Debugging

**Python**:
```python
# Add breakpoint
import pdb; pdb.set_trace()

# Or use debugpy for VS Code
import debugpy
debugpy.listen(5678)
debugpy.wait_for_client()
```

**Rust**:
```bash
# Use rust-lldb
rust-lldb target/debug/reflex-layer

# Or VSCode debugger with launch.json
```

### Database Migrations

```bash
# Create migration
alembic revision -m "add_task_priority_index"

# Edit migration in alembic/versions/xxx_add_task_priority_index.py

# Apply migration
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

### Resetting Development Environment

```bash
# Stop all services
docker compose down -v

# Remove volumes
docker volume rm octollm_postgres_data octollm_redis_data

# Restart
docker compose up -d

# Run migrations
alembic upgrade head

# Seed test data
python scripts/seed_data.py
```

---

## Troubleshooting

### Pre-commit Hooks Fail

```bash
# Run hooks manually
pre-commit run --all-files

# Fix formatting
black . && isort .

# Fix linting
ruff check . --fix

# Commit again
git commit --amend --no-edit
```

### Tests Fail in CI but Pass Locally

```bash
# Run tests exactly like CI
docker compose -f docker-compose.test.yml up -d
docker compose -f docker-compose.test.yml exec orchestrator pytest

# Check for:
# - Different Python/Rust versions
# - Missing environment variables
# - Timing issues in async tests
# - Database state pollution
```

### Merge Conflicts

```bash
# Fetch latest
git fetch upstream

# Rebase on main
git rebase upstream/main

# Resolve conflicts
# Edit conflicted files
git add <resolved-files>
git rebase --continue

# Push (force required after rebase)
git push --force-with-lease origin feature/123
```

---

## Best Practices

1. **Commit often**: Small, focused commits
2. **Test early**: Run tests before committing
3. **Stay updated**: Rebase on main regularly
4. **Communicate**: Comment on issues, ask questions
5. **Document**: Update docs with code changes
6. **Review**: Self-review before requesting review
7. **Be patient**: Allow time for review
8. **Learn**: Read existing code, follow patterns

---

## References

- [Coding Standards](../engineering/coding-standards.md)
- [Testing Strategy](../testing/strategy.md)
- [Code Review Checklist](../engineering/code-review.md)
- [Contributing Guidelines](./contributing.md)

---

**Last Review**: 2025-11-10
**Next Review**: 2026-02-10 (Quarterly)
**Owner**: Engineering Team
