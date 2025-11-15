# Phase 4: Engineering & Standards

**Status**: Not Started
**Duration**: 3-4 weeks (parallel with Phase 3)
**Team Size**: 2-3 engineers
**Prerequisites**: Phase 2 complete
**Start Date**: TBD
**Target Completion**: TBD

---

## Overview

Phase 4 establishes comprehensive engineering standards, testing infrastructure, documentation generation systems, and developer workflows to ensure code quality, maintainability, and contributor productivity.

**Key Deliverables**:
1. Code Quality Standards - Python (Black, Ruff, mypy) and Rust (rustfmt, clippy)
2. Testing Infrastructure - pytest, cargo test, coverage targets
3. Documentation Generation - API docs, component diagrams, runbooks
4. Developer Workflows - PR templates, code review automation, release process
5. Performance Benchmarking - Profiling tools and regression detection

**Success Criteria**:
- ✅ Code quality standards enforced in CI
- ✅ Test coverage targets met (85% Python, 80% Rust)
- ✅ Documentation auto-generated
- ✅ Release process automated
- ✅ All team members following standards

**Reference**: `docs/doc_phases/PHASE-4-COMPLETE-SPECIFICATIONS.md` (10,700+ lines)

---

## Sprint 4.1: Code Quality Standards [Week 17-18]

**Duration**: 1-2 weeks
**Team**: 2 engineers
**Prerequisites**: Phase 2 complete
**Priority**: HIGH

### Sprint Goals

- Configure and enforce Python code quality tools (Black, Ruff, mypy)
- Configure and enforce Rust code quality tools (rustfmt, clippy)
- Set up pre-commit hooks for all standards
- Document coding standards and best practices
- Enforce standards in CI pipeline

### Tasks

#### Python Standards Configuration (6 hours)

- [ ] **Configure Black Formatter** (1 hour)
  - Create pyproject.toml configuration
  - Line length: 88 characters
  - Target Python 3.11+
  - Code example:
    ```toml
    # pyproject.toml
    [tool.black]
    line-length = 88
    target-version = ['py311']
    include = '\.pyi?$'
    exclude = '''
    /(
        \.git
      | \.venv
      | build
      | dist
    )/
    '''
    ```
  - Files to update: `pyproject.toml`

- [ ] **Configure Ruff Linter** (2 hours)
  - Import sorting (isort compatibility)
  - Code complexity checks
  - Security checks (Bandit rules)
  - Code example:
    ```toml
    # pyproject.toml
    [tool.ruff]
    line-length = 88
    target-version = "py311"

    select = [
        "E",   # pycodestyle errors
        "W",   # pycodestyle warnings
        "F",   # pyflakes
        "I",   # isort
        "C",   # flake8-comprehensions
        "B",   # flake8-bugbear
        "UP",  # pyupgrade
        "S",   # flake8-bandit
    ]

    ignore = [
        "E501",  # line too long (handled by Black)
        "B008",  # function calls in argument defaults
    ]

    [tool.ruff.per-file-ignores]
    "tests/*" = ["S101"]  # Allow assert in tests
    ```
  - Files to update: `pyproject.toml`

- [ ] **Configure mypy Type Checker** (2 hours)
  - Strict mode for all code
  - Ignore missing imports (third-party)
  - Code example:
    ```toml
    # pyproject.toml
    [tool.mypy]
    python_version = "3.11"
    strict = true
    warn_return_any = true
    warn_unused_configs = true
    disallow_untyped_defs = true
    disallow_any_generics = true
    check_untyped_defs = true
    no_implicit_optional = true
    warn_redundant_casts = true
    warn_unused_ignores = true

    [[tool.mypy.overrides]]
    module = [
        "qdrant_client.*",
        "sentence_transformers.*",
    ]
    ignore_missing_imports = true
    ```
  - Files to update: `pyproject.toml`

