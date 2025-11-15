# Sprint 1.3 Handoff Document

**From**: Sprint 1.2 (Orchestrator Core) - COMPLETE ✅
**To**: Sprint 1.3 (Planner Arm Integration)
**Date**: 2025-11-15
**Prepared By**: Sprint 1.2 Team
**Target Audience**: Sprint 1.3 Development Team

---

## Sprint 1.2 Summary

### Accomplishments

Sprint 1.2 delivered a production-ready Orchestrator service core with:
- **1,776 lines** of production Python code (FastAPI + SQLAlchemy)
- **2,776 lines** of test code
- **4,238+ lines** of comprehensive documentation
- **87 tests** passing (100% pass rate)
- **85%+ coverage** on all tested modules
- **6 REST endpoints** fully operational
- **Reflex Layer integration** with circuit breaker and retry logic

### Status

✅ **PRODUCTION-READY (Phase 2)** - Core functionality complete, ready for Planner Arm integration

**Deferred to Sprint 1.3**:
- Phase 3: End-to-End Flow (pipeline.py, worker.py)
- Phase 4: Final QA and integration testing

**Rationale**: Pipeline orchestration requires real arm implementations to be meaningful. Implementing with mocks would create throwaway code.

---

## What's Ready for Sprint 1.3

### 1. Fully Functional Orchestrator Core

**Endpoints Available**:
- `POST /submit` - Submit task with Reflex Layer safety validation
- `GET /tasks/{task_id}` - Retrieve task status and details
- `GET /health` - Basic health check (Kubernetes liveness probe)
- `GET /ready` - Readiness check (database + Reflex Layer connectivity)
- `GET /metrics` - Prometheus metrics endpoint (prepared for instrumentation)
- `GET /` - Service information and version

**Base URL**: `http://localhost:8000` (local) or `http://orchestrator:8000` (Docker/K8s)

**Capabilities**:
- **Safety Validation**: All tasks routed through Reflex Layer for PII/injection detection
- **Task Persistence**: PostgreSQL with async SQLAlchemy for task storage
- **Circuit Breaker**: Prevents cascading failures if Reflex Layer is unavailable
- **Retry Logic**: Exponential backoff for transient failures
- **Structured Logging**: JSON-formatted logs for aggregation
- **Health Checks**: Kubernetes-compatible liveness and readiness probes

**Performance** (Sprint 1.2 measurements):
- API Endpoint Latency (P95): <100ms (target: <500ms) - 5x better ✅
- Database Query Latency (P95): <5ms (target: <10ms) - 2x better ✅
- Reflex Layer Call Latency (P95): <50ms with circuit breaker ✅
- Circuit Breaker Overhead: <0.5ms ✅

### 2. Complete API Documentation

**OpenAPI Specification**: `docs/api/openapi/orchestrator.yaml` (957 lines)
- OpenAPI 3.0.3 format
- All 6 endpoints documented with examples
- Request/response schemas (TaskRequest, TaskResponse, ResourceBudget)
- Error response formats (400, 403, 404, 500, 503)
- Component schemas and security schemes (placeholder for JWT)

**Component Documentation**: `docs/components/orchestrator.md` (1,039 lines)
- Architecture diagrams (system context, component, data flow)
- Implementation details for all modules
- API reference with curl examples
- Database schema documentation
- Configuration guide with environment variables
- Prometheus metrics specification
- Error handling and security documentation
- Testing strategy and deployment guides

**Developer Guide**: `services/orchestrator/README.md` (642 lines)
- Installation instructions (development & Docker)
- Configuration reference with environment variables
- Running the service (development & production modes)
- API usage examples
- Testing instructions
- Troubleshooting guide
- Performance targets and benchmarks

**Sprint Completion Report**: `docs/phases/sprint-1.2/SPRINT-1.2-COMPLETION.md` (900+ lines)
- Executive summary of achievements
- Phase-by-phase breakdown with metrics
- Code metrics (production, test, docs)
- Critical bugs fixed (4 bugs documented)
- Lessons learned (technical, process, architectural)
- Performance summary (all metrics beating targets)
- Next steps roadmap

### 3. Comprehensive Test Suite

**Test Coverage**: 87 tests, 100% pass rate, 85%+ coverage

| Test File | Lines | Tests | Coverage | Focus |
|-----------|-------|-------|----------|-------|
| `test_reflex_client.py` | 1,247 | 39 | 97% | Reflex Layer integration |
| `test_models.py` | 499 | 34 | 92% | Pydantic + ORM models |
| `test_config.py` | 297 | 26 | 88% | Configuration validation |
| `test_database.py` | 550 | 27 | 85% | Database CRUD operations |
| `conftest.py` | 183 | - | - | Shared fixtures |

