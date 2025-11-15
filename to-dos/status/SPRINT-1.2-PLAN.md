# Sprint 1.2 Implementation Plan

**Sprint**: 1.2 - Orchestrator Integration
**Status**: IN PROGRESS
**Started**: 2025-11-15
**Estimated Duration**: 40-50 hours (1-1.5 weeks)
**Assigned To**: Autonomous Implementation Agent

---

## Objective

Create Python Orchestrator service that integrates with the Reflex Layer, establishing the core request processing pipeline for OctoLLM.

## Dependencies

### Prerequisites Met
- ✅ Sprint 1.1 COMPLETE (Reflex Layer v1.1.0 production-ready)
- ✅ Reflex Layer API documented (`docs/api/openapi/reflex-layer.yaml`)
- ✅ Handoff document prepared (`docs/handoffs/SPRINT-1.2-HANDOFF.md`)
- ✅ Redis 7+ available for caching
- ✅ Docker environment operational

### Prerequisites Needed
- 🔲 PostgreSQL 15+ database instance
- 🔲 Python 3.11+ environment setup
- 🔲 OpenAI API key (for future LLM integration)
- 🔲 pyproject.toml with dependencies

---

## Architecture Overview

```
User Request
    ↓
POST /submit
    ↓
[Orchestrator - FastAPI Service]
    ├─→ Validate Request (Pydantic)
    ├─→ Call Reflex Layer (PII/Injection Check)
    ├─→ Store Task in PostgreSQL
    ├─→ Queue Task for Processing
    └─→ Return task_id
         ↓
GET /tasks/{task_id}
    ↓
Return Status/Result
```

---

## Phase Breakdown

### Phase 1: Python Integration Layer (8-12 hours)

**Objective**: Create HTTP client for Reflex Layer communication

**Deliverables**:
- `services/orchestrator/app/reflex_client.py` (~300-400 lines)
- Unit tests: `services/orchestrator/tests/test_reflex_client.py` (20+ tests)
- Integration tests with real/mock Reflex Layer

**Tasks**:
1. Create ReflexClient class
   - Async HTTP client using httpx
   - POST /process endpoint integration
   - Request/response models (Pydantic)
   - Retry logic with exponential backoff (3 retries, 1s-5s delays)
   - Circuit breaker pattern (fail after 5 consecutive errors, reset after 60s)
   - Health check method (GET /health)
   - Metrics collection (request count, latency, errors)
   - Error handling and logging

2. Define Pydantic models
   - ReflexRequest (text, user_id, context)
   - ReflexResponse (pii_detected, injection_detected, status, details)
   - Error models

3. Write unit tests
   - Test successful requests
   - Test retry logic (mock failures)
   - Test circuit breaker activation
   - Test timeout handling
   - Test health check
   - Test error scenarios

4. Write integration tests
   - Test with real Reflex Layer (if running)
   - Test with mock HTTP responses
   - Verify request/response format

**Acceptance Criteria**:
- ✅ ReflexClient makes successful POST /process requests
- ✅ Retry logic working (3 attempts with exponential backoff)
- ✅ Circuit breaker activates after 5 failures
- ✅ Health check method functional
- ✅ 20+ unit tests passing
- ✅ Integration tests passing

---

### Phase 2: Orchestrator Core (12-16 hours)

**Objective**: Implement FastAPI service skeleton with task management

**Deliverables**:
- `services/orchestrator/app/main.py` (~400-500 lines)
- `services/orchestrator/app/models.py` (~200-300 lines)
- `services/orchestrator/app/database.py` (~200-250 lines)
- `services/orchestrator/app/config.py` (~150-200 lines)
- Database migration scripts
- Unit tests (30+ tests, 85% coverage)

**Tasks**:

1. **Create main.py** (FastAPI application)
   - FastAPI app initialization
   - POST /submit endpoint (task submission)
   - GET /tasks/{task_id} endpoint (task status)
   - GET /health endpoint (Kubernetes liveness)
   - GET /ready endpoint (Kubernetes readiness)
   - GET /metrics endpoint (Prometheus metrics)
   - Database connection setup
   - Background task processing
   - Error handlers (404, 500)
   - CORS middleware
   - Request ID middleware

2. **Create models.py** (Data models)
   - TaskContract (Pydantic model from ref-docs)
     - task_id: str
     - goal: str
     - constraints: Dict[str, Any]
     - context: Optional[str]
     - acceptance_criteria: List[str]
     - budget: ResourceBudget
     - assigned_arm: Optional[str]
     - metadata: Dict[str, Any]
   - TaskStatus enum (pending, processing, completed, failed, cancelled)
   - TaskRequest (POST /submit request body)
   - TaskResponse (GET /tasks/{task_id} response)
   - ResourceBudget (max_tokens, max_time_seconds, max_cost_usd)
   - Database ORM models (SQLAlchemy)