- [ ] **Create Pre-Commit Configuration** (1 hour)
  - Hook for Black, Ruff, mypy
  - Run on all Python files
  - Code example:
    ```yaml
    # .pre-commit-config.yaml (Python section)
    repos:
      - repo: https://github.com/psf/black
        rev: 23.11.0
        hooks:
          - id: black
            language_version: python3.11

      - repo: https://github.com/astral-sh/ruff-pre-commit
        rev: v0.1.5
        hooks:
          - id: ruff
            args: [--fix, --exit-non-zero-on-fix]

      - repo: https://github.com/pre-commit/mirrors-mypy
        rev: v1.7.0
        hooks:
          - id: mypy
            additional_dependencies: [pydantic, fastapi, types-redis]
    ```
  - Files to update: `.pre-commit-config.yaml`

#### Rust Standards Configuration (4 hours)

- [ ] **Configure rustfmt** (1 hour)
  - Create rustfmt.toml
  - Edition 2021, max line width 100
  - Code example:
    ```toml
    # rustfmt.toml
    edition = "2021"
    max_width = 100
    use_small_heuristics = "Default"
    reorder_imports = true
    reorder_modules = true
    remove_nested_parens = true
    ```
  - Files to create: `rustfmt.toml`

- [ ] **Configure Clippy** (2 hours)
  - Deny warnings in CI
  - Enable pedantic lints
  - Code example:
    ```toml
    # Cargo.toml
    [workspace.lints.clippy]
    all = "warn"
    pedantic = "warn"
    nursery = "warn"
    cargo = "warn"

    # Allow some pedantic lints
    module_name_repetitions = "allow"
    missing_errors_doc = "allow"
    ```
  - Files to update: `Cargo.toml`

- [ ] **Add Pre-Commit Hooks for Rust** (1 hour)
  - rustfmt check
  - clippy check
  - Files to update: `.pre-commit-config.yaml`

#### Documentation Standards (4 hours)

