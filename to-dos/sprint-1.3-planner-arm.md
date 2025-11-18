# Sprint 1.3: Planner Arm Implementation

**Sprint**: 1.3
**Component**: Planner Arm
**Status**: IN PROGRESS
**Started**: 2025-11-18
**Target Completion**: TBD
**Assignee**: Claude (AI Assistant)

---

## Overview

Sprint 1.3 implements the Planner Arm, a specialized component responsible for intelligent task decomposition. The Planner Arm breaks complex goals into 3-7 sequential subtasks with clear acceptance criteria, dependency tracking, and arm assignments.

### Objectives

1. **Build task decomposition service** using GPT-3.5-turbo for cost efficiency
2. **Implement dependency resolution** to ensure correct execution order
3. **Create comprehensive test suite** with 85%+ coverage
4. **Integrate with Orchestrator** for end-to-end task planning
5. **Deploy via Docker Compose** for local development

### Success Criteria

- [ ] Planner Arm generates valid 3-7 step plans
- [ ] Dependencies are correctly ordered (no circular/forward dependencies)
- [ ] 90%+ success rate on test tasks (30+ diverse scenarios)
- [ ] All tests pass with 85%+ coverage
- [ ] Integration with Orchestrator works end-to-end
- [ ] Docker Compose deployment functional
- [ ] Linters pass (ruff, mypy, black)
- [ ] Complete documentation

---

## Architecture Reference

### Technology Stack

- **Language**: Python 3.11+
- **Framework**: FastAPI 0.104+
- **LLM**: OpenAI GPT-3.5-turbo (cost tier 2)
- **Validation**: Pydantic 2.4+
- **Logging**: structlog
- **Metrics**: prometheus-client
- **Testing**: pytest, pytest-asyncio, pytest-cov

### Code Structure

Following the orchestrator pattern but with `src/` directory structure:

```
services/arms/planner/
├── src/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings management
│   ├── models.py            # Pydantic models
│   ├── planner.py           # Core planning logic
│   └── prompts.py           # LLM prompts
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── test_config.py       # Config tests
│   ├── test_models.py       # Model validation tests
│   ├── test_planner.py      # Planning logic tests
│   ├── test_main.py         # API endpoint tests
│   └── test_integration.py  # E2E tests
├── pyproject.toml           # Dependencies and tools
├── Dockerfile               # Already exists
└── README.md                # Service documentation
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/plan` | POST | Generate execution plan from goal |
| `/health` | GET | Health check (liveness) |
| `/ready` | GET | Readiness check |
| `/metrics` | GET | Prometheus metrics |
| `/capabilities` | GET | Arm capabilities |

---

## Phase 1: Project Setup

### 1.1 Create pyproject.toml

**Task**: Set up Python project configuration with all dependencies

**Dependencies**:
```toml
[project]
name = "octollm-planner-arm"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "pydantic>=2.4.0",
    "pydantic-settings>=2.0.0",
    "openai>=1.3.0",           # OpenAI SDK
    "httpx>=0.25.0",
    "tenacity>=8.2.0",         # Retry logic
    "prometheus-client>=0.18.0",
    "structlog>=23.2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.0",
    "pytest-cov>=4.1.0",
    "pytest-mock>=3.12.0",
    "black>=23.10.0",
    "ruff>=0.1.0",
    "mypy>=1.6.0",
]
```

**Acceptance Criteria**:
- [ ] pyproject.toml created with all dependencies
- [ ] Tool configurations (black, ruff, mypy, pytest) match orchestrator patterns
- [ ] Coverage target set to 85%+

### 1.2 Create Configuration Module

**File**: `src/config.py`

**Requirements**:
- Use Pydantic Settings with environment variable support
- Prefix: `PLANNER_`
- Required settings:
  - `openai_api_key`: OpenAI API key (required)
  - `llm_model`: Default GPT-3.5-turbo
  - `planning_temperature`: 0.3 (low for consistency)
  - `max_tokens`: 2000
  - `max_plan_steps`: 7
  - `min_plan_steps`: 3
  - `timeout_seconds`: 10
  - Service metadata (name, version, environment)

**Pattern**: Follow `services/orchestrator/app/config.py`

**Acceptance Criteria**:
- [ ] Settings class with all required fields
- [ ] Field validators for critical settings
- [ ] Singleton pattern with `get_settings()`
- [ ] Type hints for all fields
- [ ] Docstrings for all fields

---

## Phase 2: Data Models

### 2.1 Create Pydantic Models

**File**: `src/models.py`

**Models to implement** (based on `docs/components/arms/planner-arm.md`):

