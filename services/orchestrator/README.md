# Orchestrator Service

**Version**: 1.0.0 (Sprint 1.2)
**Status**: ✅ Production Ready (Phase 2 Complete)
**Last Updated**: 2025-11-15

The Orchestrator is the central "brain" of OctoLLM, responsible for task coordination, safety validation via the Reflex Layer, and (future) delegation to specialized arms.

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Docker (optional, for containerized deployment)

### Installation (Development)

```bash
# Navigate to orchestrator directory
cd services/orchestrator

# Install dependencies
pip install -e ".[dev]"

# Or use system Python with venv
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Configuration

Create a `.env` file in the `services/orchestrator/` directory:

```bash
# Database Configuration
ORCHESTRATOR_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/octollm

# Reflex Layer Integration
ORCHESTRATOR_REFLEX_URL=http://localhost:8080
ORCHESTRATOR_ENABLE_REFLEX_INTEGRATION=true

# Application Settings
ORCHESTRATOR_LOG_LEVEL=INFO
ORCHESTRATOR_HOST=0.0.0.0
ORCHESTRATOR_PORT=8000
```

**Environment Variable Reference**:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ORCHESTRATOR_DATABASE_URL` | ✅ Yes | - | PostgreSQL connection URL (must use `postgresql+asyncpg://`) |
| `ORCHESTRATOR_REFLEX_URL` | No | `http://localhost:8080` | Reflex Layer service URL |
| `ORCHESTRATOR_ENABLE_REFLEX_INTEGRATION` | No | `true` | Enable/disable Reflex Layer safety checks |
| `ORCHESTRATOR_LOG_LEVEL` | No | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ORCHESTRATOR_HOST` | No | `0.0.0.0` | Server bind address |
| `ORCHESTRATOR_PORT` | No | `8000` | Server port |

### Running the Service

```bash
# Development mode (auto-reload enabled)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Docker Deployment

```bash
# Build image
docker build -t octollm-orchestrator:latest .

# Run container
docker run -d \
  --name octollm-orchestrator \
  -p 8000:8000 \
  -e ORCHESTRATOR_DATABASE_URL=postgresql+asyncpg://user:password@db:5432/octollm \
  -e ORCHESTRATOR_REFLEX_URL=http://reflex:8080 \
  octollm-orchestrator:latest
```

## Architecture Overview

### Sprint 1.2 Implementation

```
┌─────────────┐
│  User/API   │
└──────┬──────┘
       │ HTTP
       v
┌─────────────────────────────────────────┐
│       Orchestrator Service (FastAPI)    │
│                                         │
│  POST /submit  ──┐                      │
│  GET /tasks/{id} │                      │
│  GET /health     ├─> FastAPI Server     │
│  GET /ready      │   (app/main.py)      │
│  GET /metrics    │                      │
│  GET /           │                      │
│                  │                      │
│                  v                      │
│          ┌──────────────┐               │
│          │ Config Mgmt  │               │
│          │(app/config.py)               │
│          └──────┬───────┘               │
│                 │                       │
│        ┌────────┴────────┐              │
│        v                 v              │
│  ┌──────────┐     ┌─────────────┐      │
│  │  Reflex  │     │  Database   │      │
│  │  Client  │     │   Layer     │      │
│  │  (Circuit│     │(Async CRUD) │      │
│  │  Breaker)│     └──────┬──────┘      │
│  └────┬─────┘            │              │
│       │                  │              │
└───────┼──────────────────┼──────────────┘
        │                  │
        v                  v
┌──────────────┐    ┌─────────────┐
│ Reflex Layer │    │ PostgreSQL  │
│   Service    │    │  Database   │
│ (Port 8080)  │    └─────────────┘
└──────────────┘
```

### Key Components

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| **FastAPI Server** | `app/main.py` | 486 | HTTP API with 6 endpoints |
| **Reflex Client** | `app/reflex_client.py` | 504 | Reflex Layer integration (circuit breaker, retry) |
| **Database Layer** | `app/database.py` | 383 | Async SQLAlchemy CRUD operations |
| **Data Models** | `app/models.py` | 255 | Pydantic + SQLAlchemy ORM models |
| **Configuration** | `app/config.py` | 148 | Environment-based settings management |