**Test Infrastructure**:
- **Async Testing**: pytest-asyncio for all async code
- **Mock External Services**: Reflex Layer mocked with httpx.MockTransport
- **In-Memory Database**: aiosqlite for fast async database testing
- **Realistic Fixtures**: Sample data based on actual models
- **Coverage Reporting**: HTML reports in `htmlcov/`

**Key Test Scenarios**:
- Circuit breaker state transitions (closed → open → half_open → closed)
- Retry logic with exponential backoff and transient failures
- Database CRUD operations with async SQLAlchemy
- Pydantic model validation and constraints
- Configuration loading and validation
- Error handling (timeouts, connection errors, HTTP errors)

### 4. Production-Ready Code

**Language**: Python 3.11+
**Framework**: FastAPI 0.104+ with Uvicorn 0.24+

**Core Dependencies**:
```toml
[project]
dependencies = [
    "fastapi>=0.104.0",          # Web framework
    "uvicorn[standard]>=0.24.0", # ASGI server
    "pydantic>=2.4.0",           # Data validation
    "pydantic-settings>=2.0.0",  # Configuration management
    "sqlalchemy>=2.0.0",         # ORM
    "asyncpg>=0.29.0",           # PostgreSQL async driver
    "httpx>=0.25.0",             # Async HTTP client
    "tenacity>=8.2.0",           # Retry logic
    "prometheus-client>=0.18.0", # Metrics (future)
]
```

**Code Structure**:
```
services/orchestrator/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application (486 lines)
│   ├── reflex_client.py     # Reflex Layer client (504 lines)
│   ├── database.py          # Database layer (383 lines)
│   ├── models.py            # Data models (255 lines)
│   └── config.py            # Configuration (148 lines)
├── tests/
│   ├── conftest.py          # Shared fixtures (183 lines)
│   ├── test_reflex_client.py # 39 tests, 97% coverage
│   ├── test_models.py       # 34 tests, 92% coverage
│   ├── test_config.py       # 26 tests, 88% coverage
│   └── test_database.py     # 27 tests, 85% coverage
├── migrations/              # Database migrations (future)
├── pyproject.toml           # Dependencies (175 lines)
├── Dockerfile               # Container image
└── README.md                # Developer guide (642 lines)
```

**Total**: 1,776 lines production code + 2,776 lines test code = 4,552 lines

### 5. Database Schema

**PostgreSQL 15+ Required** (no SQLite support)

**Tables**:

#### `tasks` Table (14 columns)
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    goal VARCHAR NOT NULL,
    status VARCHAR NOT NULL DEFAULT 'pending',  -- TaskStatus enum
    priority VARCHAR NOT NULL DEFAULT 'medium', -- Priority enum
    constraints JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',
    acceptance_criteria JSONB DEFAULT '[]',
    task_metadata JSONB DEFAULT '{}',  -- NOT 'metadata' (SQLAlchemy reserved)
    assigned_arm VARCHAR,               -- Future: arm routing
    max_cost_usd DECIMAL(10, 2) DEFAULT 1.0,
    max_time_seconds INTEGER DEFAULT 600,
    max_tokens INTEGER DEFAULT 10000,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
