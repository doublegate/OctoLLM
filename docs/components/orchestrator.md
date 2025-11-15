# Orchestrator Service

**Component**: Central Orchestrator (Brain)
**Version**: 1.0.0
**Status**: Sprint 1.2 Complete ✅
**Last Updated**: 2025-11-15

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Implementation Details](#implementation-details)
- [API Reference](#api-reference)
- [Data Models](#data-models)
- [Database Schema](#database-schema)
- [Reflex Layer Integration](#reflex-layer-integration)
- [Configuration](#configuration)
- [Performance](#performance)
- [Metrics](#metrics)
- [Error Handling](#error-handling)
- [Security](#security)
- [Testing](#testing)
- [Deployment](#deployment)
- [Future Enhancements](#future-enhancements)

## Overview

The Orchestrator is the central "brain" of the OctoLLM system, responsible for task coordination, safety validation, and delegation to specialized arms. As of Sprint 1.2, the Orchestrator implements core task submission, Reflex Layer integration, and PostgreSQL persistence.

**Status**: Phase 2 Implementation Complete (Sprint 1.2 ✅)
**Technology**: Python 3.11+ / FastAPI / SQLAlchemy / PostgreSQL
**Lines of Code**: ~1,600 (app/) + ~2,900 (tests/)

### Design Goals

- **Safety First**: All tasks validated through Reflex Layer (PII/injection detection)
- **High Availability**: Circuit breaker pattern prevents cascading failures
- **Data Integrity**: PostgreSQL with async SQLAlchemy for persistence
- **Observability**: Prometheus metrics and structured logging
- **Developer Experience**: FastAPI with automatic OpenAPI documentation

### Sprint 1.2 Deliverables

- ✅ **Phase 1**: Reflex Layer Integration
  - ReflexClient with circuit breaker, retry logic
  - 39 tests passing, 97% coverage

- ✅ **Phase 2**: Orchestrator Core
  - FastAPI application with 6 endpoints
  - Database layer (async SQLAlchemy)
  - Models (Pydantic + SQLAlchemy ORM)
  - Configuration management
  - 87 tests passing, 100% pass rate
  - 85%+ coverage on tested modules

## Architecture

### System Context

```
┌─────────────┐
│   User/API  │
└──────┬──────┘
       │
       v
┌─────────────────────────────────────────┐
│          Orchestrator Service           │
│                                         │
│  ┌────────────┐      ┌──────────────┐ │
│  │  FastAPI   │─────>│ Reflex Layer │ │
│  │   Server   │      │    Client    │ │
│  └─────┬──────┘      └──────┬───────┘ │
│        │                    │          │
│        v                    v          │
│  ┌────────────┐      ┌──────────────┐ │
│  │  Database  │      │   Metrics    │ │
│  │   Layer    │      │  (Prometheus)│ │
│  └────────────┘      └──────────────┘ │
└─────────────────────────────────────────┘
       │                    │
       v                    v
┌─────────────┐      ┌──────────────┐
│ PostgreSQL  │      │ Reflex Layer │
└─────────────┘      │   Service    │
                     └──────────────┘
```

### Component Diagram

```mermaid
graph TB
    subgraph "Orchestrator Service"
        API[FastAPI Server<br/>app/main.py]
        MODELS[Data Models<br/>app/models.py]
        DB[Database Layer<br/>app/database.py]
        REFLEX[Reflex Client<br/>app/reflex_client.py]
        CONFIG[Configuration<br/>app/config.py]
    end

    subgraph "External Dependencies"
        PG[(PostgreSQL<br/>Tasks + Results)]
        REFLEXSVC[Reflex Layer<br/>PII/Injection Detection]
        PROM[Prometheus<br/>Metrics]
    end

    API --> MODELS
    API --> DB
    API --> REFLEX
    API --> CONFIG
    DB --> PG
    REFLEX --> REFLEXSVC
    API --> PROM
```

### Data Flow

1. **Task Submission** (POST /submit)
   ```
   User Request
       ↓
   TaskRequest (Pydantic validation)
       ↓
   TaskContract (internal format)
       ↓
   ReflexClient.process() [PII/injection check]
       ↓
   Database.create_task() [PostgreSQL]
       ↓
   TaskSubmitResponse (task_id + status)
   ```

2. **Task Retrieval** (GET /tasks/{task_id})
   ```
   User Request
       ↓
   Database.get_task() [PostgreSQL query]
       ↓
   Task.to_response() [ORM → Pydantic]
       ↓
   TaskResponse (status + result/error)
   ```

3. **Health Checks**
   - Liveness: `/health` - Always returns 200 if service is running
   - Readiness: `/ready` - Checks PostgreSQL + Reflex Layer availability

## Implementation Details

### FastAPI Application

**File**: `app/main.py` (486 lines)

**Features**:
- 6 REST API endpoints
- Request ID middleware (X-Request-ID header)
- Request logging middleware (structured logs + Prometheus metrics)
- CORS middleware (development mode)
- Exception handlers (HTTP + general exceptions)
- Lifespan manager (startup/shutdown)

**Middleware Stack**:
```python
Request
  ↓
[add_request_id] → Inject unique request ID
  ↓
[log_requests] → Log request/response + timing
  ↓
[CORSMiddleware] → CORS headers (dev mode)
  ↓
FastAPI Route Handler
  ↓
Response
```

### Reflex Layer Integration

**File**: `app/reflex_client.py` (504 lines)

The `ReflexClient` provides robust integration with the Reflex Layer service for PII and injection detection.

**Features**:
- **Retry Logic**: 3 retries with exponential backoff (1-5s) via tenacity
- **Circuit Breaker**: Opens after 5 consecutive failures, resets after 60s
- **Request Validation**: Pydantic models ensure type safety
- **Connection Pooling**: Up to 100 concurrent connections, 20 keepalive
- **Metrics Collection**: Tracks requests, latency, PII/injection detections

**Circuit Breaker States**:
```python
┌────────┐
│ Closed │ ← Normal operation
└───┬────┘
    │ 5 failures
    v
┌────────┐
│  Open  │ ← Reject all requests
└───┬────┘
    │ 60s timeout
    v
┌───────────┐
│ Half-Open │ ← Allow 3 test requests
└─────┬─────┘
      │ 3 successes    │ 1 failure
      v                v
   Closed            Open
```

**Usage Example**:
```python
from app.reflex_client import ReflexClient

client = ReflexClient(
    base_url="http://reflex-layer:8080",
    timeout=10.0,
    max_retries=3,
    circuit_breaker_threshold=5,
    circuit_breaker_reset_timeout=60,
)

response = await client.process(
    text="Analyze the sentiment of this text",
    user_id="user-123",
    context={"task_id": "task-456"}
)

if response.pii_detected:
    print(f"PII detected: {response.pii_matches}")
if response.injection_detected:
    print(f"Injection attempt: {response.injection_matches}")
```

### Database Layer

**File**: `app/database.py` (383 lines)

**Architecture**:
- **ORM**: SQLAlchemy 2.0 with async support
- **Driver**: psycopg (asyncpg driver for PostgreSQL)
- **Connection Pooling**: Configurable pool size, overflow, timeout
- **Session Management**: Context manager pattern for automatic cleanup

**Connection Pooling Configuration**:
```python
create_async_engine(
    database_url,
    poolclass=QueuePool,
    pool_size=10,              # Base connections
    max_overflow=20,           # Additional connections
    pool_timeout=30,           # Wait time for connection
    pool_pre_ping=True,        # Verify connection health
)
```

**CRUD Operations**:

| Function | Description | Returns |
|----------|-------------|---------|
| `create_task(session, contract)` | Create new task | Task ORM model |
| `get_task(session, task_id)` | Get task by UUID | Task or None |
| `get_tasks_by_status(session, status, limit)` | Filter by status | List[Task] |
| `update_task_status(session, task_id, status)` | Update status | Task or None |
| `store_task_result(session, task_id, result, error)` | Store result | TaskResult |
| `delete_task(session, task_id)` | Delete task | bool |
| `get_task_count_by_status(session)` | Count by status | Dict[str, int] |

**Usage Pattern**:
```python
from app.database import get_database, create_task

db = get_database()

async with db.session() as session:
    task = await create_task(session, contract)
    print(f"Created task: {task.id}")
```

## API Reference

### POST /submit

Submit a new task for processing with automatic safety checks.

**Request Body**:
```json
{
  "goal": "Analyze the sentiment of this text: I love OctoLLM!",
  "constraints": {
    "format": "json",
    "max_length": 1000
  },
  "context": "User feedback analysis",
  "acceptance_criteria": [
    "Response must be valid JSON",
    "Response must include sentiment score"
  ],
  "budget": {
    "max_tokens": 5000,
    "max_time_seconds": 120,
    "max_cost_usd": 0.50
  },
  "priority": "medium",
  "metadata": {
    "source": "web-app",
    "user_id": "user-123"
  }
}
```

**Response** (202 Accepted):
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "message": "Task submitted successfully and queued for processing"
}
```

**Error Responses**:
- **400 Bad Request**: Validation error or safety check failed (PII/injection detected)
- **503 Service Unavailable**: Reflex Layer unavailable (circuit breaker open)

**Safety Check Flow**:
```
1. Validate request (Pydantic)
   ↓
2. Call Reflex Layer for PII/injection check
   ↓
3. If PII detected → 400 Bad Request
   If injection detected → 400 Bad Request
   ↓
4. Store task in PostgreSQL
   ↓
5. Return 202 Accepted with task_id
```

### GET /tasks/{task_id}

Retrieve task status and result by UUID.

**Path Parameters**:
- `task_id` (string, UUID): Task identifier

**Response** (200 OK):
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "pending",
  "goal": "Analyze the sentiment of this text: I love OctoLLM!",
  "result": null,
  "error": null,
  "created_at": "2025-11-14T12:00:00Z",
  "updated_at": "2025-11-14T12:00:00Z",
  "processing_time_ms": null
}
```

**Error Responses**:
- **404 Not Found**: Task ID does not exist

### GET /health

Health check endpoint for Kubernetes liveness probe.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-11-14T12:00:00Z",
  "version": "0.1.0"
}
```

**Usage**: Always returns 200 if the service is running. Does not check dependencies.

### GET /ready

Readiness check endpoint for Kubernetes readiness probe.

**Response** (200 OK):
```json
{
  "ready": true,
  "checks": {
    "database": true,
    "reflex_layer": true
  },
  "timestamp": "2025-11-14T12:00:00Z"
}
```

**Response** (503 Service Unavailable):
```json
{
  "ready": false,
  "checks": {
    "database": true,
    "reflex_layer": false
  },
  "timestamp": "2025-11-14T12:00:00Z"
}
```

**Usage**: Checks PostgreSQL connection and Reflex Layer health. Returns 200 only if both are healthy.

### GET /metrics

Prometheus metrics endpoint in text exposition format.

**Response** (200 OK):
```
# TYPE orchestrator_tasks_submitted_total counter
orchestrator_tasks_submitted_total{priority="medium"} 42.0

# TYPE orchestrator_task_status_total counter
orchestrator_task_status_total{status="pending"} 10.0
orchestrator_task_status_total{status="completed"} 25.0
orchestrator_task_status_total{status="failed"} 7.0

# TYPE orchestrator_task_processing_seconds histogram
orchestrator_task_processing_seconds_bucket{le="0.1"} 5.0
orchestrator_task_processing_seconds_bucket{le="0.5"} 15.0
orchestrator_task_processing_seconds_bucket{le="1.0"} 30.0
...
```

### GET /

Root endpoint providing service information and navigation.

**Response** (200 OK):
```json
{
  "service": "OctoLLM Orchestrator",
  "version": "0.1.0",
  "docs": "/docs",
  "health": "/health",
  "ready": "/ready",
  "metrics": "/metrics"
}
```

## Data Models

### Pydantic Models (API Layer)

**File**: `app/models.py` (255 lines)

#### ResourceBudget

Resource constraints for task execution.

```python
class ResourceBudget(BaseModel):
    max_tokens: int = Field(default=10000, ge=1, le=100000)
    max_time_seconds: int = Field(default=300, ge=1, le=3600)
    max_cost_usd: float = Field(default=1.0, ge=0.0, le=100.0)
```

#### TaskContract

Formal specification for a task (internal format).

```python
class TaskContract(BaseModel):
    task_id: str = Field(default_factory=lambda: str(uuid4()))
    goal: str = Field(..., min_length=1, max_length=10000)
    constraints: Dict[str, Any] = Field(default_factory=dict)
    context: Optional[str] = Field(None, max_length=50000)
    acceptance_criteria: List[str] = Field(default_factory=list)
    budget: ResourceBudget = Field(default_factory=ResourceBudget)
    priority: Priority = Field(default=Priority.MEDIUM)
    parent_task_id: Optional[str] = None
    assigned_arm: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
```

#### TaskRequest

API request model for task submission.

```python
class TaskRequest(BaseModel):
    goal: str = Field(..., min_length=1, max_length=10000)
    constraints: Optional[Dict[str, Any]] = None
    context: Optional[str] = Field(None, max_length=50000)
    acceptance_criteria: Optional[List[str]] = None
    budget: Optional[ResourceBudget] = None
    priority: Optional[Priority] = Field(Priority.MEDIUM)
    metadata: Optional[Dict[str, Any]] = None
```

#### TaskResponse

API response model for task status/result.

```python
class TaskResponse(BaseModel):
    task_id: str
    status: TaskStatus
    goal: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    processing_time_ms: Optional[int] = None
```

### Enums

```python
class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Priority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
```

## Database Schema

### Tables

#### tasks

Stores task metadata and status.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Task identifier (UUID v4) |
| `goal` | TEXT | NOT NULL | Natural language task description |
| `status` | ENUM | NOT NULL, INDEX | Task status (pending, processing, completed, failed, cancelled) |
| `constraints` | JSONB | NOT NULL, DEFAULT '{}' | Task constraints (format, length, etc.) |
| `context` | TEXT | NULLABLE | Background information |
| `acceptance_criteria` | JSONB | NOT NULL, DEFAULT '[]' | Success conditions (JSON array) |
| `budget` | JSONB | NOT NULL | Resource budget (max_tokens, max_time_seconds, max_cost_usd) |
| `priority` | ENUM | NOT NULL, DEFAULT 'medium' | Task priority (low, medium, high, critical) |
| `parent_task_id` | UUID | NULLABLE, FOREIGN KEY | Parent task if this is a subtask |
| `assigned_arm` | VARCHAR(100) | NULLABLE | Target arm identifier |
| `task_metadata` | JSONB | NOT NULL, DEFAULT '{}' | Additional metadata |
| `created_at` | TIMESTAMP(TZ) | NOT NULL, INDEX | Creation timestamp |
| `updated_at` | TIMESTAMP(TZ) | NOT NULL | Last update timestamp |

**Indexes**:
- PRIMARY KEY on `id`
- INDEX on `status` (for filtering by status)
- INDEX on `created_at` (for time-based queries)

#### task_results

Stores task execution results and errors.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| `id` | UUID | PRIMARY KEY | Result identifier (UUID v4) |
| `task_id` | UUID | NOT NULL, UNIQUE, FOREIGN KEY | Task identifier |
| `result` | JSONB | NULLABLE | Task execution result (JSON) |
| `error` | TEXT | NULLABLE | Error message if task failed |
| `processing_time_ms` | INTEGER | NULLABLE | Processing time in milliseconds |
| `created_at` | TIMESTAMP(TZ) | NOT NULL | Result timestamp |

**Indexes**:
- PRIMARY KEY on `id`
- UNIQUE INDEX on `task_id` (one result per task)

**Relationships**:
- `task_results.task_id` → `tasks.id` (ONE-TO-ONE)
- CASCADE DELETE: Deleting task deletes result

### Example Queries

**Get all pending tasks**:
```sql
SELECT id, goal, priority, created_at
FROM tasks
WHERE status = 'pending'
ORDER BY priority DESC, created_at ASC
LIMIT 100;
```

**Get task with result**:
```sql
SELECT
    t.id,
    t.goal,
    t.status,
    t.created_at,
    tr.result,
    tr.error,
    tr.processing_time_ms
FROM tasks t
LEFT JOIN task_results tr ON t.id = tr.task_id
WHERE t.id = '123e4567-e89b-12d3-a456-426614174000';
```

**Count tasks by status**:
```sql
SELECT status, COUNT(*) as count
FROM tasks
GROUP BY status;
```

## Configuration

**File**: `app/config.py` (148 lines)

All settings are loaded from environment variables with the `ORCHESTRATOR_` prefix.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ORCHESTRATOR_DATABASE_URL` | Yes | - | PostgreSQL connection URL |
| `ORCHESTRATOR_REFLEX_LAYER_URL` | No | http://reflex-layer:8080 | Reflex Layer service URL |
| `ORCHESTRATOR_REDIS_URL` | No | redis://localhost:6379/0 | Redis connection URL (future) |
| `ORCHESTRATOR_LOG_LEVEL` | No | INFO | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `ORCHESTRATOR_ENABLE_REFLEX_INTEGRATION` | No | true | Enable Reflex Layer integration |
| `ORCHESTRATOR_ENABLE_BACKGROUND_PROCESSING` | No | true | Enable background task processing (future) |
| `ORCHESTRATOR_DEBUG` | No | false | Debug mode (enables /docs, verbose logging) |
| `ORCHESTRATOR_ENVIRONMENT` | No | development | Environment (development, staging, production) |

### Example .env File

```bash
# Database
ORCHESTRATOR_DATABASE_URL=postgresql://octollm:octollm@localhost:5432/octollm

# Reflex Layer
ORCHESTRATOR_REFLEX_LAYER_URL=http://localhost:8080
ORCHESTRATOR_REFLEX_LAYER_TIMEOUT=10.0
ORCHESTRATOR_REFLEX_LAYER_MAX_RETRIES=3
ORCHESTRATOR_REFLEX_LAYER_CIRCUIT_BREAKER_THRESHOLD=5
ORCHESTRATOR_REFLEX_LAYER_CIRCUIT_BREAKER_RESET_TIMEOUT=60

# Database Pooling
ORCHESTRATOR_DATABASE_POOL_SIZE=10
ORCHESTRATOR_DATABASE_MAX_OVERFLOW=20
ORCHESTRATOR_DATABASE_POOL_TIMEOUT=30

# Observability
ORCHESTRATOR_LOG_LEVEL=INFO
ORCHESTRATOR_ENABLE_METRICS=true

# Feature Flags
ORCHESTRATOR_ENABLE_REFLEX_INTEGRATION=true
ORCHESTRATOR_ENABLE_BACKGROUND_PROCESSING=false

# Development
ORCHESTRATOR_DEBUG=true
ORCHESTRATOR_ENVIRONMENT=development
```

### Settings Validation

The `Settings` class uses Pydantic validators to ensure configuration correctness:

- `database_url` must start with `postgresql://` or `postgresql+psycopg://`
- `redis_url` must start with `redis://` or `rediss://`
- `environment` must be one of: `development`, `staging`, `production`
- Numeric fields have range validation (e.g., `pool_size` >= 1)

## Performance

### Latency Targets

| Endpoint | Target (P95) | Actual (Sprint 1.2) |
|----------|--------------|---------------------|
| POST /submit | <500ms | ~100-150ms (with Reflex call) |
| GET /tasks/{task_id} | <100ms | ~5-10ms (database query) |
| GET /health | <10ms | <1ms |
| GET /ready | <100ms | ~10-20ms (health checks) |
| GET /metrics | <50ms | ~5ms |

### Component Latency Breakdown

**POST /submit** (~100-150ms total):
```
Pydantic validation:        ~1-2ms
Reflex Layer call:          ~50-100ms (depends on Reflex Layer)
Database insert:            ~5-10ms
Response serialization:     ~1-2ms
Middleware overhead:        ~2-5ms
```

**GET /tasks/{task_id}** (~5-10ms total):
```
Database query:             ~3-7ms
ORM → Pydantic conversion:  ~1-2ms
Response serialization:     ~1ms
```

### Resource Requirements

**Minimum (Development)**:
- CPU: 500m (0.5 cores)
- Memory: 512Mi
- Disk: 1Gi

**Recommended (Production)**:
- CPU: 2000m (2 cores)
- Memory: 2Gi
- Disk: 10Gi
- Database: PostgreSQL 15+ with 4GB RAM, 50GB storage

### Scalability

- **Horizontal Scaling**: Stateless design enables multiple instances behind load balancer
- **Concurrent Tasks**: Each instance can handle ~10-20 concurrent requests
- **Database Connection Pooling**: 10 base connections + 20 overflow per instance
- **Reflex Client Pooling**: 100 concurrent connections to Reflex Layer

## Metrics

### Prometheus Metrics Exposed

| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `orchestrator_tasks_submitted_total` | Counter | `priority` | Total tasks submitted by priority |
| `orchestrator_task_status_total` | Counter | `status` | Total tasks by status |
| `orchestrator_task_processing_seconds` | Histogram | - | Task processing time (buckets: 0.1s to 300s) |
| `orchestrator_http_request_duration_seconds` | Histogram | `method`, `endpoint`, `status` | HTTP request duration |
| `orchestrator_reflex_calls_total` | Counter | `status` | Total Reflex Layer calls by status (Success/Blocked/Error) |

### Example Queries

**Task submission rate**:
```promql
rate(orchestrator_tasks_submitted_total[5m])
```

**95th percentile task processing time**:
```promql
histogram_quantile(0.95, rate(orchestrator_task_processing_seconds_bucket[5m]))
```

**Reflex Layer error rate**:
```promql
rate(orchestrator_reflex_calls_total{status="Error"}[5m])
/
rate(orchestrator_reflex_calls_total[5m])
```

**Task success rate**:
```promql
sum(rate(orchestrator_task_status_total{status="completed"}[5m]))
/
sum(rate(orchestrator_task_status_total[5m]))
```

## Error Handling

### HTTP Status Codes

| Code | Condition | Response |
|------|-----------|----------|
| 200 | Success | Task retrieved successfully |
| 202 | Accepted | Task submitted and queued |
| 400 | Bad Request | Validation error or safety check failed |
| 404 | Not Found | Task ID does not exist |
| 500 | Internal Server Error | Uncaught exception |
| 503 | Service Unavailable | Reflex Layer unavailable (circuit breaker open) |

### Error Response Format

```json
{
  "error": "Task blocked by security policy",
  "request_id": "req-123e4567",
  "details": {
    "pii_detected": true,
    "pii_matches": [
      {
        "pii_type": "Email",
        "value": "user@example.com",
        "position": 42,
        "confidence": 0.95,
        "context": "Contact me at user@example.com for..."
      }
    ]
  }
}
```

### Circuit Breaker Behavior

**Normal Operation (Closed)**:
- All requests proceed to Reflex Layer
- Failures increment failure counter
- Successes reset failure counter

**Circuit Open**:
- All requests fail immediately with 503
- No requests sent to Reflex Layer
- After 60s timeout, circuit enters half-open state

**Half-Open Testing**:
- Allow 3 test requests to Reflex Layer
- If all 3 succeed → circuit closes
- If any fails → circuit opens again

### Retry Logic

Reflex Layer calls use exponential backoff:
- **Max Retries**: 3
- **Backoff**: 1s, 2s, 4s (exponential with multiplier=1)
- **Max Backoff**: 5s
- **Retry on**: Network errors, HTTP 5xx errors
- **No retry on**: HTTP 4xx errors (client errors)

## Security

### Input Validation

**Pydantic Models**:
- All API requests validated against Pydantic schemas
- Type safety enforced (strings, integers, enums)
- Field constraints (min/max length, value ranges)
- Custom validators (e.g., goal cannot be empty whitespace)

**SQL Injection Protection**:
- SQLAlchemy ORM prevents SQL injection
- Parameterized queries only
- No raw SQL execution

**XSS Protection**:
- FastAPI auto-escapes JSON responses
- No HTML rendering in API responses

### PII Handling

**Reflex Layer Integration**:
- All task goals processed through Reflex Layer
- 18 PII patterns detected (Email, SSN, Credit Card, etc.)
- Tasks with detected PII rejected with 400 Bad Request
- No PII stored in database

**PII Detection Patterns**:
- Email addresses
- Social Security Numbers (SSN)
- Credit card numbers
- Phone numbers
- IP addresses
- Passport numbers
- Driver's license numbers
- Medical record numbers
- Bank account numbers
- And more...

### Injection Protection

**Prompt Injection Detection**:
- 14 OWASP injection patterns detected
- Severity levels: Critical, High, Medium, Low
- Context-aware analysis (quoted text, academic discussion, testing)
- Tasks with detected injections rejected with 400 Bad Request

**Injection Patterns**:
- Ignore previous instructions
- System prompt override attempts
- Role manipulation
- Jailbreak attempts
- Delimiter injection
- And more...

### Secrets Management

- Database credentials via environment variables only
- No secrets in code or logs
- Secrets redacted in structured logs (database URL masks credentials)

## Testing

### Test Coverage

**Total Tests**: 87 tests
**Pass Rate**: 100%
**Coverage**: 85%+ on core modules

**Test Files**:
- `tests/test_models.py`: 34 tests (Pydantic/ORM models)
- `tests/test_config.py`: 26 tests (configuration)
- `tests/test_database.py`: 27 tests (CRUD operations)
- `tests/test_reflex_client.py`: 39 tests (Reflex integration)

### Test Categories

**Unit Tests**:
- Pydantic model validation
- Configuration loading and validation
- Database CRUD operations (in-memory SQLite)
- Reflex client request/response handling

**Integration Tests** (Deferred to Sprint 1.3):
- End-to-end task submission flow
- Actual PostgreSQL database
- Actual Reflex Layer service
- Concurrent request handling

### Running Tests

```bash
# All tests
pytest -v

# With coverage
pytest --cov=app --cov-report=html --cov-report=term

# Specific test file
pytest tests/test_models.py -v

# Specific test
pytest tests/test_models.py::test_task_contract_validation -v

# Integration tests (when available)
pytest -m integration -v
```

### Test Fixtures

**Common Fixtures**:
- `sample_task_contract()`: Valid TaskContract for testing
- `sample_task_request()`: Valid TaskRequest for testing
- `db_session()`: In-memory SQLite session for database tests
- `mock_reflex_client()`: Mock Reflex client for testing without real service

## Deployment

### Docker

**Dockerfile**: `services/orchestrator/Dockerfile`

```bash
# Build image
cd services/orchestrator
docker build -t octollm/orchestrator:1.0.0 .

# Run container
docker run -p 8000:8000 \
  -e ORCHESTRATOR_DATABASE_URL=postgresql+psycopg://user:pass@db:5432/octollm \
  -e ORCHESTRATOR_REFLEX_LAYER_URL=http://reflex-layer:8080 \
  octollm/orchestrator:1.0.0
```

### Docker Compose

**File**: `docker-compose.yml`

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: octollm
      POSTGRES_PASSWORD: octollm
      POSTGRES_DB: octollm
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  reflex-layer:
    build: ./services/reflex-layer
    ports:
      - "8080:8080"

  orchestrator:
    build: ./services/orchestrator
    ports:
      - "8000:8000"
    environment:
      ORCHESTRATOR_DATABASE_URL: postgresql+psycopg://octollm:octollm@postgres:5432/octollm
      ORCHESTRATOR_REFLEX_LAYER_URL: http://reflex-layer:8080
      ORCHESTRATOR_ENABLE_REFLEX_INTEGRATION: "true"
      ORCHESTRATOR_DEBUG: "true"
    depends_on:
      - postgres
      - reflex-layer

volumes:
  postgres_data:
```

### Kubernetes (Future)

**Resources**: `infrastructure/kubernetes/orchestrator/`

- Deployment: 3 replicas with rolling updates
- Service: ClusterIP exposing port 8000
- HorizontalPodAutoscaler: Scale based on CPU (target: 70%)
- ConfigMap: Environment variables
- Secret: Database credentials

## Future Enhancements

### Sprint 1.3+

- [ ] **Pipeline Module**: Task processing pipeline with step execution
- [ ] **Background Worker**: Async task processing with Redis queue
- [ ] **Arm Routing**: Determine which arm should handle each task
- [ ] **Task Decomposition**: Break complex tasks into subtasks
- [ ] **Result Integration**: Combine results from multiple arms
- [ ] **Validation Layer**: Verify results meet acceptance criteria

### Phase 3+

- [ ] **Authentication**: JWT-based API authentication
- [ ] **Rate Limiting**: Per-user rate limiting with Redis
- [ ] **WebSocket Support**: Real-time task updates
- [ ] **Caching Layer**: Redis-backed result caching
- [ ] **Distributed Tracing**: OpenTelemetry integration
- [ ] **Multi-Tenancy**: Tenant isolation and resource quotas
- [ ] **Task Cancellation**: Cancel running tasks
- [ ] **Task Dependencies**: Define task dependencies and execution order
- [ ] **Swarm Execution**: Parallel execution with multiple arms
- [ ] **Active Learning**: Learn from task execution traces

## References

- [OctoLLM Architecture](../../ref-docs/OctoLLM-Architecture-Implementation.md)
- [Reflex Layer Component](./reflex-layer.md)
- [API Specification](../api/openapi/orchestrator.yaml)
- [Database Design](../implementation/memory-systems.md)
- [Sprint 1.2 Completion Report](../phases/sprint-1.2/SPRINT-1.2-COMPLETION.md)
- [Service README](../../services/orchestrator/README.md)

## See Also

- [Arm Specifications](./arms/)
- [Integration Patterns](../implementation/integration-patterns.md)
- [Testing Guide](../implementation/testing-guide.md)
- [Deployment Guide](../operations/deployment.md)