**Total**: ~1,776 lines of production code + ~2,900 lines of tests

## API Reference

### Base URL

```
http://localhost:8000
```

### Endpoints

#### 1. Submit Task

**POST** `/submit`

Submit a new task with safety validation via Reflex Layer.

**Request Body**:
```json
{
  "goal": "Analyze sentiment of user reviews",
  "constraints": ["No PII in output", "Complete within 5 minutes"],
  "context": {
    "user_id": "user123",
    "source": "web_app"
  },
  "acceptance_criteria": ["Sentiment score between -1 and 1"],
  "priority": "high",
  "budget": {
    "max_cost_usd": 0.50,
    "max_time_seconds": 300,
    "max_tokens": 2000
  }
}
```

**Response** (200 OK):
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "goal": "Analyze sentiment of user reviews",
  "status": "pending",
  "priority": "high",
  "created_at": "2025-11-15T12:00:00Z",
  "metadata": {
    "user_id": "user123",
    "source": "web_app"
  }
}
```

**Error Response** (403 Forbidden - Safety Check Failed):
```json
{
  "detail": "Safety check failed: PII detected in input"
}
```

#### 2. Get Task Status

**GET** `/tasks/{task_id}`

Retrieve task details and current status.

**Response** (200 OK):
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "goal": "Analyze sentiment of user reviews",
  "status": "completed",
  "priority": "high",
  "created_at": "2025-11-15T12:00:00Z",
  "updated_at": "2025-11-15T12:05:30Z",
  "metadata": {
    "user_id": "user123",
    "source": "web_app"
  }
}
```

**Error Response** (404 Not Found):
```json
{
  "detail": "Task not found"
}
```

#### 3. Health Check

**GET** `/health`

Basic health check endpoint.

**Response** (200 OK):
```json
{
  "status": "healthy"
}
```

#### 4. Readiness Check

**GET** `/ready`

Check if service is ready to accept traffic (database + Reflex Layer connectivity).

**Response** (200 OK):
```json
{
  "status": "ready",
  "database": "connected",
  "reflex_layer": "available"
}
```

**Response** (503 Service Unavailable):
```json
{
  "status": "not_ready",
  "database": "disconnected",
  "reflex_layer": "unavailable"
}
```

#### 5. Metrics

**GET** `/metrics`

Prometheus metrics endpoint.

**Response** (200 OK - Prometheus text format):
```
# HELP octollm_orchestrator_tasks_total Total number of tasks submitted
# TYPE octollm_orchestrator_tasks_total counter
octollm_orchestrator_tasks_total{status="pending"} 42
octollm_orchestrator_tasks_total{status="completed"} 38

# HELP octollm_orchestrator_reflex_calls_total Reflex Layer API calls
# TYPE octollm_orchestrator_reflex_calls_total counter
octollm_orchestrator_reflex_calls_total{result="safe"} 75
octollm_orchestrator_reflex_calls_total{result="blocked"} 5
```

#### 6. Root

**GET** `/`

Service information and version.

**Response** (200 OK):
```json
{
  "service": "OctoLLM Orchestrator",
  "version": "1.0.0",
  "status": "operational"
}
```

### API Authentication (Future)

Sprint 1.2 does not include authentication. Future sprints will add:
- JWT-based authentication
- API key management
- Rate limiting per client

## Data Models

### TaskStatus Enum

- `pending` - Task submitted, awaiting processing
- `processing` - Task currently being executed
- `completed` - Task finished successfully
- `failed` - Task execution failed
- `cancelled` - Task cancelled by user

### Priority Enum

- `low` - Non-urgent tasks
- `medium` - Standard priority (default)
- `high` - High-priority tasks
- `critical` - Time-sensitive tasks

### TaskRequest (Pydantic)

```python
{
  "goal": str,                           # Required: Task description
  "constraints": List[str] = [],         # Optional: Hard constraints
  "context": Dict[str, Any] = {},        # Optional: Background info
  "acceptance_criteria": List[str] = [], # Optional: Success conditions
  "priority": Priority = "medium",       # Optional: Task priority
  "budget": ResourceBudget = None        # Optional: Resource limits
}
```

### ResourceBudget (Pydantic)