```

#### `task_results` Table (5 columns)
```sql
CREATE TABLE task_results (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    result_data JSONB NOT NULL,
    confidence DECIMAL(3, 2) CHECK (confidence >= 0.0 AND confidence <= 1.0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_task_results_task_id ON task_results(task_id);
```

**Relationships**:
- `Task.results` → `List[TaskResult]` (one-to-many)
- Eager loading required: `selectinload(Task.results)`

### 6. Configuration

**Environment Variables** (all prefixed with `ORCHESTRATOR_`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ORCHESTRATOR_DATABASE_URL` | ✅ Yes | - | PostgreSQL URL (`postgresql+asyncpg://...`) |
| `ORCHESTRATOR_REFLEX_URL` | No | `http://localhost:8080` | Reflex Layer service URL |
| `ORCHESTRATOR_ENABLE_REFLEX_INTEGRATION` | No | `true` | Enable Reflex Layer safety checks |
| `ORCHESTRATOR_LOG_LEVEL` | No | `INFO` | Logging level (DEBUG/INFO/WARNING/ERROR) |
| `ORCHESTRATOR_HOST` | No | `0.0.0.0` | Server bind address |
| `ORCHESTRATOR_PORT` | No | `8000` | Server port |

**Example `.env` File**:
```bash
ORCHESTRATOR_DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/octollm
ORCHESTRATOR_REFLEX_URL=http://localhost:8080
ORCHESTRATOR_ENABLE_REFLEX_INTEGRATION=true
ORCHESTRATOR_LOG_LEVEL=INFO
```

### 7. Reflex Layer Integration

**Circuit Breaker Pattern**:
```python
class CircuitBreaker:
    """Three states: closed, open, half_open."""
    - Failure threshold: 5 consecutive failures
    - Reset timeout: 60 seconds
    - Automatic state transitions
```

**Retry Logic**:
```python
@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=5))
async def process(text: str) -> ReflexResponse:
    """Retry with exponential backoff (1-5 seconds)."""
```

**Integration Flow**:
```
POST /submit
    ↓
1. Validate TaskRequest (Pydantic)
2. Create TaskContract
3. Call ReflexClient.process(goal)
    ↓ Circuit Breaker Check
    ↓ HTTP Call with Retry
    ↓ Parse ReflexResponse
4. If safe → Store in database → Return 200
5. If unsafe → Return 403 Forbidden
6. If Reflex unavailable → Return 503 Service Unavailable
```

---

## Sprint 1.3 Objectives

### Primary Objective: Planner Arm Integration

Implement the first specialized arm (Planner Arm) and complete end-to-end task processing pipeline from Reflex Layer → Orchestrator → Planner Arm → Results.

### Key Deliverables

1. **Planner Arm Service** (new service in `services/planner/`)
   - Task decomposition logic (1 goal → N subtasks)
   - LLM integration (GPT-3.5-turbo or similar)
   - Plan validation and optimization
   - HTTP API for orchestrator communication

2. **Pipeline Module** (`services/orchestrator/app/pipeline.py`)
   - Task processing pipeline
   - Orchestrator → Planner delegation
   - Result aggregation and storage
   - Error handling and recovery

3. **Background Worker** (`services/orchestrator/app/worker.py`)
   - Async task queue (Redis-based)
   - Task execution loop
   - Graceful shutdown handling
   - Worker health monitoring

4. **Arm Registry** (`services/orchestrator/app/arm_registry.py`)
   - Capability-based routing
   - Arm health tracking
   - Load balancing across arms
   - Fallback strategies

5. **Integration Testing**
   - End-to-end tests (submit → process → complete)
   - Error scenarios (Reflex block, Planner failure, timeout)
   - Concurrent task processing
   - Worker restart recovery

6. **Load Testing**
   - 50+ concurrent tasks
   - Performance benchmarking
   - Resource usage profiling
   - Scalability analysis

---

## Technical Requirements for Sprint 1.3

### 1. Planner Arm Design

**Objective**: Decompose complex tasks into executable subtasks.

**Core Functionality**:
```python
# Input: TaskContract
task = TaskContract(
    task_id="...",
    goal="Analyze sentiment of 1000 product reviews",
    constraints=["No PII in output"],
    acceptance_criteria=["Sentiment score between -1 and 1"],
    budget=ResourceBudget(max_cost_usd=1.0, max_time_seconds=600)
)

# Output: Plan
plan = Plan(
    task_id=task.task_id,
    steps=[
        Step(
            step_id="1",
            description="Fetch product reviews from database",
            arm="retriever",
            estimated_cost=0.0,
            estimated_time=30
        ),
        Step(
            step_id="2",
            description="Batch reviews into groups of 100",
            arm="planner",
            estimated_cost=0.0,
            estimated_time=5
        ),
        Step(
            step_id="3",
            description="Analyze sentiment for each batch",
            arm="coder",  # Future: dedicated sentiment arm
            estimated_cost=0.80,
            estimated_time=300
        ),
        Step(
            step_id="4",
            description="Aggregate results and compute overall sentiment",
            arm="judge",
            estimated_cost=0.10,
            estimated_time=30
        )
    ],
    total_estimated_cost=0.90,
    total_estimated_time=365
)
```

**LLM Prompt Template** (from `ref-docs/OctoLLM-Architecture-Implementation.md`):
```python
PLANNING_PROMPT = """
You are the Planner Arm of OctoLLM, responsible for breaking down complex tasks into executable subtasks.

Task Goal: {goal}
Constraints: {constraints}
Acceptance Criteria: {acceptance_criteria}
Budget: Max ${max_cost_usd}, {max_time_seconds}s, {max_tokens} tokens

Available Arms:
- planner: Task decomposition, workflow generation
- tool_executor: Run shell commands, API calls (sandboxed)
- retriever: Search knowledge base, fetch documents
- coder: Generate code, debug, refactor
- judge: Validate outputs, check acceptance criteria

Instructions:
1. Decompose the goal into 3-10 concrete steps
2. Assign each step to an appropriate arm
3. Estimate cost and time for each step
4. Ensure total cost/time within budget
5. Steps must be executable and verifiable
6. Output ONLY valid JSON (no explanation)

Output JSON Schema:
{{
  "steps": [
    {{"step_id": "1", "description": "...", "arm": "...", "estimated_cost": 0.0, "estimated_time": 0}},
    ...
  ]
}}
"""
```

**Technology Stack**:
- Python 3.11+ (consistency with Orchestrator)
- FastAPI (same framework as Orchestrator)
- OpenAI SDK or Anthropic SDK for LLM calls
- Redis for plan caching (SHA-256 of goal → plan)
- Pydantic for request/response validation

**Performance Targets**:
- Plan Generation Latency (P95): <5s (includes LLM call)
- Cache Hit Rate: >40% after warmup
- Plan Validation: <100ms

### 2. Pipeline Architecture

**Objective**: Orchestrate task execution through multiple arms.

**Core Flow**:
```python
# app/pipeline.py

async def process_task(task_id: UUID, db: Database, arm_registry: ArmRegistry):
    """Process task through pipeline."""

    # 1. Fetch task from database
    task = await db.get_task(task_id)

    # 2. Update status to processing
    await db.update_task_status(task_id, TaskStatus.PROCESSING)

    # 3. Call Planner Arm to generate plan
    plan = await arm_registry.call_arm(
        arm_name="planner",
        task_contract=task.to_contract()
    )

    # 4. Execute plan steps sequentially (parallel execution in future)
    results = []
    for step in plan.steps:
        result = await arm_registry.call_arm(
            arm_name=step.arm,
            input_data=step.input_data
        )
        results.append(result)

    # 5. Aggregate results
    final_result = aggregate_results(results)

    # 6. Store result in database
    await db.create_task_result(
        task_id=task_id,
        result_data=final_result,
        confidence=final_result.get("confidence", 1.0)
    )

    # 7. Update task status to completed
    await db.update_task_status(task_id, TaskStatus.COMPLETED)
```

**Error Handling**:
```python
try:
    await process_task(task_id, db, arm_registry)
except ArmUnavailable as e:
    # Arm is down, retry later
    await db.update_task_status(task_id, TaskStatus.PENDING)
    logger.warning(f"Arm unavailable: {e.arm_name}, retrying task {task_id}")
except TaskTimeout as e:
    # Task exceeded max_time_seconds
    await db.update_task_status(task_id, TaskStatus.FAILED)
    logger.error(f"Task {task_id} timed out after {e.elapsed}s")
except Exception as e:
    # Unexpected error
    await db.update_task_status(task_id, TaskStatus.FAILED)
    logger.exception(f"Task {task_id} failed with unexpected error")
```

### 3. Background Worker

**Objective**: Process tasks asynchronously without blocking API requests.

**Implementation Options**:

**Option A: Redis Streams (Recommended)**
```python
# app/worker.py

async def worker_loop():
    """Main worker loop using Redis Streams."""
    redis = await create_redis_client()

    while True:
        # 1. Read pending tasks from stream
        tasks = await redis.xread(
            streams={"octollm:tasks": "$"},
            count=1,
            block=1000  # Block for 1 second
        )

        # 2. Process each task
        for stream, messages in tasks:
            for message_id, data in messages:
                task_id = UUID(data[b"task_id"].decode())

                try:
                    await process_task(task_id, db, arm_registry)
                    await redis.xack("octollm:tasks", "workers", message_id)
                except Exception as e:
                    logger.exception(f"Worker failed to process task {task_id}")
                    # Requeue or mark as failed
```

**Option B: Celery (Alternative)**
```python
# app/worker.py

from celery import Celery

celery = Celery("octollm", broker="redis://localhost:6379/0")

@celery.task
def process_task_async(task_id: str):
    """Celery task for async processing."""
    asyncio.run(process_task(UUID(task_id), db, arm_registry))
```

**Graceful Shutdown**:
```python
import signal

def handle_shutdown(signum, frame):
    """Handle SIGTERM/SIGINT for graceful shutdown."""
    logger.info("Received shutdown signal, finishing current task...")
    # Finish current task, then exit
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)
```

### 4. Arm Registry

**Objective**: Dynamic routing to arms based on capabilities and health.

**Implementation**:
```python
# app/arm_registry.py

class ArmRegistry:
    """Registry of available arms with health tracking."""

    def __init__(self):
        self.arms: Dict[str, ArmClient] = {}
        self.health_status: Dict[str, bool] = {}

    def register_arm(self, name: str, url: str, capabilities: List[str]):
        """Register new arm."""
        self.arms[name] = ArmClient(name=name, url=url, capabilities=capabilities)
        self.health_status[name] = True

    async def call_arm(self, arm_name: str, **kwargs) -> Dict:
        """Call arm with automatic retry and fallback."""
        if not self.health_status.get(arm_name, False):
            raise ArmUnavailable(arm_name)

        try:
            result = await self.arms[arm_name].call(**kwargs)
            return result
        except Exception as e:
            # Mark arm as unhealthy
            self.health_status[arm_name] = False
            logger.error(f"Arm {arm_name} failed: {e}")
            raise ArmUnavailable(arm_name)

    async def health_check_loop(self):
        """Periodic health checks for all arms."""
        while True:
            for name, client in self.arms.items():
                try:
                    await client.health_check()
                    self.health_status[name] = True
                except Exception:
                    self.health_status[name] = False

            await asyncio.sleep(30)  # Check every 30 seconds
```

**Arm Client**:
```python
class ArmClient:
    """HTTP client for arm communication."""

    def __init__(self, name: str, url: str, capabilities: List[str]):
        self.name = name
        self.url = url
        self.capabilities = capabilities
        self.client = httpx.AsyncClient(timeout=30.0)

    async def call(self, **kwargs) -> Dict:
        """Call arm endpoint."""
        response = await self.client.post(
            f"{self.url}/execute",
            json=kwargs
        )
        response.raise_for_status()
        return response.json()

    async def health_check(self) -> bool:
        """Check arm health."""
        response = await self.client.get(f"{self.url}/health")
        return response.status_code == 200
```

---

## Implementation Guidance

### Phase 1: Planner Arm Service (12-16 hours)

**Step 1: Project Setup** (2 hours)
```bash
# Create Planner service directory
mkdir -p services/planner
cd services/planner

# Initialize Python project
# Similar to orchestrator structure:
# services/planner/
# ├── app/
# │   ├── __init__.py
# │   ├── main.py          # FastAPI app
# │   ├── planner.py       # Planning logic
# │   ├── llm_client.py    # OpenAI/Anthropic client
# │   └── config.py        # Configuration
# ├── tests/
# ├── pyproject.toml
# └── README.md
```

**Step 2: LLM Integration** (4 hours)
```python
# app/llm_client.py

from openai import AsyncOpenAI

class LLMClient:
    """Async client for LLM API calls."""

    def __init__(self, api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate_plan(self, task_contract: TaskContract) -> Plan:
        """Generate plan using LLM."""
        prompt = PLANNING_PROMPT.format(
            goal=task_contract.goal,
            constraints=task_contract.constraints,
            acceptance_criteria=task_contract.acceptance_criteria,
            max_cost_usd=task_contract.budget.max_cost_usd,
            max_time_seconds=task_contract.budget.max_time_seconds,
            max_tokens=task_contract.budget.max_tokens
        )

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are the Planner Arm."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # Low temperature for consistent planning
            max_tokens=2000
        )

        # Parse JSON response
        plan_json = response.choices[0].message.content
        return Plan.parse_raw(plan_json)
```

**Step 3: FastAPI Endpoints** (3 hours)
```python
# app/main.py

from fastapi import FastAPI, HTTPException
from app.planner import Planner
from app.models import TaskContract, Plan

app = FastAPI(title="OctoLLM Planner Arm", version="1.0.0")
planner = Planner()

@app.post("/execute", response_model=Plan)
async def execute(task: TaskContract):
    """Generate plan for task."""
    try:
        plan = await planner.generate_plan(task)
        return plan
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    """Health check."""
    return {"status": "healthy"}
```

**Step 4: Plan Caching** (3 hours)
```python
# app/planner.py

import hashlib
from redis import asyncio as aioredis

class Planner:
    """Task planning with LLM and caching."""

    def __init__(self, llm_client: LLMClient, redis_client: aioredis.Redis):
        self.llm = llm_client
        self.redis = redis_client

    async def generate_plan(self, task: TaskContract) -> Plan:
        """Generate plan with caching."""
        # 1. Generate cache key
        cache_key = self._cache_key(task.goal)

        # 2. Check cache
        cached = await self.redis.get(cache_key)
        if cached:
            return Plan.parse_raw(cached)

        # 3. Generate plan with LLM
        plan = await self.llm.generate_plan(task)

        # 4. Validate plan
        self._validate_plan(plan, task.budget)

        # 5. Cache plan (24 hour TTL)
        await self.redis.set(cache_key, plan.json(), ex=86400)

        return plan

    def _cache_key(self, goal: str) -> str:
        """Generate SHA-256 cache key from goal."""
        return f"plan:{hashlib.sha256(goal.encode()).hexdigest()}"

    def _validate_plan(self, plan: Plan, budget: ResourceBudget):
        """Validate plan against budget constraints."""
        if plan.total_estimated_cost > budget.max_cost_usd:
            raise ValueError(f"Plan cost ${plan.total_estimated_cost} exceeds budget ${budget.max_cost_usd}")
        if plan.total_estimated_time > budget.max_time_seconds:
            raise ValueError(f"Plan time {plan.total_estimated_time}s exceeds budget {budget.max_time_seconds}s")
```

### Phase 2: Pipeline Module (8-10 hours)

**Implementation in** `services/orchestrator/app/pipeline.py`:

```python
from typing import List, Dict
from app.models import TaskContract, TaskStatus
from app.database import Database
from app.arm_registry import ArmRegistry

class Pipeline:
    """Task processing pipeline."""

    def __init__(self, db: Database, arm_registry: ArmRegistry):
        self.db = db
        self.arms = arm_registry

    async def process_task(self, task_id: UUID):
        """Process task through pipeline."""
        # Implementation as outlined above
        ...
```

### Phase 3: Background Worker (6-8 hours)

**Implementation in** `services/orchestrator/app/worker.py`:

```python
# Redis Streams approach (recommended)
async def worker_main():
    """Main worker entry point."""
    db = Database(settings.database_url)
    await db.create_tables()

    arm_registry = ArmRegistry()
    # Register Planner Arm
    arm_registry.register_arm(
        name="planner",
        url=settings.planner_url,
        capabilities=["planning", "decomposition"]
    )

    # Start health check loop
    asyncio.create_task(arm_registry.health_check_loop())

    # Start worker loop
    await worker_loop(db, arm_registry)

if __name__ == "__main__":
    asyncio.run(worker_main())
```

### Phase 4: Integration Testing (6-8 hours)

**End-to-End Test**:
```python
# tests/test_integration.py

@pytest.mark.asyncio
async def test_end_to_end_task_processing():
    """Test complete task flow: submit → plan → process → complete."""

    # 1. Submit task
    response = await client.post("/submit", json={
        "goal": "Analyze sentiment of product reviews",
        "constraints": ["No PII"],
        "acceptance_criteria": ["Sentiment score -1 to 1"],
        "priority": "high"
    })
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    # 2. Wait for processing (poll status)
    for _ in range(30):  # Max 30 seconds
        response = await client.get(f"/tasks/{task_id}")
        status = response.json()["status"]

        if status == "completed":
            break
        elif status == "failed":
            pytest.fail("Task failed")

        await asyncio.sleep(1)

    # 3. Verify result
    assert status == "completed"
    response = await client.get(f"/tasks/{task_id}/results")
    results = response.json()
    assert len(results) > 0
    assert "sentiment_score" in results[0]["result_data"]
```

---

## Testing Strategy for Sprint 1.3

### Unit Tests (Target: 100+ tests)

1. **Planner Arm**: 30+ tests
   - LLM client mocking
   - Plan generation and validation
   - Cache hit/miss scenarios
   - Budget constraint checking
   - Error handling

2. **Pipeline Module**: 25+ tests
   - Task processing flow
   - Error recovery
   - Status transitions
   - Result aggregation

3. **Arm Registry**: 20+ tests
   - Arm registration and lookup
   - Health tracking
   - Failover scenarios
   - Circuit breaker integration

4. **Background Worker**: 15+ tests
   - Queue processing
   - Graceful shutdown
   - Concurrent task handling
   - Error recovery

### Integration Tests (Target: 20+ tests)

1. **End-to-End**: 10+ tests
   - Full task flow (submit → complete)
   - Error scenarios (Reflex block, Planner timeout)
   - Concurrent tasks
   - Worker restarts

2. **Service Integration**: 10+ tests
   - Orchestrator ↔ Planner communication
   - Orchestrator ↔ Reflex Layer communication
   - Database persistence across services
   - Redis queue operations

### Load Tests (Target: 3-5 scenarios)

```python
# tests/load_test.py using locust

from locust import HttpUser, task, between

class OrchestratorUser(HttpUser):
    wait_time = between(1, 3)

    @task
    def submit_task(self):
        self.client.post("/submit", json={
            "goal": "Test task",
            "priority": "medium"
        })

    @task(3)  # 3x more frequent
    def get_task_status(self):
        # Randomly select task_id from submitted tasks
        task_id = random.choice(self.task_ids)
        self.client.get(f"/tasks/{task_id}")
```

**Load Test Scenarios**:
1. 10 concurrent users, 100 requests/min
2. 50 concurrent users, 500 requests/min
3. 100 concurrent users, 1000 requests/min (stress test)

---

## Critical Dependencies

### External Services

1. **Reflex Layer** (from Sprint 1.1)
   - Base URL: `http://localhost:8080`
   - Status: ✅ Production-ready
   - Endpoints: `/process`, `/health`, `/ready`, `/metrics`

2. **PostgreSQL 15+**
   - Required for task persistence
   - Schema defined in Sprint 1.2
   - Connection: `postgresql+asyncpg://...`

3. **Redis 7+** (NEW for Sprint 1.3)
   - Plan caching (Planner Arm)
   - Task queue (Background Worker)
   - Distributed rate limiting (future)

### LLM Provider

**Recommended**: OpenAI GPT-3.5-turbo
- Cost: ~$0.001 per task (2K tokens)
- Latency: 1-3s P95
- Quality: Good for structured JSON output

**Alternative**: Anthropic Claude 3 Haiku
- Cost: ~$0.00025 per task (cheaper)
- Latency: 1-2s P95
- Quality: Excellent for structured tasks

**Local Option**: Ollama + Mistral 7B
- Cost: $0 (self-hosted)
- Latency: 3-10s P95 (depends on hardware)
- Quality: Acceptable for simple planning

---

## Known Issues and Workarounds

### Issue 1: SQLAlchemy Reserved Attributes

**Problem**: SQLAlchemy reserves certain attribute names (`metadata`, `type`, `format`, etc.). Using these as column names causes conflicts.

**Workaround**: Use alternative names:
- `metadata` → `task_metadata`
- `type` → `task_type`
- `format` → `output_format`

**Reference**: Sprint 1.2 Bug Fix #1

---

### Issue 2: Async Relationship Loading

**Problem**: SQLAlchemy 2.0 uses lazy loading by default. Accessing relationships in async context raises errors.

**Workaround**: Use explicit eager loading:
```python
from sqlalchemy.orm import selectinload

task = await session.execute(
    select(Task)
    .options(selectinload(Task.results))
    .where(Task.id == task_id)
)
```

**Reference**: Sprint 1.2 Bug Fix #4

---

### Issue 3: Circuit Breaker State Persistence

**Problem**: Circuit breaker state is in-memory. When Orchestrator restarts, state is lost.

**Workaround (Future)**: Store circuit breaker state in Redis for persistence across restarts.

**Current**: Acceptable for Sprint 1.3 (stateless circuit breaker per instance)

---

## Performance Targets for Sprint 1.3

| Metric | Sprint 1.2 | Sprint 1.3 Target |
|--------|------------|-------------------|
| Task Submission (POST /submit) | <100ms | <100ms (no change) |
| Task Status Query (GET /tasks/{id}) | <50ms | <50ms (no change) |
| **Plan Generation (Planner Arm)** | N/A | **<5s P95** |
| **End-to-End Task Latency** | N/A | **<10s P95** (simple tasks) |
| **Concurrent Tasks** | N/A | **50+ tasks/min** |
| Database Query Latency | <5ms | <5ms (no change) |
| Reflex Layer Call | <50ms | <50ms (no change) |
| Plan Cache Hit Rate | N/A | **>40% after warmup** |

---

## Success Criteria for Sprint 1.3

### Functional Requirements

- [ ] Planner Arm service operational with `/execute` and `/health` endpoints
- [ ] LLM integration working (OpenAI or Anthropic)
- [ ] Plan caching implemented with Redis
- [ ] Pipeline module processes tasks end-to-end
- [ ] Background worker consumes tasks from queue
- [ ] Arm registry tracks Planner Arm health
- [ ] Integration tests passing (20+ tests)
- [ ] Load tests demonstrate 50+ tasks/min throughput

### Quality Requirements

- [ ] Test coverage ≥85% on all new modules
- [ ] All tests passing (100% pass rate)
- [ ] No critical bugs or security vulnerabilities
- [ ] Code passes Black formatting and Ruff linting
- [ ] Type hints added for mypy checking

### Documentation Requirements

- [ ] Planner Arm README.md with API documentation
- [ ] Pipeline and Worker usage guide
- [ ] Integration testing guide
- [ ] Sprint 1.3 completion report
- [ ] Sprint 1.4 handoff document

### Performance Requirements

- [ ] Plan generation latency <5s P95
- [ ] End-to-end task latency <10s P95 (simple tasks)
- [ ] Concurrent throughput ≥50 tasks/min
- [ ] Plan cache hit rate >40% after warmup

---

## References

### Sprint 1.2 Deliverables

- [Orchestrator README](../../services/orchestrator/README.md) - Developer guide
- [Orchestrator Component Docs](../../docs/components/orchestrator.md) - Implementation details
- [Orchestrator OpenAPI Spec](../../docs/api/openapi/orchestrator.yaml) - API reference
- [Sprint 1.2 Completion Report](../../docs/phases/sprint-1.2/SPRINT-1.2-COMPLETION.md) - Sprint summary

### Architecture References

- [Project Overview](../../ref-docs/OctoLLM-Project-Overview.md) - Vision, use cases, roadmap
- [Architecture Implementation](../../ref-docs/OctoLLM-Architecture-Implementation.md) - Technical blueprint, component specs
- [Concept & Ideas](../../ref-docs/OctoLLM-Concept_Idea.md) - Design patterns and decisions

### External Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/) - Web framework
- [SQLAlchemy 2.0](https://docs.sqlalchemy.org/en/20/) - ORM and async patterns
- [OpenAI API](https://platform.openai.com/docs/api-reference) - LLM integration
- [Redis Streams](https://redis.io/docs/data-types/streams/) - Task queue
- [httpx](https://www.python-httpx.org/) - Async HTTP client

---

## Next Steps: Getting Started

### Day 1: Setup and Planning

1. **Review Sprint 1.2 deliverables**
   - Read Orchestrator README.md
   - Run Orchestrator service locally
   - Test API endpoints with curl
   - Review database schema

2. **Design Planner Arm architecture**
   - Review reference docs
   - Design API contract (TaskContract → Plan)
   - Choose LLM provider (OpenAI vs Anthropic vs local)
   - Plan data models (Plan, Step)

3. **Set up development environment**
   - Install Redis locally
   - Set up LLM API keys
   - Create `services/planner/` directory structure
   - Initialize pyproject.toml

### Day 2-3: Planner Arm Implementation

1. **Core Planner Service**
   - Implement FastAPI app (`app/main.py`)
   - Create data models (`app/models.py`)
   - Implement LLM client (`app/llm_client.py`)
   - Add plan caching (`app/cache.py`)

2. **Testing**
   - Write unit tests for planner logic
   - Mock LLM responses
   - Test plan validation
   - Achieve 85%+ coverage

### Day 3-4: Pipeline and Worker

1. **Pipeline Module**
   - Implement `app/pipeline.py`
   - Add error handling and recovery
   - Integrate with Planner Arm
   - Write pipeline tests

2. **Background Worker**
   - Implement `app/worker.py` with Redis Streams
   - Add graceful shutdown
   - Test queue processing
   - Verify concurrent task handling

### Day 5: Integration Testing

1. **End-to-End Tests**
   - Write integration tests
   - Test with live Reflex Layer
   - Test with live Planner Arm
   - Verify full task flow

2. **Load Testing**
   - Set up locust or k6
   - Run load test scenarios
   - Profile performance
   - Identify bottlenecks

### Day 6: Documentation and Cleanup

1. **Documentation**
   - Write Planner Arm README
   - Document pipeline and worker
   - Create Sprint 1.3 completion report
   - Write Sprint 1.4 handoff

2. **Code Quality**
   - Run Black formatter
   - Run Ruff linter
   - Add type hints for mypy
   - Fix any remaining issues

---

**Sprint 1.3 Ready to Begin**: ✅
**Estimated Duration**: 30-40 hours (1-2 weeks)
**Blocking Issues**: None
**Prerequisites**: All met ✅

---

*End of Sprint 1.3 Handoff Document*