```python
class SubTask(BaseModel):
    """A single step in the execution plan."""
    step: int
    action: str
    required_arm: str
    acceptance_criteria: List[str]
    depends_on: List[int] = Field(default_factory=list)
    estimated_cost_tier: int = Field(1, ge=1, le=5)
    estimated_duration_seconds: int = Field(30, ge=1)

class PlanResponse(BaseModel):
    """Complete execution plan."""
    plan: List[SubTask]
    rationale: str
    confidence: float = Field(ge=0.0, le=1.0)
    total_estimated_duration: int
    complexity_score: float = Field(ge=0.0, le=1.0)

class PlanRequest(BaseModel):
    """Incoming planning request."""
    goal: str
    constraints: List[str] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    request_id: Optional[str] = Field(default_factory=lambda: str(uuid4()))

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    model: str
    timestamp: str

class CapabilitiesResponse(BaseModel):
    """Arm capabilities response."""
    arm_id: str
    capabilities: List[str]
    cost_tier: int
    average_latency_ms: int
    success_rate: float
```

**Acceptance Criteria**:
- [ ] All models defined with proper field types
- [ ] Field validators where needed
- [ ] Default factories for mutable defaults
- [ ] Proper constraints (ge, le, min_length, max_length)
- [ ] Docstrings for all models and fields

### 2.2 Add Model Validation Tests

**File**: `tests/test_models.py`

**Test cases**:
- Valid SubTask creation
- Invalid dependencies (forward/non-existent)
- Cost tier bounds (1-5)
- Confidence score bounds (0.0-1.0)
- PlanRequest with various inputs
- Model serialization/deserialization

**Acceptance Criteria**:
- [ ] 15+ test cases covering all models
- [ ] Edge case testing (empty lists, None values)
- [ ] Validation error testing

---

## Phase 3: Core Planning Logic

### 3.1 Create Prompt Templates

**File**: `src/prompts.py`

**Requirements**:
- System prompt defining available arms and capabilities
- User prompt template with goal, constraints, context
- JSON schema specification for structured output
- Clear instructions for dependency handling

**Key arms to document**:
- planner: Task decomposition, planning
- retriever: Knowledge search, documentation
- coder: Code generation, debugging
- executor: Command execution, API calls
- judge: Validation, quality assurance
- guardian: PII detection, safety checks

**Acceptance Criteria**:
- [ ] System prompt with arm capability descriptions
- [ ] User prompt template (format string)
- [ ] JSON schema enforcement instructions
- [ ] Dependency rules clearly stated
- [ ] Quality criteria (3-7 steps, validation step)

### 3.2 Implement Planning Logic

**File**: `src/planner.py`

**Class**: `PlannerArm`

**Methods**:
```python
async def generate_plan(
    goal: str,
    constraints: List[str],
    context: Dict[str, Any]
) -> PlanResponse:
    """Generate execution plan using LLM."""

async def _call_llm(prompt: str) -> str:
    """Call OpenAI API with retry logic."""

def _validate_dependencies(steps: List[Dict]) -> None:
    """Ensure dependencies are valid."""

def _calculate_metrics(plan: List[SubTask]) -> Tuple[int, float]:
    """Calculate total duration and complexity."""
```

**Key features**:
- Retry logic with exponential backoff (tenacity)
- JSON parsing with error handling
- Dependency validation (no forward refs, no cycles)
- Metric calculation
- Structured logging

**Acceptance Criteria**:
- [ ] PlannerArm class implemented
- [ ] LLM integration with OpenAI SDK
- [ ] Retry logic (3 attempts, exponential backoff)
- [ ] Dependency validation prevents invalid plans
- [ ] Error handling for JSON parse failures
- [ ] Structured logging for all operations
- [ ] Type hints for all methods

### 3.3 Add Planning Logic Tests

**File**: `tests/test_planner.py`

**Test cases**:
- Basic plan generation (mock LLM)
- Complex plan with dependencies
- Dependency validation (invalid cases)
- JSON parsing errors
- LLM timeout/retry
- Metric calculation accuracy

**Acceptance Criteria**:
- [ ] 20+ test cases with mocked LLM calls
- [ ] Happy path and error path coverage
- [ ] Edge cases (min/max steps)

---

## Phase 4: FastAPI Application

### 4.1 Implement Main Application

**File**: `src/main.py`