```python
{
  "max_cost_usd": float = 1.0,          # Maximum cost in USD
  "max_time_seconds": int = 600,        # Maximum execution time
  "max_tokens": int = 10000             # Maximum LLM tokens
}
```

## Database Schema

### Tables

#### `tasks` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Task identifier |
| `goal` | VARCHAR | NOT NULL | Task description |
| `status` | ENUM | NOT NULL, DEFAULT 'pending' | Current task status |
| `priority` | ENUM | NOT NULL, DEFAULT 'medium' | Task priority |
| `constraints` | JSONB | DEFAULT '[]' | Task constraints |
| `context` | JSONB | DEFAULT '{}' | Background information |
| `acceptance_criteria` | JSONB | DEFAULT '[]' | Success criteria |
| `task_metadata` | JSONB | DEFAULT '{}' | Additional metadata |
| `assigned_arm` | VARCHAR | NULLABLE | Target arm (future) |
| `max_cost_usd` | DECIMAL | DEFAULT 1.0 | Cost budget |
| `max_time_seconds` | INTEGER | DEFAULT 600 | Time budget |
| `max_tokens` | INTEGER | DEFAULT 10000 | Token budget |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Creation timestamp |
| `updated_at` | TIMESTAMP | DEFAULT NOW() | Last update timestamp |

#### `task_results` Table

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Result identifier |
| `task_id` | UUID | FOREIGN KEY → tasks.id | Associated task |
| `result_data` | JSONB | NOT NULL | Result payload |
| `confidence` | DECIMAL | CHECK 0.0-1.0 | Confidence score |
| `created_at` | TIMESTAMP | DEFAULT NOW() | Result timestamp |

**Indexes**:
- `idx_tasks_status` on `tasks(status)` - Fast status queries
- `idx_tasks_created_at` on `tasks(created_at)` - Chronological ordering
- `idx_task_results_task_id` on `task_results(task_id)` - Result lookups

## Testing

### Running Tests

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html

# Run specific test file
pytest tests/test_models.py -v

# Run tests matching pattern
pytest tests/ -k "test_database" -v
```

### Test Coverage (Sprint 1.2)

| Module | Tests | Coverage |
|--------|-------|----------|
| `app/reflex_client.py` | 39 | 97% |
| `app/models.py` | 34 | 92% |
| `app/config.py` | 26 | 88% |
| `app/database.py` | 27 | 85% |
| **Total** | **87** | **85%+** |

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── test_reflex_client.py    # Reflex Layer integration tests
├── test_models.py           # Pydantic + ORM model tests
├── test_config.py           # Configuration validation tests
└── test_database.py         # Database CRUD operation tests
```

### Key Fixtures

```python
@pytest.fixture
async def db():
    """Async SQLite database for testing."""
    # Creates in-memory database
    # Yields Database instance
    # Cleans up after test

@pytest.fixture
def sample_task_contract():
    """Sample TaskContract for testing."""
    return TaskContract(
        task_id=str(uuid.uuid4()),
        goal="Test goal",
        # ... other fields
    )
```

## Performance Targets

| Metric | Target | Sprint 1.2 Status |
|--------|--------|-------------------|
| API Endpoint Latency (P95) | <500ms | ✅ <100ms (without LLM) |
| Database Query Latency (P95) | <10ms | ✅ <5ms (async SQLAlchemy) |
| Reflex Layer Call Latency (P95) | <100ms | ✅ Achieved with circuit breaker |
| Concurrent Requests | 50+/instance | ⏳ Load testing in Sprint 1.3 |
| Task Success Rate | >95% | ⏳ Requires full pipeline |

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

**Error**: `asyncpg.exceptions.InvalidCatalogNameError: database "octollm" does not exist`

**Solution**:
```bash
# Create database
createdb octollm

# Or use psql
psql -U postgres -c "CREATE DATABASE octollm;"
```

#### 2. Reflex Layer Unavailable

**Error**: `CircuitBreakerOpen: Reflex Layer unavailable`

**Solution**:
```bash
# Check Reflex Layer status
curl http://localhost:8080/health

# Temporarily disable Reflex integration
export ORCHESTRATOR_ENABLE_REFLEX_INTEGRATION=false
```

#### 3. Import Errors in Tests

