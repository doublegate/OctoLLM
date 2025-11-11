# Coding Standards

**Last Updated**: 2025-11-10
**Status**: Production Standard
**Applies To**: All OctoLLM codebase (Python, Rust)

## Overview

This document defines coding standards for the OctoLLM project to ensure consistency, maintainability, and quality across the codebase. These standards apply to all contributors and are enforced through automated tooling and code reviews.

## Table of Contents

- [Python Standards](#python-standards)
- [Rust Standards](#rust-standards)
- [General Standards](#general-standards)
- [Documentation Standards](#documentation-standards)
- [Testing Standards](#testing-standards)
- [Git Commit Standards](#git-commit-standards)
- [Automated Enforcement](#automated-enforcement)

---

## Python Standards

### Style Guide

Follow [PEP 8](https://peps.python.org/pep-0008/) with the following specific requirements:

**Line Length**:
```python
# Maximum 100 characters per line (not PEP 8's 79)
# For better readability on modern displays
MAX_LINE_LENGTH = 100
```

**Imports**:
```python
# Group imports in this order:
# 1. Standard library
# 2. Third-party packages
# 3. Local application imports

import asyncio
import logging
from typing import List, Optional, Dict, Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from octollm.models import TaskContract
from octollm.utils import generate_id
```

**Type Hints**:
```python
# ALWAYS use type hints for function signatures
from typing import List, Dict, Optional, Any, Union

# Good
async def get_task(task_id: str) -> Optional[TaskContract]:
    """Retrieve a task by ID."""
    return await db.get_task(task_id)

# Bad - no type hints
async def get_task(task_id):
    return await db.get_task(task_id)

# Use TypedDict for complex dictionaries
from typing import TypedDict

class TaskData(TypedDict):
    task_id: str
    status: str
    result: Optional[Dict[str, Any]]

# Prefer Pydantic models for validation
from pydantic import BaseModel

class TaskContract(BaseModel):
    task_id: str
    description: str
    priority: int = Field(default=5, ge=1, le=10)
```

**Async/Await**:
```python
# Use async/await consistently
# Prefix async functions with "async_" if mixing sync/async

# Good
async def fetch_data() -> Dict[str, Any]:
    async with httpx.AsyncClient() as client:
        response = await client.get("http://api.example.com/data")
        return response.json()

# For mixed codebases, be explicit
async def async_process_task(task: TaskContract) -> str:
    result = await fetch_data()
    return sync_format_result(result)

def sync_format_result(data: Dict[str, Any]) -> str:
    return json.dumps(data, indent=2)
```

**Class Definitions**:
```python
# Use dataclasses for simple data structures
from dataclasses import dataclass, field
from typing import List

@dataclass
class ArmCapability:
    """Represents an arm's capabilities."""

    name: str
    description: str
    tags: List[str] = field(default_factory=list)
    enabled: bool = True

    def matches_tag(self, tag: str) -> bool:
        """Check if capability matches a tag."""
        return tag.lower() in [t.lower() for t in self.tags]

# Use Pydantic for validation and API models
from pydantic import BaseModel, Field, validator

class TaskRequest(BaseModel):
    """Request model for task creation."""

    description: str = Field(..., min_length=10, max_length=10000)
    priority: int = Field(default=5, ge=1, le=10)
    timeout: int = Field(default=300, gt=0, le=3600)

    @validator('description')
    def description_not_empty(cls, v: str) -> str:
        """Ensure description is not just whitespace."""
        if not v.strip():
            raise ValueError("Description cannot be empty")
        return v.strip()
```

**Error Handling**:
```python
# Use specific exceptions, not bare except
# Create custom exceptions for domain errors

class OctoLLMException(Exception):
    """Base exception for OctoLLM errors."""
    pass

class TaskNotFoundError(OctoLLMException):
    """Task not found in database."""
    pass

class ArmUnavailableError(OctoLLMException):
    """No suitable arm available for task."""
    pass

# Good error handling
async def get_task(task_id: str) -> TaskContract:
    try:
        task = await db.query_task(task_id)
        if not task:
            raise TaskNotFoundError(f"Task {task_id} not found")
        return task
    except asyncpg.PostgresError as e:
        logger.error("Database error", task_id=task_id, error=str(e))
        raise OctoLLMException("Failed to retrieve task") from e

# Bad - catches everything
try:
    task = await db.query_task(task_id)
except Exception:
    return None
```

**Logging**:
```python
# Use structured logging with context
import structlog

logger = structlog.get_logger(__name__)

# Good - structured with context
async def process_task(task: TaskContract) -> str:
    logger.info(
        "task.processing.started",
        task_id=task.task_id,
        priority=task.priority,
        user_id=task.user_id
    )

    try:
        result = await execute_task(task)
        logger.info(
            "task.processing.completed",
            task_id=task.task_id,
            duration_ms=result.duration
        )
        return result.output
    except Exception as e:
        logger.error(
            "task.processing.failed",
            task_id=task.task_id,
            error=str(e),
            exc_info=True
        )
        raise

# Bad - unstructured logging
logging.info(f"Processing task {task.task_id}")
```

**Docstrings**:
```python
# Use Google-style docstrings
def calculate_routing_score(
    task: TaskContract,
    capability: ArmCapability
) -> float:
    """Calculate routing score for arm selection.

    Args:
        task: The task to route
        capability: The arm capability to evaluate

    Returns:
        Score between 0.0 and 1.0, where higher is better match

    Raises:
        ValueError: If task or capability is invalid

    Example:
        >>> task = TaskContract(description="Write Python code")
        >>> capability = ArmCapability(name="coder", tags=["python"])
        >>> score = calculate_routing_score(task, capability)
        >>> assert 0.0 <= score <= 1.0
    """
    if not task.description:
        raise ValueError("Task description cannot be empty")

    score = 0.0
    for tag in capability.tags:
        if tag.lower() in task.description.lower():
            score += 0.2

    return min(score, 1.0)
```

**Code Organization**:
```python
# Organize modules by feature, not by type
# Good structure:
octollm/
├── orchestrator/
│   ├── __init__.py
│   ├── planner.py       # Task planning logic
│   ├── router.py        # Arm routing logic
│   ├── models.py        # Orchestrator models
│   └── api.py           # FastAPI endpoints
├── arms/
│   ├── __init__.py
│   ├── base.py          # Base arm interface
│   ├── planner/
│   ├── coder/
│   └── judge/
└── memory/
    ├── __init__.py
    ├── global_memory.py
    ├── local_memory.py
    └── router.py

# Each module should have clear responsibilities
# Keep functions focused and small (< 50 lines)
```

### Tools Configuration

**pyproject.toml** (Black, isort, mypy):
```toml
[tool.black]
line-length = 100
target-version = ['py311']
include = '\.pyi?$'

[tool.isort]
profile = "black"
line_length = 100
multi_line_output = 3
include_trailing_comma = true

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
strict_equality = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false

[tool.ruff]
line-length = 100
target-version = "py311"
select = [
    "E",    # pycodestyle errors
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "ARG",  # flake8-unused-arguments
    "SIM",  # flake8-simplify
]
ignore = [
    "E501",  # line too long (handled by black)
    "B008",  # function call in argument defaults
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = "test_*.py"
python_classes = "Test*"
python_functions = "test_*"
addopts = "-v --strict-markers --cov=octollm --cov-report=term-missing"
```

**.pre-commit-config.yaml**:
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-json
      - id: check-added-large-files
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix, --exit-non-zero-on-fix]

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

---

## Rust Standards

### Style Guide

Follow the [Rust Style Guide](https://doc.rust-lang.org/style-guide/) with `rustfmt` defaults.

**Naming Conventions**:
```rust
// Snake case for variables and functions
let task_id = generate_id();
fn process_request(input: &str) -> Result<String, Error> { }

// CamelCase for types
struct TaskContract { }
enum TaskStatus { }
trait ArmCapability { }

// SCREAMING_SNAKE_CASE for constants
const MAX_RETRIES: u32 = 3;
const DEFAULT_TIMEOUT: Duration = Duration::from_secs(30);
```

**Error Handling**:
```rust
// Use Result for recoverable errors
use thiserror::Error;

#[derive(Error, Debug)]
pub enum ReflexError {
    #[error("PII detected in input: {pattern}")]
    PiiDetected { pattern: String },

    #[error("Rate limit exceeded: {limit} req/s")]
    RateLimitExceeded { limit: u32 },

    #[error("Cache error: {0}")]
    CacheError(#[from] redis::RedisError),
}

// Use ? operator for error propagation
async fn preprocess(input: &str) -> Result<String, ReflexError> {
    let sanitized = detect_pii(input)?;
    let cached = cache.get(&sanitized).await?;
    Ok(cached.unwrap_or_else(|| sanitized))
}

// Avoid unwrap() in production code
// Good
match result {
    Ok(value) => process(value),
    Err(e) => {
        error!("Processing failed: {}", e);
        return Err(e);
    }
}

// Bad
let value = result.unwrap();
```

**Async/Await**:
```rust
// Use tokio for async runtime
use tokio::time::{sleep, Duration};

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    let server = start_server().await?;
    server.await?;
    Ok(())
}

// Use async fn for async functions
async fn fetch_data(url: &str) -> Result<String, reqwest::Error> {
    let response = reqwest::get(url).await?;
    response.text().await
}

// Use async blocks for complex logic
let future = async {
    let data1 = fetch_data("http://api1.com").await?;
    let data2 = fetch_data("http://api2.com").await?;
    Ok::<_, Error>(merge(data1, data2))
};
```

**Traits and Generics**:
```rust
// Define traits for shared behavior
pub trait ArmInterface {
    async fn execute(&self, task: TaskContract) -> Result<String, ArmError>;
    async fn health_check(&self) -> HealthStatus;
    fn capabilities(&self) -> &[Capability];
}

// Use generics with trait bounds
pub struct Router<T: ArmInterface> {
    arms: Vec<T>,
}

impl<T: ArmInterface> Router<T> {
    pub async fn route(&self, task: &TaskContract) -> Result<&T, RouterError> {
        for arm in &self.arms {
            if arm.capabilities().iter().any(|c| c.matches(task)) {
                return Ok(arm);
            }
        }
        Err(RouterError::NoMatchingArm)
    }
}
```

**Documentation**:
```rust
/// Process a task through the reflex layer.
///
/// This function performs PII detection, rate limiting, and caching
/// before forwarding the task to the orchestrator.
///
/// # Arguments
///
/// * `input` - The raw task input from the user
/// * `config` - Reflex layer configuration
///
/// # Returns
///
/// * `Ok(String)` - Sanitized and validated input
/// * `Err(ReflexError)` - If validation fails
///
/// # Errors
///
/// Returns `ReflexError::PiiDetected` if PII is found and cannot be sanitized.
/// Returns `ReflexError::RateLimitExceeded` if rate limit is exceeded.
///
/// # Example
///
/// ```
/// use reflex::{preprocess, Config};
///
/// let config = Config::default();
/// let result = preprocess("Hello world", &config).await?;
/// assert_eq!(result, "Hello world");
/// ```
pub async fn preprocess(
    input: &str,
    config: &Config,
) -> Result<String, ReflexError> {
    // Implementation
}
```

**Module Organization**:
```rust
// src/lib.rs - Public API
pub mod config;
pub mod error;
pub mod pii;
pub mod rate_limit;
pub mod cache;

pub use config::Config;
pub use error::ReflexError;

// src/pii.rs - PII detection module
use regex::Regex;
use once_cell::sync::Lazy;

static EMAIL_PATTERN: Lazy<Regex> = Lazy::new(|| {
    Regex::new(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b").unwrap()
});

pub struct PiiDetector {
    patterns: Vec<Regex>,
}

impl PiiDetector {
    pub fn new() -> Self {
        Self {
            patterns: vec![EMAIL_PATTERN.clone()],
        }
    }

    pub fn detect(&self, text: &str) -> Vec<String> {
        // Implementation
    }
}
```

### Tools Configuration

**Cargo.toml**:
```toml
[package]
name = "octollm-reflex"
version = "0.1.0"
edition = "2021"
rust-version = "1.75"

[dependencies]
tokio = { version = "1.35", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
thiserror = "1.0"
tracing = "0.1"
regex = "1.10"

[dev-dependencies]
tokio-test = "0.4"
mockall = "0.12"

[profile.release]
opt-level = 3
lto = true
codegen-units = 1
```

**rustfmt.toml**:
```toml
max_width = 100
hard_tabs = false
tab_spaces = 4
edition = "2021"
use_small_heuristics = "Max"
fn_call_width = 80
struct_lit_width = 80
imports_granularity = "Crate"
group_imports = "StdExternalCrate"
```

**clippy.toml**:
```toml
# Deny warnings in CI
warn-on-all-wildcard-imports = true
```

**.cargo/config.toml**:
```toml
[build]
rustflags = ["-D", "warnings"]

[target.x86_64-unknown-linux-gnu]
linker = "clang"
rustflags = ["-C", "link-arg=-fuse-ld=lld"]
```

---

## General Standards

### Naming Conventions

**Files**:
- Python: `snake_case.py` (e.g., `task_router.py`)
- Rust: `snake_case.rs` (e.g., `pii_detector.rs`)
- Configuration: `kebab-case.yml` (e.g., `docker-compose.yml`)

**Variables**:
- Descriptive names, avoid abbreviations
- Good: `task_id`, `user_request`, `arm_capability`
- Bad: `tid`, `req`, `cap`

**Functions**:
- Verb-based names indicating action
- Good: `process_task()`, `validate_input()`, `calculate_score()`
- Bad: `task()`, `input()`, `score()`

**Classes**:
- Noun-based names indicating entity
- Good: `TaskRouter`, `ArmCapability`, `MemoryClient`
- Bad: `ProcessTask`, `DoValidation`, `GetMemory`

### Code Complexity

**Function Length**:
- Target: < 50 lines
- Maximum: 100 lines
- Extract helper functions if exceeding limits

**Cyclomatic Complexity**:
- Target: < 10
- Maximum: 15
- Refactor complex conditionals into separate functions

**Nesting Depth**:
- Target: < 3 levels
- Maximum: 4 levels
- Use early returns and guard clauses

```python
# Good - early returns
def process_task(task: Optional[TaskContract]) -> str:
    if not task:
        return "No task provided"

    if not task.description:
        return "No description"

    return execute_task(task)

# Bad - deep nesting
def process_task(task):
    if task:
        if task.description:
            return execute_task(task)
        else:
            return "No description"
    else:
        return "No task provided"
```

### Performance Considerations

**Database Queries**:
```python
# Good - single query with join
tasks = await db.query("""
    SELECT t.*, u.name as user_name
    FROM tasks t
    JOIN users u ON t.user_id = u.id
    WHERE t.status = $1
""", "pending")

# Bad - N+1 queries
tasks = await db.query("SELECT * FROM tasks WHERE status = $1", "pending")
for task in tasks:
    user = await db.query("SELECT name FROM users WHERE id = $1", task.user_id)
```

**Async Operations**:
```python
# Good - concurrent execution
results = await asyncio.gather(
    fetch_data_1(),
    fetch_data_2(),
    fetch_data_3()
)

# Bad - sequential execution
result1 = await fetch_data_1()
result2 = await fetch_data_2()
result3 = await fetch_data_3()
```

**Caching**:
```python
from cachetools import TTLCache

# Use caching for expensive operations
cache = TTLCache(maxsize=1000, ttl=3600)

async def get_arm_capabilities(arm_id: str) -> List[Capability]:
    if arm_id in cache:
        return cache[arm_id]

    capabilities = await db.fetch_capabilities(arm_id)
    cache[arm_id] = capabilities
    return capabilities
```

---

## Documentation Standards

### Code Comments

**When to Comment**:
- Complex algorithms that aren't self-explanatory
- Business logic that requires context
- Workarounds for bugs or limitations
- Performance-critical sections

**When NOT to Comment**:
- Obvious code (don't state what code does, explain why)
- Redundant information already in function names

```python
# Good
# Use exponential backoff to avoid overwhelming the API
# after transient failures (rate limits, temporary outages)
for attempt in range(MAX_RETRIES):
    try:
        return await api_client.call()
    except TransientError:
        await asyncio.sleep(2 ** attempt)

# Bad
# Loop 3 times
for attempt in range(3):
    # Try to call API
    return await api_client.call()
```

### README Files

Every module/package should have a README.md:

```markdown
# Module Name

Brief description of what this module does.

## Purpose

Detailed explanation of the module's role in the system.

## Components

- `file1.py`: Description
- `file2.py`: Description

## Usage

```python
from module import Component

component = Component()
result = component.process()
```

## Dependencies

- dependency1: Why needed
- dependency2: Why needed

## Testing

```bash
pytest tests/test_module.py
```
```

---

## Testing Standards

### Test Coverage

- **Unit Tests**: 80-95% coverage
- **Integration Tests**: Critical paths covered
- **E2E Tests**: Key workflows covered

### Test Organization

```python
# tests/test_orchestrator.py
import pytest
from octollm.orchestrator import Orchestrator

class TestOrchestrator:
    """Test suite for Orchestrator component."""

    @pytest.fixture
    def orchestrator(self):
        """Provide orchestrator instance for tests."""
        return Orchestrator(config=test_config)

    def test_plan_simple_task(self, orchestrator):
        """Test planning for a simple task."""
        task = TaskContract(description="List files")
        plan = orchestrator.plan(task)

        assert len(plan.steps) == 1
        assert plan.steps[0].arm == "executor"

    @pytest.mark.asyncio
    async def test_execute_task_success(self, orchestrator):
        """Test successful task execution."""
        task = TaskContract(description="Write hello world")
        result = await orchestrator.execute(task)

        assert result.status == "completed"
        assert "hello world" in result.output.lower()
```

### Test Naming

- Test file: `test_<module>.py`
- Test class: `Test<Component>`
- Test method: `test_<what>_<condition>_<expected>`

Examples:
- `test_plan_complex_task_returns_multiple_steps`
- `test_route_invalid_task_raises_error`
- `test_cache_miss_fetches_from_database`

---

## Git Commit Standards

### Commit Message Format

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code restructuring without feature change
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `chore`: Build process, dependencies, etc.

**Examples**:
```
feat(orchestrator): add support for parallel task execution

Implement asyncio.gather() for executing multiple independent
subtasks concurrently. This reduces overall task completion time
by 40% for tasks with multiple independent steps.

Closes #123
```

```
fix(reflex): handle edge case in PII detection

Email regex was not matching emails with plus addressing
(user+tag@domain.com). Updated pattern to support RFC 5322.

Fixes #456
```

### Branch Naming

- Feature: `feature/<issue-id>-<short-description>`
- Bug fix: `fix/<issue-id>-<short-description>`
- Hotfix: `hotfix/<issue-id>-<short-description>`

Examples:
- `feature/123-parallel-execution`
- `fix/456-pii-email-detection`
- `hotfix/789-critical-memory-leak`

---

## Automated Enforcement

### Pre-commit Hooks

Install pre-commit hooks:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### CI/CD Checks

**.github/workflows/quality.yml**:
```yaml
name: Code Quality

on: [push, pull_request]

jobs:
  python-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install black isort ruff mypy pytest pytest-cov
          pip install -r requirements.txt

      - name: Check formatting (black)
        run: black --check .

      - name: Check import sorting (isort)
        run: isort --check-only .

      - name: Lint (ruff)
        run: ruff check .

      - name: Type check (mypy)
        run: mypy octollm/

      - name: Run tests
        run: pytest --cov=octollm --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  rust-quality:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Rust
        uses: actions-rs/toolchain@v1
        with:
          toolchain: stable
          components: rustfmt, clippy

      - name: Check formatting
        run: cargo fmt --check

      - name: Lint
        run: cargo clippy -- -D warnings

      - name: Run tests
        run: cargo test
```

### IDE Configuration

**VS Code** (`.vscode/settings.json`):
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.mypyEnabled": true,
  "python.formatting.provider": "black",
  "editor.formatOnSave": true,
  "editor.rulers": [100],
  "[python]": {
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "rust-analyzer.checkOnSave.command": "clippy"
}
```

---

## References

- [PEP 8 -- Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 257 -- Docstring Conventions](https://peps.python.org/pep-0257/)
- [The Rust Style Guide](https://doc.rust-lang.org/style-guide/)
- [Conventional Commits](https://www.conventionalcommits.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)

---

**Last Review**: 2025-11-10
**Next Review**: 2026-02-10 (Quarterly)
**Owner**: Engineering Team