**Structure**:
```python
from fastapi import FastAPI, HTTPException
from prometheus_client import Counter, Histogram
import structlog

# Metrics
PLAN_REQUEST_COUNTER = Counter(...)
PLAN_DURATION_HISTOGRAM = Histogram(...)
PLAN_SUCCESS_COUNTER = Counter(...)

# Lifespan manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: initialize planner, validate API key
    yield
    # Shutdown: cleanup

# Application
app = FastAPI(
    title="OctoLLM Planner Arm",
    version="0.1.0",
    lifespan=lifespan
)

# Endpoints
@app.post("/plan", response_model=PlanResponse)
async def create_plan(request: PlanRequest):
    """Generate execution plan."""

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""

@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""

@app.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities():
    """Return arm capabilities."""
```

**Middleware**:
- CORS (allow orchestrator)
- Request logging
- Metrics collection
- Error handling

**Acceptance Criteria**:
- [ ] All 5 endpoints implemented
- [ ] Lifespan manager for startup/shutdown
- [ ] Prometheus metrics (3+ metrics)
- [ ] Structured logging for all requests
- [ ] Error responses with proper status codes
- [ ] CORS middleware configured

### 4.2 Add API Endpoint Tests

**File**: `tests/test_main.py`

**Test cases**:
- POST /plan success (200)
- POST /plan with invalid input (422)
- POST /plan with LLM failure (500)
- GET /health (200)
- GET /ready (200)
- GET /metrics (200)
- GET /capabilities (200)

**Acceptance Criteria**:
- [ ] 15+ API endpoint tests
- [ ] Test client fixture in conftest.py
- [ ] Mocked planner for deterministic tests
- [ ] Error case coverage

### 4.3 Add Configuration Tests

**File**: `tests/test_config.py`

**Test cases**:
- Settings load from env vars
- Default values
- Validation errors (invalid model, missing API key)
- Singleton pattern

**Acceptance Criteria**:
- [ ] 10+ configuration tests
- [ ] Environment variable override testing
- [ ] Validation testing

---

## Phase 5: Integration Testing

### 5.1 Create Integration Test Suite

**File**: `tests/test_integration.py`

**Test scenarios** (with real OpenAI API or mock):
1. Simple task: "Write a Python function to sort a list"
2. Complex task: "Build and deploy a REST API with tests"
3. Multi-dependency task: "Debug authentication issue and add tests"
4. High constraint task: "Complete in <2 minutes, use Python only"

**Validation checks**:
- Plan has 3-7 steps
- Dependencies are valid (no forward refs)
- Arms are correctly assigned
- Acceptance criteria exist for each step
- Confidence > 0.6

**Acceptance Criteria**:
- [ ] 10+ integration test cases
- [ ] Diverse task scenarios
- [ ] Real LLM calls (with pytest mark for slow tests)
- [ ] Mock LLM option for CI/CD

### 5.2 Create Pytest Configuration

**File**: `tests/conftest.py`

**Fixtures**:
```python
@pytest.fixture
def planner():
    """PlannerArm instance with test settings."""

@pytest.fixture
def test_client():
    """FastAPI test client."""

@pytest.fixture
def mock_openai():
    """Mock OpenAI API responses."""
```

**Acceptance Criteria**:
- [ ] All fixtures defined
- [ ] Shared test utilities
- [ ] Mock data generators

---

## Phase 6: Orchestrator Integration

### 6.1 Add Planner Client to Orchestrator

**File**: `services/orchestrator/app/planner_client.py` (NEW)

**Purpose**: HTTP client for calling Planner Arm from Orchestrator

**Features**:
- Async HTTP calls with httpx
- Retry logic with tenacity
- Circuit breaker pattern (like reflex_client.py)
- Structured logging
- Prometheus metrics

**Methods**:
```python
class PlannerClient:
    async def create_plan(
        task_id: str,
        goal: str,
        constraints: List[str],
        context: Dict[str, Any]
    ) -> PlanResponse:
        """Call Planner Arm to generate plan."""
```

**Acceptance Criteria**:
- [ ] PlannerClient class implemented
- [ ] Circuit breaker pattern
- [ ] Retry logic (3 attempts)
- [ ] Error handling
- [ ] Unit tests for client

### 6.2 Update Orchestrator Configuration

**File**: `services/orchestrator/app/config.py`

**Add settings**:
```python
# Planner Arm Configuration
planner_arm_url: str = Field(
    default="http://planner-arm:8001",
    description="Planner Arm service URL",
)
planner_arm_timeout: float = Field(
    default=10.0, ge=1.0, le=60.0, description="Request timeout"
)
planner_arm_max_retries: int = Field(
    default=3, ge=1, le=10, description="Max retry attempts"
)
```

**Acceptance Criteria**:
- [ ] Planner Arm settings added
- [ ] Validation for URL format

### 6.3 Add Planner Integration to Orchestrator

**File**: `services/orchestrator/app/main.py`

**Update**: Add planning step to task processing