3. **Create database.py** (Database layer)
   - PostgreSQL connection pooling
   - Session management (async)
   - Task CRUD operations
     - create_task(task: TaskContract) → task_id
     - get_task(task_id: str) → Task
     - update_task_status(task_id: str, status: TaskStatus)
     - store_task_result(task_id: str, result: Dict)
   - Migration support (Alembic)

4. **Create config.py** (Configuration)
   - Environment variable loading
   - Service URLs (Reflex Layer, PostgreSQL, Redis)
   - Timeouts and retry settings
   - Feature flags
   - Validation

5. **Create database migrations**
   - Initialize Alembic
   - Create tasks table
     - id (UUID primary key)
     - goal (TEXT)
     - status (ENUM)
     - constraints (JSONB)
     - context (TEXT)
     - acceptance_criteria (JSONB)
     - budget (JSONB)
     - assigned_arm (VARCHAR)
     - metadata (JSONB)
     - created_at (TIMESTAMP)
     - updated_at (TIMESTAMP)
   - Create task_results table
     - task_id (UUID foreign key)
     - result (JSONB)
     - error (TEXT)
     - processing_time_ms (INTEGER)
     - created_at (TIMESTAMP)
   - Indexes for performance
     - idx_tasks_status
     - idx_tasks_created_at

6. **Write unit tests**
   - Test all endpoints (FastAPI TestClient)
   - Test database operations (SQLAlchemy fixtures)
   - Test model validation
   - Test error handling
   - Test health/ready checks
   - Test metrics endpoint

**Acceptance Criteria**:
- ✅ FastAPI app starts successfully
- ✅ All 6 endpoints functional
- ✅ Database connection working
- ✅ Task CRUD operations working
- ✅ 30+ unit tests passing
- ✅ 85% code coverage

---

### Phase 3: End-to-End Flow (8-10 hours)

**Objective**: Implement complete request pipeline

**Deliverables**:
- `services/orchestrator/app/pipeline.py` (~300-400 lines)
- Integration tests (~15 tests)
- E2E test scenarios (~5 scenarios)

**Tasks**:

1. **Create pipeline.py** (Request processing pipeline)
   - process_task(task: TaskContract) → TaskResult
   - Validation logic
   - Reflex Layer integration
   - Task routing logic (placeholder for future arms)
   - Response aggregation
   - Error recovery and fallback strategies

2. **Implement request flow**
   - User → POST /submit
   - Validate request (Pydantic)
   - Call Reflex Layer for PII/injection check
   - If safe, create task in database
   - Queue task for background processing (asyncio)
   - Return task_id (202 Accepted)
   - Background worker processes task
   - User polls GET /tasks/{task_id}
   - Return result when complete

3. **Implement background processing**
   - Task queue (asyncio Queue or Redis)
   - Worker process
   - Task completion notification
   - Error handling

4. **Write integration tests**
   - E2E test with real Reflex Layer
   - E2E test with PostgreSQL
   - Concurrent request handling
   - Error scenarios (Reflex Layer down, DB unavailable)
   - Timeout handling

5. **Write E2E test scenarios**
   - Test 1: Simple task submission and retrieval
   - Test 2: Task with PII (blocked by Reflex)
   - Test 3: Task with injection attempt (blocked)
   - Test 4: Multiple concurrent tasks
   - Test 5: Task cancellation

**Acceptance Criteria**:
- ✅ Complete request pipeline functional
- ✅ Reflex Layer integration working
- ✅ Background task processing working
- ✅ 15+ integration tests passing
- ✅ 5 E2E scenarios passing
- ✅ Error recovery functional

---

### Phase 4: Testing & Documentation (6-8 hours)

**Objective**: Ensure quality and completeness

**Deliverables**:
- Comprehensive test suite (50+ tests total)
- Updated documentation (5+ files)
- Sprint completion report
- Sprint 1.3 handoff document

**Tasks**:

1. **Achieve 85%+ test coverage**
   - Run `pytest --cov=app --cov-report=html`
   - Identify uncovered code
   - Add tests for edge cases
   - Verify all branches covered

2. **Run integration tests**
   - Start Docker Compose (PostgreSQL, Redis, Reflex Layer)
   - Run full integration test suite
   - Verify all services communicate correctly

3. **Update documentation**
   - `docs/components/orchestrator.md` - Component documentation
   - `services/orchestrator/README.md` - Service README
   - `docs/api/openapi/orchestrator.yaml` - OpenAPI 3.0 spec
   - `docs/phases/sprint-1.2/SPRINT-1.2-COMPLETION.md` - Completion report

