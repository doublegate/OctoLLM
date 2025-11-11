# Testing Guide for OctoLLM

**Document**: Implementation Guide
**Version**: 1.0
**Last Updated**: 2025-11-10
**Estimated Time**: 45-60 minutes

[← Back to Documentation](../README.md) | [Implementation Guides](./README.md)

---

## Table of Contents

1. [Overview](#overview)
   - [Testing Philosophy](#testing-philosophy)
   - [Test Pyramid](#test-pyramid)
   - [Coverage Goals](#coverage-goals)
2. [Setup](#setup)
   - [Testing Dependencies](#testing-dependencies)
   - [Test Environment](#test-environment)
   - [Fixtures](#fixtures)
3. [Unit Testing](#unit-testing)
   - [Testing Pydantic Models](#testing-pydantic-models)
   - [Testing Business Logic](#testing-business-logic)
   - [Mocking External Dependencies](#mocking-external-dependencies)
4. [Integration Testing](#integration-testing)
   - [Testing API Endpoints](#testing-api-endpoints)
   - [Testing Database Integration](#testing-database-integration)
   - [Testing Arm Communication](#testing-arm-communication)
5. [End-to-End Testing](#end-to-end-testing)
   - [Complete Workflow Tests](#complete-workflow-tests)
   - [Multi-Component Tests](#multi-component-tests)
6. [Performance Testing](#performance-testing)
   - [Load Testing](#load-testing)
   - [Latency Testing](#latency-testing)
7. [Security Testing](#security-testing)
   - [Input Validation](#input-validation)
   - [Authentication](#authentication)
8. [Running Tests](#running-tests)
   - [Local Execution](#local-execution)
   - [CI/CD Integration](#cicd-integration)
9. [Best Practices](#best-practices)

---

## Overview

Comprehensive testing ensures OctoLLM components work correctly in isolation and together. This guide covers all testing levels from unit to end-to-end.

### Testing Philosophy

OctoLLM follows these testing principles:

1. **Test Behavior, Not Implementation**: Focus on what components do, not how
2. **Fast Feedback**: Unit tests run in < 1s, integration in < 10s
3. **Reliable**: Tests are deterministic and don't flake
4. **Maintainable**: Tests are clear, well-documented, and easy to update
5. **Comprehensive**: Critical paths have 100% coverage

### Test Pyramid

```mermaid
graph TD
    subgraph "Test Pyramid"
        E2E[E2E Tests<br/>10%<br/>Slow, Comprehensive]
        INT[Integration Tests<br/>30%<br/>Medium Speed]
        UNIT[Unit Tests<br/>60%<br/>Fast, Focused]
    end

    UNIT --> INT
    INT --> E2E

    style E2E fill:#ff9999
    style INT fill:#ffcc99
    style UNIT fill:#99ff99
```

**Target Distribution**:
- **60% Unit Tests**: Fast, focused on individual functions/classes
- **30% Integration Tests**: Test component interactions
- **10% E2E Tests**: Full system workflows

### Coverage Goals

| Component | Target Coverage | Current |
|-----------|----------------|---------|
| Orchestrator | 90% | - |
| Arms | 85% | - |
| Reflex Layer | 90% | - |
| Memory Systems | 85% | - |
| API Layer | 95% | - |

---

## Setup

### Testing Dependencies

**File**: `pyproject.toml` (testing section)

```toml
[tool.poetry.group.test]
optional = true

[tool.poetry.group.test.dependencies]
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"
pytest-xdist = "^3.5.0"  # Parallel execution
pytest-timeout = "^2.2.0"
httpx-mock = "^0.11.0"  # Mock HTTP
faker = "^20.1.0"  # Generate test data
factory-boy = "^3.3.0"  # Model factories
freezegun = "^1.4.0"  # Time mocking
respx = "^0.20.2"  # HTTP mocking for httpx

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
markers = [
    "unit: Unit tests",
    "integration: Integration tests",
    "e2e: End-to-end tests",
    "slow: Slow tests (> 1s)",
    "security: Security tests"
]
timeout = 10  # Default timeout per test
```

**Install test dependencies**:

```bash
poetry install --with test
```

### Test Environment

**File**: `tests/.env.test`

```bash
# Test environment configuration
POSTGRES_URL=postgresql://postgres:password@localhost:5432/octollm_test
REDIS_URL=redis://localhost:6379/15
QDRANT_URL=http://localhost:6333

# Use mock LLM for tests
OPENAI_API_KEY=test-key
USE_MOCK_LLM=true

# Fast settings for tests
CACHE_TTL_SECONDS=10
TASK_TIMEOUT_SECONDS=30
```

### Fixtures

**File**: `tests/conftest.py`

```python
"""Pytest fixtures for OctoLLM tests."""

import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
import asyncpg
import redis.asyncio as redis
from unittest.mock import AsyncMock, Mock

from orchestrator.main import app
from orchestrator.config import settings


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_pool() -> AsyncGenerator[asyncpg.Pool, None]:
    """PostgreSQL connection pool for tests."""
    pool = await asyncpg.create_pool(settings.postgres_url)

    # Clean database before test
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE entities, relationships CASCADE")

    yield pool

    await pool.close()


@pytest.fixture
async def redis_client() -> AsyncGenerator[redis.Redis, None]:
    """Redis client for tests."""
    client = await redis.from_url(settings.redis_url)

    # Flush test database
    await client.flushdb()

    yield client

    await client.close()


@pytest.fixture
async def http_client() -> AsyncGenerator[AsyncClient, None]:
    """HTTP client for API tests."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    client = AsyncMock()

    # Mock chat completion
    client.chat.completions.create.return_value = Mock(
        choices=[
            Mock(
                message=Mock(
                    content='{"goal": "test goal", "domain": "code", "complexity": "simple", "constraints": [], "keywords": [], "entities": {}}'
                )
            )
        ]
    )

    return client


@pytest.fixture
def mock_arm_registry():
    """Mock arm registry."""
    return {
        "coder-001": {
            "arm_type": "coder",
            "endpoint": "http://coder-arm:8080/execute",
            "capabilities": ["code_generation", "refactoring"],
            "cost_tier": 4,
            "status": "healthy"
        },
        "executor-001": {
            "arm_type": "executor",
            "endpoint": "http://executor-arm:8080/execute",
            "capabilities": ["shell", "http"],
            "cost_tier": 3,
            "status": "healthy"
        }
    }


@pytest.fixture
def sample_task_request():
    """Sample task request for tests."""
    from orchestrator.api.tasks import TaskRequest

    return TaskRequest(
        goal="Write a function to sort a list",
        constraints=["Use only Python standard library"],
        context={"language": "python"},
        priority="medium",
        budget={
            "max_tokens": 2000,
            "max_time_seconds": 30
        }
    )
```

---

## Unit Testing

### Testing Pydantic Models

**File**: `tests/unit/test_models.py`

```python
"""Unit tests for Pydantic models."""

import pytest
from pydantic import ValidationError
from uuid import uuid4

from orchestrator.models import TaskContract, Priority


class TestTaskContract:
    """Test TaskContract validation."""

    def test_valid_task_contract(self):
        """Test valid task contract creation."""
        task = TaskContract(
            task_id=f"task-{uuid4()}",
            goal="Write a function to sort a list",
            constraints=["Use Python 3.11+"],
            priority=Priority.MEDIUM
        )

        assert task.task_id.startswith("task-")
        assert len(task.goal) >= 10
        assert task.priority == Priority.MEDIUM

    def test_task_id_validation(self):
        """Test task ID format validation."""
        with pytest.raises(ValidationError) as exc_info:
            TaskContract(
                task_id="invalid-format",  # Should be task-{uuid}
                goal="Test goal"
            )

        assert "task_id" in str(exc_info.value)

    def test_goal_length_validation(self):
        """Test goal length constraints."""
        # Too short
        with pytest.raises(ValidationError):
            TaskContract(
                task_id=f"task-{uuid4()}",
                goal="Short"  # Less than 10 chars
            )

        # Too long
        with pytest.raises(ValidationError):
            TaskContract(
                task_id=f"task-{uuid4()}",
                goal="a" * 2001  # More than 2000 chars
            )

    def test_constraints_max_items(self):
        """Test constraints list max items."""
        with pytest.raises(ValidationError):
            TaskContract(
                task_id=f"task-{uuid4()}",
                goal="Test goal",
                constraints=["constraint"] * 21  # Max 20
            )

    def test_default_values(self):
        """Test default values are applied."""
        task = TaskContract(
            task_id=f"task-{uuid4()}",
            goal="Test goal"
        )

        assert task.priority == Priority.MEDIUM
        assert task.budget["max_tokens"] == 4000
        assert task.budget["max_time_seconds"] == 30
        assert task.constraints == []
```

### Testing Business Logic

**File**: `tests/unit/test_intent_parser.py`

```python
"""Unit tests for intent parser."""

import pytest
from unittest.mock import AsyncMock, Mock, patch

from orchestrator.core.intent_parser import IntentParser, ParsedIntent


@pytest.mark.unit
class TestIntentParser:
    """Test IntentParser functionality."""

    @pytest.fixture
    def parser(self, mock_openai_client):
        """Create parser with mocked OpenAI client."""
        parser = IntentParser(openai_api_key="test-key")
        parser.client = mock_openai_client
        return parser

    @pytest.mark.asyncio
    async def test_parse_simple_request(self, parser, mock_openai_client):
        """Test parsing simple user request."""
        # Setup mock response
        mock_openai_client.chat.completions.create.return_value = Mock(
            choices=[
                Mock(
                    message=Mock(
                        content='''{
                            "goal": "Write a sorting function",
                            "domain": "code",
                            "complexity": "simple",
                            "constraints": ["Use Python"],
                            "keywords": ["sort", "function"],
                            "entities": {"language": ["Python"]}
                        }'''
                    )
                )
            ]
        )

        # Execute
        intent = await parser.parse("Write a function to sort a list")

        # Verify
        assert intent.goal == "Write a sorting function"
        assert intent.domain == "code"
        assert intent.complexity == "simple"
        assert "Use Python" in intent.constraints
        assert "sort" in intent.keywords

        # Verify LLM was called
        mock_openai_client.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_parse_complex_request_with_constraints(self, parser):
        """Test parsing complex request with multiple constraints."""
        request = """
        Find and fix the authentication bug in auth/login.py.
        Requirements:
        - Don't modify database schema
        - Complete within 5 minutes
        - Add tests for the fix
        """

        intent = await parser.parse(request)

        assert intent.complexity in ["medium", "complex"]
        assert len(intent.constraints) > 0

    @pytest.mark.asyncio
    async def test_parse_handles_llm_errors(self, parser, mock_openai_client):
        """Test graceful handling of LLM errors."""
        # Setup mock to raise error
        mock_openai_client.chat.completions.create.side_effect = Exception("API Error")

        # Should raise exception
        with pytest.raises(Exception) as exc_info:
            await parser.parse("Test request")

        assert "API Error" in str(exc_info.value)
```

### Mocking External Dependencies

**File**: `tests/unit/test_arm_router.py`

```python
"""Unit tests for arm router."""

import pytest
from orchestrator.core.arm_router import ArmRouter, ArmScore


@pytest.mark.unit
class TestArmRouter:
    """Test ArmRouter arm selection logic."""

    @pytest.fixture
    def router(self, mock_arm_registry):
        """Create router with mock registry."""
        return ArmRouter(arm_registry=mock_arm_registry)

    @pytest.mark.asyncio
    async def test_route_selects_matching_arm(self, router):
        """Test router selects arm with matching capabilities."""
        selected = await router.route(
            task_type="coder",
            required_capabilities=["code_generation"],
            priority="medium"
        )

        assert selected == "coder-001"

    @pytest.mark.asyncio
    async def test_route_returns_none_for_no_match(self, router):
        """Test router returns None when no arm matches."""
        selected = await router.route(
            task_type="nonexistent",
            required_capabilities=["unknown"],
            priority="low"
        )

        assert selected is None

    def test_score_arm_capability_matching(self, router):
        """Test capability matching scoring."""
        score = router._score_arm(
            arm_id="coder-001",
            required_capabilities=["code_generation", "refactoring"],
            priority="medium"
        )

        # Both capabilities match
        assert score.capability_match == 1.0
        assert score.total_score > 0.5

    def test_score_arm_partial_match(self, router):
        """Test scoring with partial capability match."""
        score = router._score_arm(
            arm_id="coder-001",
            required_capabilities=["code_generation", "unknown_capability"],
            priority="medium"
        )

        # Only one of two capabilities match
        assert score.capability_match == 0.5

    def test_update_stats_tracks_success(self, router):
        """Test statistics tracking."""
        # Record successes and failures
        router.update_stats("coder-001", success=True)
        router.update_stats("coder-001", success=True)
        router.update_stats("coder-001", success=False)

        stats = router.historical_stats["coder-001"]
        assert stats["total"] == 3
        assert stats["success"] == 2
```

---

## Integration Testing

### Testing API Endpoints

**File**: `tests/integration/test_api.py`

```python
"""Integration tests for API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestTaskAPI:
    """Test task API endpoints."""

    @pytest.mark.asyncio
    async def test_submit_task_success(self, http_client, sample_task_request):
        """Test successful task submission."""
        response = await http_client.post(
            "/api/v1/tasks",
            json=sample_task_request.dict()
        )

        assert response.status_code == 202
        data = response.json()
        assert "task_id" in data
        assert data["status"] == "accepted"
        assert data["task_id"].startswith("task-")

    @pytest.mark.asyncio
    async def test_submit_task_validation_error(self, http_client):
        """Test task submission with invalid data."""
        response = await http_client.post(
            "/api/v1/tasks",
            json={
                "goal": "Short",  # Too short
                "priority": "invalid"
            }
        )

        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_get_task_status(self, http_client, sample_task_request):
        """Test retrieving task status."""
        # Submit task
        submit_response = await http_client.post(
            "/api/v1/tasks",
            json=sample_task_request.dict()
        )
        task_id = submit_response.json()["task_id"]

        # Get status
        status_response = await http_client.get(f"/api/v1/tasks/{task_id}")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["task_id"] == task_id
        assert "status" in data

    @pytest.mark.asyncio
    async def test_get_nonexistent_task(self, http_client):
        """Test getting status of nonexistent task."""
        response = await http_client.get("/api/v1/tasks/task-nonexistent")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_task(self, http_client, sample_task_request):
        """Test task cancellation."""
        # Submit task
        submit_response = await http_client.post(
            "/api/v1/tasks",
            json=sample_task_request.dict()
        )
        task_id = submit_response.json()["task_id"]

        # Cancel task
        cancel_response = await http_client.post(f"/api/v1/tasks/{task_id}/cancel")

        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] == "cancelled"
```

### Testing Database Integration

**File**: `tests/integration/test_database.py`

```python
"""Integration tests for database operations."""

import pytest
from orchestrator.memory.global_memory import GlobalMemoryClient


@pytest.mark.integration
class TestGlobalMemory:
    """Test PostgreSQL knowledge graph operations."""

    @pytest.mark.asyncio
    async def test_create_entity(self, db_pool):
        """Test entity creation."""
        memory = GlobalMemoryClient(pool=db_pool)

        entity_id = await memory.entity_create(
            entity_type="function",
            name="sort_list",
            properties={"language": "python", "complexity": "O(n log n)"}
        )

        assert entity_id is not None

        # Verify entity exists
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM entities WHERE id = $1",
                entity_id
            )
            assert row["name"] == "sort_list"
            assert row["entity_type"] == "function"

    @pytest.mark.asyncio
    async def test_create_relationship(self, db_pool):
        """Test relationship creation."""
        memory = GlobalMemoryClient(pool=db_pool)

        # Create two entities
        entity1_id = await memory.entity_create("function", "func_a", {})
        entity2_id = await memory.entity_create("function", "func_b", {})

        # Create relationship
        await memory.relationship_create(
            from_entity_id=entity1_id,
            to_entity_id=entity2_id,
            relationship_type="calls",
            properties={"frequency": "often"}
        )

        # Verify relationship
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT * FROM relationships
                WHERE from_entity_id = $1 AND to_entity_id = $2
                """,
                entity1_id,
                entity2_id
            )
            assert row["relationship_type"] == "calls"

    @pytest.mark.asyncio
    async def test_graph_query(self, db_pool):
        """Test graph traversal query."""
        memory = GlobalMemoryClient(pool=db_pool)

        # Build small graph: A -> B -> C
        a_id = await memory.entity_create("node", "A", {})
        b_id = await memory.entity_create("node", "B", {})
        c_id = await memory.entity_create("node", "C", {})

        await memory.relationship_create(a_id, b_id, "links_to")
        await memory.relationship_create(b_id, c_id, "links_to")

        # Query from A
        subgraph = await memory.graph_query(
            entity_id=a_id,
            relationship_type="links_to",
            max_depth=2
        )

        # Should find A, B, and C
        assert len(subgraph) == 3
```

---

## End-to-End Testing

### Complete Workflow Tests

**File**: `tests/e2e/test_complete_workflow.py`

```python
"""End-to-end tests for complete workflows."""

import pytest
from httpx import AsyncClient
import asyncio


@pytest.mark.e2e
@pytest.mark.slow
class TestCompleteWorkflow:
    """Test complete task execution workflows."""

    @pytest.mark.asyncio
    async def test_simple_code_generation_workflow(self, http_client):
        """Test complete workflow: submit → execute → validate → complete."""

        # 1. Submit task
        submit_response = await http_client.post(
            "/api/v1/tasks",
            json={
                "goal": "Write a function to calculate factorial",
                "constraints": ["Use Python", "Include docstring"],
                "priority": "medium"
            }
        )

        assert submit_response.status_code == 202
        task_id = submit_response.json()["task_id"]

        # 2. Poll for completion (max 30 seconds)
        max_wait = 30
        poll_interval = 1
        elapsed = 0

        while elapsed < max_wait:
            status_response = await http_client.get(f"/api/v1/tasks/{task_id}")
            status = status_response.json()

            if status["status"] == "completed":
                # 3. Verify result
                assert "result" in status
                assert status["result"]["success"] is True

                # Verify code was generated
                assert "code" in status["result"]
                code = status["result"]["code"]
                assert "factorial" in code.lower()
                assert "def " in code

                return  # Success

            elif status["status"] == "failed":
                pytest.fail(f"Task failed: {status.get('error')}")

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        pytest.fail(f"Task did not complete within {max_wait} seconds")

    @pytest.mark.asyncio
    async def test_multi_step_workflow_with_retrieval(self, http_client):
        """Test workflow requiring research → code → validate."""

        submit_response = await http_client.post(
            "/api/v1/tasks",
            json={
                "goal": "Create a Flask app with user authentication",
                "constraints": ["Use bcrypt for passwords", "Include error handling"],
                "priority": "high"
            }
        )

        task_id = submit_response.json()["task_id"]

        # Wait for completion
        final_status = await self._wait_for_completion(http_client, task_id, timeout=60)

        # Verify multi-step execution
        assert "execution_steps" in final_status
        steps = final_status["execution_steps"]

        # Should have research, code generation, and validation steps
        assert len(steps) >= 3
        assert any("research" in step["arm_type"] for step in steps)
        assert any("coder" in step["arm_type"] for step in steps)
        assert any("judge" in step["arm_type"] for step in steps)

    async def _wait_for_completion(
        self,
        client: AsyncClient,
        task_id: str,
        timeout: int = 60
    ) -> dict:
        """Helper to wait for task completion."""
        elapsed = 0
        poll_interval = 2

        while elapsed < timeout:
            response = await client.get(f"/api/v1/tasks/{task_id}")
            status = response.json()

            if status["status"] in ["completed", "failed"]:
                return status

            await asyncio.sleep(poll_interval)
            elapsed += poll_interval

        raise TimeoutError(f"Task {task_id} did not complete within {timeout}s")
```

---

## Performance Testing

### Load Testing

**File**: `tests/performance/test_load.py`

```python
"""Load tests for orchestrator."""

import pytest
import asyncio
from httpx import AsyncClient


@pytest.mark.slow
class TestLoad:
    """Test system under load."""

    @pytest.mark.asyncio
    async def test_concurrent_task_submission(self):
        """Test submitting many tasks concurrently."""
        num_tasks = 100

        async with AsyncClient(base_url="http://localhost:8000") as client:
            # Submit tasks concurrently
            tasks = [
                client.post(
                    "/api/v1/tasks",
                    json={
                        "goal": f"Test task {i}",
                        "priority": "low"
                    }
                )
                for i in range(num_tasks)
            ]

            responses = await asyncio.gather(*tasks)

            # Verify all succeeded
            success_count = sum(1 for r in responses if r.status_code == 202)
            assert success_count == num_tasks

    @pytest.mark.asyncio
    async def test_sustained_load(self):
        """Test system under sustained load."""
        duration_seconds = 60
        requests_per_second = 10

        start_time = asyncio.get_event_loop().time()
        end_time = start_time + duration_seconds

        completed = 0
        failed = 0

        async with AsyncClient(base_url="http://localhost:8000") as client:
            while asyncio.get_event_loop().time() < end_time:
                try:
                    response = await client.post(
                        "/api/v1/tasks",
                        json={"goal": "Sustained load test task"},
                        timeout=5.0
                    )

                    if response.status_code == 202:
                        completed += 1
                    else:
                        failed += 1

                except Exception:
                    failed += 1

                await asyncio.sleep(1.0 / requests_per_second)

        # Success rate should be > 95%
        success_rate = completed / (completed + failed)
        assert success_rate > 0.95
```

---

## Running Tests

### Local Execution

**Run all tests**:
```bash
pytest
```

**Run with coverage**:
```bash
pytest --cov=orchestrator --cov-report=html --cov-report=term
```

**Run specific test types**:
```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests
pytest -m integration

# E2E tests
pytest -m e2e

# Exclude slow tests
pytest -m "not slow"
```

**Run in parallel**:
```bash
pytest -n auto  # Use all CPU cores
pytest -n 4     # Use 4 workers
```

**Run with verbose output**:
```bash
pytest -v  # Verbose
pytest -vv  # Extra verbose
pytest -s   # Show print statements
```

### CI/CD Integration

**File**: `.github/workflows/test.yml`

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: password
          POSTGRES_DB: octollm_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: |
          poetry install --with test

      - name: Run unit tests
        run: |
          poetry run pytest -m unit --cov=orchestrator --cov-report=xml

      - name: Run integration tests
        run: |
          poetry run pytest -m integration

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

---

## Best Practices

### 1. Test Naming

Use descriptive test names:

```python
# Good
def test_submit_task_with_invalid_goal_returns_422():
    ...

# Bad
def test_task():
    ...
```

### 2. Arrange-Act-Assert Pattern

Structure tests clearly:

```python
def test_example():
    # Arrange: Set up test data
    task = TaskRequest(goal="Test")

    # Act: Execute the code being tested
    result = orchestrator.execute(task)

    # Assert: Verify expectations
    assert result.status == "completed"
```

### 3. Use Factories for Test Data

```python
import factory

class TaskFactory(factory.Factory):
    class Meta:
        model = TaskContract

    task_id = factory.LazyFunction(lambda: f"task-{uuid4()}")
    goal = factory.Faker("sentence")
    priority = "medium"


# Usage
task = TaskFactory.create()
```

### 4. Test Edge Cases

```python
def test_task_with_empty_constraints():
    """Test task with no constraints."""
    ...

def test_task_with_max_constraints():
    """Test task with maximum allowed constraints (20)."""
    ...

def test_task_with_unicode_goal():
    """Test task with unicode characters in goal."""
    ...
```

### 5. Clean Up After Tests

```python
@pytest.fixture
async def clean_database(db_pool):
    """Clean database after test."""
    yield

    # Cleanup
    async with db_pool.acquire() as conn:
        await conn.execute("TRUNCATE entities CASCADE")
```

---

## Summary

This guide covered comprehensive testing for OctoLLM:

| Test Level | Coverage | Speed | Examples |
|------------|----------|-------|----------|
| Unit | 60% | < 1s | Models, parsers, routers |
| Integration | 30% | < 10s | APIs, databases, arms |
| E2E | 10% | < 60s | Complete workflows |

### Key Takeaways

1. **Test at all levels**: Unit, integration, and E2E
2. **Use fixtures**: Share setup code with pytest fixtures
3. **Mock external services**: Use mocks for LLMs, APIs
4. **Run tests in CI/CD**: Automate with GitHub Actions
5. **Measure coverage**: Target 85%+ for critical code
6. **Write clear tests**: Descriptive names, AAA pattern

### Next Steps

- [Debugging Guide](./debugging.md) - Debug failing tests
- [Integration Patterns](./integration-patterns.md) - Test integrations
- [CI/CD Setup](./ci-cd-setup.md) - Automate testing
- [Performance Testing](../testing/performance-tests.md) - Advanced performance tests

---

**Document Maintainers**: OctoLLM Core Team
**Last Updated**: 2025-11-10
**Next Review**: 2025-12-10