- [ ] **Define Function Documentation Requirements** (2 hours)
  - Google-style docstrings for Python
  - Rustdoc comments for Rust
  - Type hints required for all public APIs
  - Examples:
    ```python
    # Python example
    def calculate_score(
        results: List[Dict[str, Any]],
        weights: Dict[str, float]
    ) -> float:
        """Calculate weighted score from results.

        Args:
            results: List of result dictionaries with scores
            weights: Weight for each scoring dimension

        Returns:
            Weighted average score (0-100)

        Raises:
            ValueError: If weights don't sum to 1.0

        Example:
            >>> results = [{"dimension": "quality", "score": 90}]
            >>> weights = {"quality": 1.0}
            >>> calculate_score(results, weights)
            90.0
        """
        ...
    ```

    ```rust
    // Rust example
    /// Calculate weighted score from results.
    ///
    /// # Arguments
    ///
    /// * `results` - Vector of result scores
    /// * `weights` - Dimension weights (must sum to 1.0)
    ///
    /// # Returns
    ///
    /// Weighted average score (0-100)
    ///
    /// # Errors
    ///
    /// Returns `ScoreError` if weights don't sum to 1.0
    ///
    /// # Example
    ///
    /// ```
    /// let results = vec![90.0, 80.0];
    /// let weights = vec![0.6, 0.4];
    /// let score = calculate_score(&results, &weights)?;
    /// assert_eq!(score, 86.0);
    /// ```
    pub fn calculate_score(
        results: &[f64],
        weights: &[f64]
    ) -> Result<f64, ScoreError> {
        ...
    }
    ```
  - Files to create: `docs/engineering/documentation-style.md`

- [ ] **Create README Templates** (1 hour)
  - Component README template
  - Service README template
  - Files to create: `docs/templates/README-component.md`, `docs/templates/README-service.md`

- [ ] **Set Up API Documentation Generation** (1 hour)
  - FastAPI auto-generates OpenAPI at `/docs`
  - Configure Swagger UI theme
  - Add API versioning strategy
  - Files to update: All `main.py` files

### Success Criteria

- [ ] Pre-commit hooks prevent non-compliant code
- [ ] CI enforces standards on all PRs
- [ ] All existing code passes linters
- [ ] Documentation standards documented
- [ ] Team trained on standards

### Estimated Effort

- Development: 14 hours
- Testing: 2 hours
- Documentation: 2 hours
- **Total**: 18 hours (~1 week for 2 engineers)

---

## Sprint 4.2: Testing Infrastructure [Week 18-19]

**Duration**: 1-2 weeks
**Team**: 2 engineers
**Prerequisites**: Sprint 4.1 complete
**Priority**: HIGH

### Sprint Goals

- Set up pytest infrastructure with fixtures and plugins
- Configure cargo test for Rust
- Implement mocking strategies (LLMs, databases, external APIs)
- Achieve coverage targets (85% Python, 80% Rust)
- Create testing best practices guide

### Tasks

#### Python Testing Setup (8 hours)

- [ ] **Configure pytest** (2 hours)
  - pytest.ini configuration
  - Fixtures for database, Redis, Qdrant
  - Markers for test categories (unit, integration, e2e)
  - Code example:
    ```ini
    # pytest.ini
    [pytest]
    minversion = 7.0
    testpaths = tests
    python_files = test_*.py
    python_classes = Test*
    python_functions = test_*
    addopts =
        --strict-markers
        --verbose
        --cov=orchestrator
        --cov=arms
        --cov-report=html
        --cov-report=term-missing
        --cov-fail-under=85
    markers =
        unit: Unit tests (no external dependencies)
        integration: Integration tests (require services)
        e2e: End-to-end tests (full system)
        slow: Slow tests (>1 second)
    ```
  - Files to create: `pytest.ini`

- [ ] **Create Test Fixtures** (3 hours)
  - Database fixtures (clean state per test)
  - Redis fixtures (isolated namespaces)
  - Qdrant fixtures (test collections)
  - LLM mock fixtures
  - Code example:
    ```python
    # tests/conftest.py
    import pytest
    import asyncio
    from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
    from redis.asyncio import Redis
    from qdrant_client import QdrantClient

    @pytest.fixture(scope="session")
    def event_loop():
        """Create event loop for async tests."""
        loop = asyncio.get_event_loop_policy().new_event_loop()
        yield loop
        loop.close()

    @pytest.fixture
    async def db_session():
        """Provide clean database session for each test."""
        engine = create_async_engine("postgresql+asyncpg://octollm:test@localhost/test_octollm")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        async with AsyncSession(engine) as session:
            yield session

        await engine.dispose()

    @pytest.fixture
    async def redis_client():
        """Provide Redis client with test namespace."""
        client = Redis.from_url("redis://localhost:6379/15")  # Test DB 15
        yield client
        await client.flushdb()  # Clean up after test
        await client.close()

    @pytest.fixture
    def mock_llm(monkeypatch):
        """Mock LLM API calls."""
        async def mock_completion(*args, **kwargs):
            return {
                "choices": [{"message": {"content": "Mocked response"}}],
                "usage": {"total_tokens": 100}
            }

        monkeypatch.setattr("openai.AsyncOpenAI.chat.completions.create", mock_completion)
    ```
  - Files to create: `tests/conftest.py`

- [ ] **Implement Mocking Strategies** (2 hours)
  - httpx-mock for external API calls
  - pytest-mock for function mocking
  - unittest.mock for class mocking
  - Files to create: `tests/utils/mocks.py`

- [ ] **Set Up Coverage Reporting** (1 hour)
  - pytest-cov configuration
  - HTML reports
  - Codecov integration
  - Files to update: `pytest.ini`, `.github/workflows/test.yml`

#### Rust Testing Setup (4 hours)

- [ ] **Configure cargo test** (1 hour)
  - Test organization (unit tests inline, integration tests in tests/)
  - Doctest examples
  - Code example:
    ```toml
    # Cargo.toml
    [dev-dependencies]
    tokio-test = "0.4"
    mockall = "0.12"
    proptest = "1.4"
    ```

- [ ] **Create Test Utilities** (2 hours)
  - Mock Redis client
  - Test fixtures
  - Code example:
    ```rust
    // reflex-layer/tests/common/mod.rs
    use redis::{Client, Connection};
    use mockall::predicate::*;
    use mockall::mock;

    mock! {
        pub RedisClient {}

        impl redis::ConnectionLike for RedisClient {
            fn req_command(&mut self, cmd: &redis::Cmd) -> redis::RedisResult<redis::Value>;
        }
    }

    pub fn setup_test_redis() -> MockRedisClient {
        let mut mock = MockRedisClient::new();
        mock.expect_req_command()
            .returning(|_| Ok(redis::Value::Okay));
        mock
    }
    ```
  - Files to create: `reflex-layer/tests/common/mod.rs`

- [ ] **Add Integration Tests** (1 hour)
  - Test full request processing pipeline
  - Test PII detection accuracy
  - Files to create: `reflex-layer/tests/integration_test.rs`

### Success Criteria

- [ ] All test suites run in CI
- [ ] Coverage targets met (85% Python, 80% Rust)
- [ ] Mocking strategies documented
- [ ] Test fixtures reusable across projects
- [ ] Testing best practices documented

### Estimated Effort

- Development: 12 hours
- Testing: 2 hours
- Documentation: 2 hours
- **Total**: 16 hours (~1 week for 2 engineers)

---

## Sprint 4.3: Documentation Generation [Week 19-20]

**(Abbreviated for space - full version would be 800-1,000 lines)**

### Sprint Goals

- Auto-generate API documentation (OpenAPI for FastAPI)
- Generate Rust documentation (cargo doc)
- Create architecture diagrams (Mermaid in markdown)
- Generate component READMEs from templates
- Create runbook templates

### Key Tasks (Summary)

1. OpenAPI Documentation (Swagger UI, ReDoc)
2. Rust Documentation (cargo doc, doc comments)
3. Architecture Diagrams (Mermaid.js integration)
4. Component README Generation
5. Runbook Templates

### Estimated Effort: 12 hours

---

## Sprint 4.4: Developer Workflows [Week 20-21]

**(Abbreviated for space - full version would be 800-1,000 lines)**

### Sprint Goals

- Create PR templates with comprehensive checklists
- Set up code review automation (danger.js, reviewdog)
- Enforce branching strategy
- Automate release process (semantic versioning, changelog)
- Create developer onboarding guide

### Key Tasks (Summary)

1. PR Templates (checklist: testing, docs, changelog)
2. Code Review Automation (automated checks, review comments)
3. Branching Strategy Enforcement
4. Release Automation (semantic-release, changelog generation)
5. Developer Onboarding Guide

### Estimated Effort: 14 hours

---

## Sprint 4.5: Performance Benchmarking [Week 21-22]

**(Abbreviated for space - full version would be 600-800 lines)**

### Sprint Goals

- Set up benchmark suite (criterion for Rust, pytest-benchmark for Python)
- Integrate profiling tools (py-spy, perf, flamegraph)
- Implement performance regression detection
- Document critical performance paths
- Create performance optimization guide

### Key Tasks (Summary)

1. Benchmark Suite (criterion, pytest-benchmark)
2. Profiling Tools Integration (py-spy, cargo flamegraph)
3. Performance Regression Detection (track over time)
4. Critical Path Documentation
5. Optimization Guide

### Estimated Effort: 10 hours

---

## Phase 4 Summary

**Total Tasks**: 30+ engineering tasks across 5 sprints
**Estimated Duration**: 3-4 weeks with 2-3 engineers
**Total Estimated Hours**: ~70 hours development + ~10 hours testing + ~10 hours documentation = 90 hours

**Deliverables**:
- Code quality standards enforced (Python + Rust)
- Comprehensive testing infrastructure
- Auto-generated documentation
- Streamlined developer workflows
- Performance benchmarking suite

**Completion Checklist**:
- [ ] Code quality standards enforced in CI
- [ ] Test coverage targets met (85% Python, 80% Rust)
- [ ] Documentation auto-generated
- [ ] Release process automated
- [ ] Performance benchmarks established
- [ ] All team members trained on workflows

**Next Phase**: Phase 5 (Security Hardening)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-10
**Maintained By**: OctoLLM Project Management Team