**Error**: `ModuleNotFoundError: No module named 'aiosqlite'`

**Solution**:
```bash
# Install dev dependencies
pip install -e ".[dev]"

# Or install aiosqlite directly
pip install aiosqlite
```

#### 4. SQLAlchemy Metadata Conflicts

**Error**: `AttributeError: 'Task' object has no attribute 'metadata'`

**Solution**: This was fixed in Sprint 1.2 by renaming `Task.metadata` → `Task.task_metadata`. Ensure you're using the latest models.py.

### Debugging Tips

```bash
# Enable debug logging
export ORCHESTRATOR_LOG_LEVEL=DEBUG

# Run single test with verbose output
pytest tests/test_database.py::test_create_task -v -s

# Check database migrations
alembic current
alembic history

# Inspect database schema
psql octollm -c "\d tasks"
psql octollm -c "\d task_results"
```

## Deployment

### Docker Compose (Development)

See `docker-compose.yml` in project root for full stack deployment with PostgreSQL and Reflex Layer.

### Kubernetes (Production - Future)

Sprint 1.2 focuses on core functionality. Kubernetes deployment will be added in Sprint 2.x with:
- Deployment manifests
- Service definitions
- ConfigMaps and Secrets
- HorizontalPodAutoscaler
- Ingress configuration

## Metrics and Observability

### Prometheus Metrics

The `/metrics` endpoint exposes the following metrics:

| Metric | Type | Description |
|--------|------|-------------|
| `octollm_orchestrator_tasks_total` | Counter | Total tasks by status |
| `octollm_orchestrator_reflex_calls_total` | Counter | Reflex Layer calls by result |
| `octollm_orchestrator_api_requests_total` | Counter | API requests by endpoint |
| `octollm_orchestrator_errors_total` | Counter | Errors by type |

### Structured Logging

All logs are output in JSON format for aggregation:

```json
{
  "timestamp": "2025-11-15T12:00:00Z",
  "level": "INFO",
  "message": "Task submitted successfully",
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "priority": "high"
}
```

## Security Considerations

### Sprint 1.2 Implementation

- ✅ Input validation via Pydantic schemas
- ✅ PII detection via Reflex Layer
- ✅ Injection detection via Reflex Layer
- ✅ Environment-based configuration (no secrets in code)
- ✅ SQL injection prevention (SQLAlchemy parameterized queries)

### Future Enhancements (Sprint 2+)

- ⏳ JWT authentication
- ⏳ Rate limiting (per client)
- ⏳ API key management
- ⏳ HTTPS/TLS termination
- ⏳ Audit logging

## Future Enhancements

### Sprint 1.3: Planner Arm Integration

- Task decomposition logic
- Multi-step planning
- Arm routing and delegation
- Pipeline orchestration

### Sprint 2.x: Additional Arms

- Tool Executor Arm (sandboxed execution)
- Retriever Arm (knowledge base search)
- Coder Arm (code generation)
- Judge Arm (output validation)

### Sprint 3.x: Production Features

- Distributed tracing (OpenTelemetry)
- Kubernetes deployment
- Multi-region support
- Advanced caching strategies

## References

### Documentation

- [Component Documentation](../../docs/components/orchestrator.md) - Comprehensive implementation guide
- [OpenAPI Specification](../../docs/api/openapi/orchestrator.yaml) - Full API reference
- [Sprint 1.2 Completion Report](../../docs/phases/sprint-1.2/SPRINT-1.2-COMPLETION.md) - Sprint summary

### Source Code

```
services/orchestrator/
├── app/
│   ├── main.py              # FastAPI application (486 lines)
│   ├── reflex_client.py     # Reflex Layer client (504 lines)
│   ├── database.py          # Database layer (383 lines)
│   ├── models.py            # Data models (255 lines)
│   └── config.py            # Configuration (148 lines)
├── tests/                   # Test suite (87 tests, 85%+ coverage)
├── pyproject.toml           # Dependencies and metadata
├── Dockerfile               # Container image
└── README.md                # This file
```

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/en/20/)
- [Pydantic V2 Documentation](https://docs.pydantic.dev/latest/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Sprint 1.2 Status**: ✅ Complete (2025-11-15)
**Next Sprint**: Sprint 1.3 - Planner Arm Integration