4. **Create handoff document**
   - `docs/handoffs/SPRINT-1.3-HANDOFF.md` - Next sprint preparation
   - Summary of what was delivered
   - Prerequisites for Sprint 1.3
   - Recommended approach

5. **Update project files**
   - `CHANGELOG.md` - Add Sprint 1.2 entry
   - `to-dos/MASTER-TODO.md` - Mark Sprint 1.2 complete

**Acceptance Criteria**:
- ✅ Test coverage ≥85%
- ✅ All tests passing (100% pass rate)
- ✅ Documentation complete
- ✅ Sprint completion report created
- ✅ Sprint 1.3 handoff created

---

## Technology Stack

### Languages & Frameworks
- Python 3.11+
- FastAPI 0.104+ (async web framework)
- Pydantic 2.4+ (data validation)
- SQLAlchemy 2.0+ (ORM)
- Alembic 1.12+ (migrations)
- httpx 0.25+ (async HTTP client)

### Databases
- PostgreSQL 15+ (task persistence)
- Redis 7+ (optional: task queue)

### Testing
- pytest 7.4+
- pytest-asyncio 0.21+
- pytest-cov 4.1+
- httpx (mock HTTP)
- FastAPI TestClient

### Quality Tools
- Black (formatting)
- Ruff (linting)
- mypy (type checking)

---

## Dependencies to Add

Create `services/orchestrator/pyproject.toml`:

```toml
[project]
name = "octollm-orchestrator"
version = "0.1.0"
description = "OctoLLM Orchestrator Service - Central brain for AI orchestration"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.4.0",
    "pydantic-settings>=2.0.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "psycopg[binary]>=3.1.0",
    "httpx>=0.25.0",
    "tenacity>=8.2.0",
    "redis>=5.0.0",
    "prometheus-client>=0.18.0",
    "python-multipart>=0.0.6",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "black>=23.10.0",
    "ruff>=0.1.0",
    "mypy>=1.6.0",
    "httpx[testing]>=0.25.0",
]

[build-system]
requires = ["setuptools>=68.0.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = [
    "-v",
    "--strict-markers",
    "--cov=app",
    "--cov-report=term-missing",
    "--cov-report=html",
]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

---

## Risk Assessment

### High Risk
- **PostgreSQL Setup**: Need database instance (mitigation: use Docker Compose)
- **Integration Complexity**: Multiple services communicating (mitigation: thorough testing)

### Medium Risk
- **Async Complexity**: AsyncIO and async HTTP (mitigation: use proven libraries)
- **Database Migrations**: Schema changes (mitigation: use Alembic)

### Low Risk
- **Testing Coverage**: Achieving 85% (mitigation: systematic testing approach)
- **Documentation**: Keeping docs in sync (mitigation: write docs alongside code)

---

## Success Criteria

Sprint 1.2 is COMPLETE when ALL of the following are true:

- ✅ All 4 phases implemented (Python client, Core, E2E flow, Testing)
- ✅ ReflexClient working (async, retry, circuit breaker)
- ✅ FastAPI service running (5+ endpoints)
- ✅ Database integration working (PostgreSQL via SQLAlchemy)
- ✅ E2E flow tested (User → Orchestrator → Reflex → Response)
- ✅ Tests passing (50+ tests, 100% pass rate)
- ✅ Coverage ≥85% (pytest-cov)
- ✅ Pre-commit hooks passing
- ✅ Documentation updated (5+ files)
- ✅ Sprint completion report created
- ✅ Sprint 1.3 handoff document created
- ✅ Ready to commit (conventional commits format)

---

## Timeline

| Phase | Duration | Status |
|-------|----------|--------|
| Phase 1: Python Integration | 8-12h | 🔲 Pending |
| Phase 2: Orchestrator Core | 12-16h | 🔲 Pending |
| Phase 3: E2E Flow | 8-10h | 🔲 Pending |
| Phase 4: Testing & Docs | 6-8h | 🔲 Pending |
| **Total** | **40-50h** | **🔲 In Progress** |

---

## Next Steps

1. ✅ Create planning documents (CURRENT)
2. 🔲 Set up Python environment
3. 🔲 Create pyproject.toml
4. 🔲 Implement Phase 1: ReflexClient
5. 🔲 Implement Phase 2: Orchestrator Core
6. 🔲 Implement Phase 3: E2E Flow
7. 🔲 Implement Phase 4: Testing & Documentation
8. 🔲 Quality Assurance
9. 🔲 Final Report

---

**Document Status**: ✅ COMPLETE
**Last Updated**: 2025-11-15
**Next Review**: After Phase 1 completion
