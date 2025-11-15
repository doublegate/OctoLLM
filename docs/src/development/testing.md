# Testing

Comprehensive testing guide covering unit, integration, and end-to-end tests.

## Testing Strategy

OctoLLM uses a multi-layered testing approach:

1. **Unit Tests**: Component-level validation
2. **Integration Tests**: Service interaction validation
3. **End-to-End Tests**: Full workflow validation
4. **Performance Tests**: Latency and throughput benchmarks
5. **Security Tests**: Vulnerability scanning

See [Testing Strategy](../testing/strategy.md) for complete strategy documentation.

## Running Tests

### All Tests

```bash
# Run all tests
docker-compose run --rm orchestrator pytest

# With coverage
docker-compose run --rm orchestrator pytest --cov=octollm --cov-report=html
```

### Unit Tests

```bash
# All unit tests
pytest tests/unit/

# Specific module
pytest tests/unit/test_orchestrator.py

# Specific test
pytest tests/unit/test_orchestrator.py::test_task_creation
```

### Integration Tests

```bash
# Requires running services
docker-compose up -d postgres redis

# Run integration tests
pytest tests/integration/
```

### Coverage

```bash
# Generate coverage report
pytest --cov=octollm --cov-report=html --cov-report=term

# View HTML report
open htmlcov/index.html
```

## Test Organization

```
tests/
├── unit/              # Unit tests
│   ├── orchestrator/
│   ├── reflex/
│   └── arms/
├── integration/       # Integration tests
│   ├── api/
│   └── database/
├── e2e/              # End-to-end tests
├── performance/       # Performance benchmarks
└── security/         # Security tests
```

## Writing Tests

### Unit Test Example

```python
import pytest
from octollm.orchestrator import Orchestrator

def test_task_creation():
    """Test task creation with valid input."""
    orchestrator = Orchestrator()
    task = orchestrator.create_task(
        goal="Test goal",
        constraints={},
        context={},
        acceptance_criteria=["criterion1"]
    )
    assert task.task_id is not None
    assert task.goal == "Test goal"
```

### Integration Test Example

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_task_api_endpoint():
    """Test task creation via API."""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.post("/api/v1/tasks", json={
            "goal": "Test goal",
            "constraints": {},
            "context": {},
            "acceptance_criteria": ["criterion1"]
        })
        assert response.status_code == 201
        data = response.json()
        assert "task_id" in data
```

## Coverage Targets

| Component | Target | Current |
|-----------|--------|---------|
| Reflex Layer | >90% | 90%+ ✅ |
| Orchestrator | >85% | 85%+ ✅ |
| Arms | >85% | TBD |
| Overall | >85% | ~87% ✅ |

## See Also

- [Testing Strategy](../testing/strategy.md)
- [Testing Checklist](../project-tracking/testing-checklist.md)
- [Development Workflow](./workflow.md)