**Logic**:
```python
# After task submission
if task.assigned_arm is None:
    # Call Planner Arm to decompose task
    plan = await planner_client.create_plan(...)
    # Store plan in database
    # Update task with subtasks
```

**Acceptance Criteria**:
- [ ] Planner Arm called during task processing
- [ ] Plan stored in database
- [ ] Integration tests pass

### 6.4 Update Docker Compose

**File**: `infrastructure/docker-compose/docker-compose.dev.yml`

**Add Planner Arm service**:
```yaml
planner-arm:
  build:
    context: ../..
    dockerfile: services/arms/planner/Dockerfile
  container_name: planner-arm
  ports:
    - "8001:8001"
  environment:
    - PLANNER_OPENAI_API_KEY=${OPENAI_API_KEY}
    - PLANNER_LLM_MODEL=gpt-3.5-turbo
    - PLANNER_ENVIRONMENT=development
  depends_on:
    - orchestrator
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
    interval: 10s
    timeout: 3s
    retries: 3
```

**Update**: Add OPENAI_API_KEY to `.env.example`

**Acceptance Criteria**:
- [ ] Planner Arm service in docker-compose.yml
- [ ] Health check configured
- [ ] Environment variables set
- [ ] Service starts successfully

---

## Phase 7: Testing & Quality Assurance

### 7.1 Run Full Test Suite

**Commands**:
```bash
cd services/arms/planner
pytest tests/ -v --cov=src --cov-report=term-missing
```

**Acceptance Criteria**:
- [ ] All tests pass (100%)
- [ ] Coverage ≥ 85%
- [ ] No skipped tests
- [ ] Test execution < 30 seconds

### 7.2 Run Linters

**Commands**:
```bash
# Format check
black --check src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

**Acceptance Criteria**:
- [ ] Black formatting passes
- [ ] Ruff linting passes (0 errors)
- [ ] Mypy type checking passes (0 errors)

### 7.3 Fix All Issues

**Acceptance Criteria**:
- [ ] All linting issues resolved
- [ ] All type errors fixed
- [ ] Code formatted with black

### 7.4 End-to-End Testing

**Test scenario**:
1. Start docker-compose stack
2. Submit task to Orchestrator: `POST /submit`
3. Verify Orchestrator calls Planner Arm
4. Verify plan is generated and returned
5. Check logs for errors

**Commands**:
```bash
docker-compose -f infrastructure/docker-compose/docker-compose.dev.yml up -d
curl -X POST http://localhost:8000/submit -H "Content-Type: application/json" -d '{"goal": "Write a function to calculate fibonacci"}'
docker-compose logs planner-arm
```

**Acceptance Criteria**:
- [ ] All services healthy
- [ ] Orchestrator → Planner Arm communication works
- [ ] Plan generated successfully
- [ ] No errors in logs

---

## Phase 8: Documentation

### 8.1 Update Service README

**File**: `services/arms/planner/README.md`

**Sections**:
- Overview
- Architecture
- API Endpoints
- Configuration
- Development
- Testing
- Deployment
- Troubleshooting

**Acceptance Criteria**:
- [ ] Comprehensive README (500+ lines)
- [ ] Code examples for all endpoints
- [ ] Environment variable documentation
- [ ] Testing instructions

### 8.2 Create Sprint Completion Report

**File**: `docs/sprint-reports/SPRINT-1.3-COMPLETION.md`

**Sections**:
- Executive Summary
- Objectives Met
- Deliverables
- Architecture Decisions
- Code Statistics
- Test Results
- Integration Status
- Lessons Learned
- Next Steps

**Metrics to include**:
- Lines of code (production + tests)
- Test coverage percentage
- Number of endpoints
- Number of tests
- Linter results

**Acceptance Criteria**:
- [ ] Completion report created
- [ ] All metrics documented
- [ ] Screenshots/examples included

### 8.3 Update MASTER-TODO

**File**: `to-dos/MASTER-TODO.md`

**Updates**:
- Mark Sprint 1.3 as COMPLETE
- Update Phase 1 progress percentage
- Add completion timestamp
- Update "Latest Update" section

**Acceptance Criteria**:
- [ ] Sprint 1.3 marked complete
- [ ] Progress updated
- [ ] Timestamps accurate

### 8.4 Update CHANGELOG

**File**: `CHANGELOG.md`

**Add version 0.2.0 entry**:
```markdown
## [0.2.0] - 2025-11-18

### Added
- Planner Arm service with task decomposition capability
- OpenAI GPT-3.5-turbo integration for planning
- Dependency resolution and validation
- Planner client in Orchestrator
- 50+ unit and integration tests
- Prometheus metrics for planning operations

### Changed
- Orchestrator now uses Planner Arm for task decomposition
- Docker Compose includes planner-arm service
```

**Acceptance Criteria**:
- [ ] CHANGELOG.md updated
- [ ] Version number correct
- [ ] All changes documented

---

## Phase 9: Git Commit & Push

### 9.1 Review All Changes

**Commands**:
```bash
git status
git diff --stat
```

**Acceptance Criteria**:
- [ ] All new files staged
- [ ] No unintended changes
- [ ] No secrets in code
- [ ] .gitignore updated if needed

### 9.2 Create Commit

**Commit message**:
```
feat(planner-arm): Implement Sprint 1.3 - Planner Arm with task decomposition

Sprint 1.3 Implementation Summary:
- Planner Arm service with FastAPI (500+ lines Python)
- OpenAI GPT-3.5-turbo integration for intelligent planning
- Dependency resolution and validation logic
- 5 REST endpoints (/plan, /health, /ready, /metrics, /capabilities)
- Comprehensive test suite (50+ tests, 85%+ coverage)
- Planner client in Orchestrator with circuit breaker
- Docker Compose integration

Key Features:
- Generates 3-7 step execution plans with acceptance criteria
- Validates dependencies (no forward/circular refs)
- Cost-aware arm selection
- Retry logic with exponential backoff
- Prometheus metrics and structured logging

Integration:
- Orchestrator → Planner Arm communication working
- Docker Compose deployment functional
- All services healthy in dev environment

Testing:
- 50+ unit and integration tests (all passing)
- 85%+ code coverage
- Linters pass (black, ruff, mypy)
- E2E tests with real LLM calls

Documentation:
- Service README (500+ lines)
- Sprint completion report
- API documentation
- Updated MASTER-TODO and CHANGELOG

Phase 1 Progress: 33% → 45% (3/9 sprints complete)
Next: Sprint 1.4 (Executor Arm)

Co-authored-by: Claude <assistant@anthropic.com>
```

**Acceptance Criteria**:
- [ ] Commit message follows conventional commits
- [ ] All changes committed
- [ ] Commit hash recorded

### 9.3 Push to Remote

**Commands**:
```bash
git push origin claude/review-project-status-01ADAPcnx59Q7WsFGvARVt52
```

**Acceptance Criteria**:
- [ ] Changes pushed successfully
- [ ] Branch visible on remote
- [ ] No merge conflicts

---

## Success Metrics

### Code Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Lines of Code (src/) | 500+ | TBD |
| Lines of Tests | 600+ | TBD |
| Test Coverage | ≥85% | TBD |
| Number of Tests | 50+ | TBD |
| Linter Errors | 0 | TBD |
| Type Errors | 0 | TBD |

### Functional Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Plan Success Rate | ≥90% | TBD |
| Valid Dependencies | 100% | TBD |
| Average Plan Steps | 4-6 | TBD |
| P95 Latency | <3s | TBD |
| Uptime | 99%+ | TBD |

### Integration Metrics

| Metric | Target | Actual |
|--------|--------|--------|
| Orchestrator Integration | ✓ | TBD |
| Docker Compose Deploy | ✓ | TBD |
| E2E Tests Passing | ✓ | TBD |
| CI/CD Passing | ✓ | TBD |

---

## Risk Assessment

### High Priority Risks

1. **OpenAI API Key Management**
   - Risk: API key exposure in logs/commits
   - Mitigation: Use environment variables, gitignore .env files, audit commits

2. **LLM Response Quality**
   - Risk: Plans with invalid JSON or poor quality
   - Mitigation: Structured output mode, retry logic, validation

3. **Cost Overruns**
   - Risk: Excessive OpenAI API calls
   - Mitigation: Use GPT-3.5-turbo (cheap), implement caching, rate limiting

### Medium Priority Risks

4. **Integration Complexity**
   - Risk: Orchestrator → Planner Arm communication failures
   - Mitigation: Circuit breaker, retry logic, comprehensive tests

5. **Test Coverage**
   - Risk: Missing edge cases in tests
   - Mitigation: Review coverage report, add tests for uncovered paths

---

## References

- [Planner Arm Specification](/home/user/OctoLLM/docs/components/arms/planner-arm.md)
- [Orchestrator Code](/home/user/OctoLLM/services/orchestrator/app/)
- [MASTER-TODO](/home/user/OctoLLM/to-dos/MASTER-TODO.md)
- [OpenAPI Spec](/home/user/OctoLLM/docs/api/openapi/planner.yaml)

---

**Last Updated**: 2025-11-18
**Document Version**: 1.0
