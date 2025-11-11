# Orchestrator Implementation Guide

**Document**: Implementation Guide
**Version**: 1.0
**Last Updated**: 2025-11-10
**Estimated Time**: 2-3 hours

[← Back to Documentation](../README.md) | [Implementation Guides](./README.md)

---

## Table of Contents

1. [Overview](#overview)
   - [What You'll Build](#what-youll-build)
   - [Prerequisites](#prerequisites)
   - [Architecture Recap](#architecture-recap)
2. [Project Setup](#project-setup)
   - [Directory Structure](#directory-structure)
   - [Dependencies](#dependencies)
   - [Configuration](#configuration)
3. [Core Components](#core-components)
   - [Intent Parser](#intent-parser)
   - [Task Planner](#task-planner)
   - [Arm Router](#arm-router)
   - [Result Integrator](#result-integrator)
   - [State Manager](#state-manager)
4. [API Implementation](#api-implementation)
   - [FastAPI Setup](#fastapi-setup)
   - [Task Endpoints](#task-endpoints)
   - [Health and Metrics](#health-and-metrics)
5. [Arm Registry](#arm-registry)
   - [Registry Data Model](#registry-data-model)
   - [Discovery Mechanism](#discovery-mechanism)
   - [Health Checking](#health-checking)
6. [Execution Engine](#execution-engine)
   - [Workflow Execution](#workflow-execution)
   - [Dependency Resolution](#dependency-resolution)
   - [Error Handling](#error-handling)
7. [Memory Integration](#memory-integration)
   - [Global Memory Access](#global-memory-access)
   - [Cache Layer](#cache-layer)
   - [Context Management](#context-management)
8. [Testing](#testing)
   - [Unit Tests](#unit-tests)
   - [Integration Tests](#integration-tests)
   - [End-to-End Tests](#end-to-end-tests)
9. [Deployment](#deployment)
   - [Docker Build](#docker-build)
   - [Kubernetes Deployment](#kubernetes-deployment)
   - [Production Checklist](#production-checklist)

---

## Overview

The Orchestrator is the central "brain" of OctoLLM, responsible for strategic planning, task decomposition, arm coordination, and result integration. This guide walks you through building a production-ready orchestrator from scratch.

### What You'll Build

By the end of this guide, you'll have a fully functional orchestrator that:

- Accepts tasks via REST API
- Parses user intent and extracts goals
- Decomposes complex tasks into subtasks
- Routes subtasks to appropriate arms
- Integrates results from multiple arms
- Handles failures with retry logic
- Persists execution history
- Exposes metrics and health checks

```mermaid
graph TD
    subgraph "Orchestrator Components"
        API[FastAPI Server]
        PARSE[Intent Parser]
        PLAN[Task Planner]
        ROUTE[Arm Router]
        EXEC[Execution Engine]
        INTEG[Result Integrator]
        STATE[State Manager]
    end

    CLIENT[Client] -->|POST /tasks| API
    API --> PARSE
    PARSE --> PLAN
    PLAN --> ROUTE
    ROUTE --> EXEC
    EXEC --> INTEG
    INTEG --> STATE
    STATE -->|Response| CLIENT
```

### Prerequisites

Before starting, ensure you have:

- Python 3.11+ installed
- Poetry for dependency management
- Docker and Docker Compose
- PostgreSQL, Redis, and Qdrant running (see [dev-environment.md](./dev-environment.md))
- Basic understanding of FastAPI and async Python
- Familiarity with OctoLLM architecture (see [system-overview.md](../architecture/system-overview.md))

### Architecture Recap

The Orchestrator operates as a stateless service:

```mermaid
stateDiagram-v2
    [*] --> Idle
    Idle --> Parsing: Request
    Parsing --> Planning: Intent
    Planning --> Routing: Plan
    Routing --> Executing: Arms
    Executing --> Integrating: Results
    Integrating --> Validating: Combined
    Validating --> Caching: Valid
    Caching --> Idle: Response
    Validating --> Repairing: Invalid
    Repairing --> Integrating: Retry
```

---

## Project Setup

### Directory Structure

Create the following structure for the orchestrator:

```bash
orchestrator/
├── pyproject.toml           # Poetry dependencies
├── README.md                # Project README
├── .env.example             # Environment template
├── Dockerfile               # Container image
├── docker-compose.yml       # Local development
├── orchestrator/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Configuration management
│   ├── models.py            # Pydantic models
│   ├── api/
│   │   ├── __init__.py
│   │   ├── tasks.py         # Task endpoints
│   │   └── health.py        # Health/metrics endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── intent_parser.py
│   │   ├── task_planner.py
│   │   ├── arm_router.py
│   │   ├── result_integrator.py
│   │   └── state_manager.py
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── engine.py        # Workflow execution
│   │   └── workflow.py      # Workflow definitions
│   ├── registry/
│   │   ├── __init__.py
│   │   ├── arm_registry.py  # Arm discovery and management
│   │   └── health_checker.py
│   └── memory/
│       ├── __init__.py
│       ├── global_memory.py # PostgreSQL client
│       ├── cache.py         # Redis client
│       └── context.py       # Context management
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest fixtures
│   ├── unit/
│   │   ├── test_intent_parser.py
│   │   ├── test_task_planner.py
│   │   └── test_arm_router.py
│   ├── integration/
│   │   ├── test_workflow.py
│   │   └── test_api.py
│   └── e2e/
│       └── test_complete_flow.py
└── k8s/
    ├── deployment.yaml
    ├── service.yaml
    └── configmap.yaml
```

**Create the directory structure**:

```bash
mkdir -p orchestrator/{orchestrator/{api,core,execution,registry,memory},tests/{unit,integration,e2e},k8s}
cd orchestrator
touch orchestrator/__init__.py orchestrator/{api,core,execution,registry,memory}/__init__.py
```

### Dependencies

**File**: `orchestrator/pyproject.toml`

```toml
[tool.poetry]
name = "octollm-orchestrator"
version = "1.0.0"
description = "OctoLLM Central Orchestrator"
authors = ["OctoLLM Team <team@octollm.io>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.104.1"
uvicorn = {extras = ["standard"], version = "^0.24.0"}
pydantic = "^2.5.0"
pydantic-settings = "^2.1.0"
httpx = "^0.25.2"
asyncpg = "^0.29.0"
redis = {extras = ["hiredis"], version = "^5.0.1"}
qdrant-client = "^1.7.0"
structlog = "^23.2.0"
tenacity = "^8.2.3"
openai = "^1.3.7"
prometheus-client = "^0.19.0"

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.3"
pytest-asyncio = "^0.21.1"
pytest-cov = "^4.1.0"
httpx-mock = "^0.11.0"
faker = "^20.1.0"
black = "^23.12.0"
ruff = "^0.1.8"
mypy = "^1.7.1"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
target-version = "py311"
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
```

**Install dependencies**:

```bash
poetry install
poetry shell
```

### Configuration

**File**: `orchestrator/orchestrator/config.py`

```python
"""Configuration management for orchestrator."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl
from typing import Optional


class Settings(BaseSettings):
    """Orchestrator configuration.

    All settings can be overridden via environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    api_workers: int = Field(default=4, description="Number of workers")

    # LLM Configuration
    openai_api_key: str = Field(..., description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model")
    openai_temperature: float = Field(default=0.7, ge=0.0, le=2.0)

    # Database Configuration
    postgres_url: str = Field(
        default="postgresql://postgres:password@localhost:5432/octollm",
        description="PostgreSQL connection URL"
    )
    redis_url: str = Field(
        default="redis://localhost:6379/0",
        description="Redis connection URL"
    )
    qdrant_url: HttpUrl = Field(
        default="http://localhost:6333",
        description="Qdrant server URL"
    )

    # Arm Registry
    arm_registry_path: str = Field(
        default="/config/arm_registry.json",
        description="Path to arm registry config"
    )

    # Execution Configuration
    max_concurrent_tasks: int = Field(default=10, ge=1, le=100)
    max_retries: int = Field(default=3, ge=0, le=10)
    task_timeout_seconds: int = Field(default=300, ge=10, le=3600)

    # Cache Configuration
    cache_ttl_seconds: int = Field(default=300, ge=10)

    # Logging
    log_level: str = Field(default="INFO", description="Log level")
    log_format: str = Field(default="json", description="Log format (json or console)")

    # Observability
    enable_metrics: bool = Field(default=True)
    metrics_port: int = Field(default=9090)


# Global settings instance
settings = Settings()
```

**File**: `.env.example`

```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4

# LLM Configuration
OPENAI_API_KEY=your-api-key-here
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7

# Database Configuration
POSTGRES_URL=postgresql://postgres:password@localhost:5432/octollm
REDIS_URL=redis://localhost:6379/0
QDRANT_URL=http://localhost:6333

# Arm Registry
ARM_REGISTRY_PATH=/config/arm_registry.json

# Execution Configuration
MAX_CONCURRENT_TASKS=10
MAX_RETRIES=3
TASK_TIMEOUT_SECONDS=300

# Cache Configuration
CACHE_TTL_SECONDS=300

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Observability
ENABLE_METRICS=true
METRICS_PORT=9090
```

---

## Core Components

### Intent Parser

The Intent Parser extracts structured information from user requests.

**File**: `orchestrator/orchestrator/core/intent_parser.py`

```python
"""Intent parser for extracting goals and constraints."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel
import structlog
import openai

logger = structlog.get_logger()


class ParsedIntent(BaseModel):
    """Structured intent extracted from user request."""
    goal: str
    constraints: List[str]
    domain: str  # e.g., "code", "security", "data"
    complexity: str  # "simple", "medium", "complex"
    keywords: List[str]
    entities: Dict[str, Any]


class IntentParser:
    """
    Parse natural language requests into structured intents.

    Uses LLM to extract:
    - Main goal
    - Constraints and requirements
    - Domain classification
    - Complexity estimation
    - Key entities
    """

    def __init__(self, openai_api_key: str, model: str = "gpt-3.5-turbo"):
        self.client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.model = model

    async def parse(self, user_request: str) -> ParsedIntent:
        """
        Parse user request into structured intent.

        Args:
            user_request: Natural language request

        Returns:
            ParsedIntent with extracted information
        """
        logger.info("intent_parser.start", request_length=len(user_request))

        # Construct prompt for LLM
        prompt = self._build_parsing_prompt(user_request)

        # Call LLM
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]}
            ],
            temperature=0.3,  # Low temperature for consistent parsing
            response_format={"type": "json_object"}
        )

        # Parse LLM response
        parsed = response.choices[0].message.content
        intent_data = json.loads(parsed)

        intent = ParsedIntent(**intent_data)

        logger.info(
            "intent_parser.complete",
            domain=intent.domain,
            complexity=intent.complexity,
            constraints_count=len(intent.constraints)
        )

        return intent

    def _build_parsing_prompt(self, user_request: str) -> Dict[str, str]:
        """Build prompt for intent parsing."""
        return {
            "system": """You are an intent parser for a distributed AI system.
Extract structured information from user requests.

Return JSON with this exact structure:
{
  "goal": "clear, concise goal statement",
  "constraints": ["constraint 1", "constraint 2"],
  "domain": "code|security|data|infrastructure|general",
  "complexity": "simple|medium|complex",
  "keywords": ["keyword1", "keyword2"],
  "entities": {
    "files": ["file1.py"],
    "functions": ["function_name"],
    "technologies": ["Python", "FastAPI"]
  }
}

Guidelines:
- goal: Single sentence describing what user wants
- constraints: Hard requirements (time, cost, safety)
- domain: Primary domain of the task
- complexity: simple (1-2 steps), medium (3-5 steps), complex (6+ steps)
- keywords: Important terms for context retrieval
- entities: Structured entities mentioned in request""",
            "user": user_request
        }


# Example usage
async def example_parse_intent():
    """Example: Parse user request."""
    parser = IntentParser(openai_api_key="your-key")

    intent = await parser.parse(
        "Find and fix the authentication bug in auth/login.py. "
        "Don't modify the database schema and complete within 5 minutes."
    )

    print(f"Goal: {intent.goal}")
    print(f"Domain: {intent.domain}")
    print(f"Complexity: {intent.complexity}")
    print(f"Constraints: {intent.constraints}")
```

### Task Planner

The Task Planner decomposes complex tasks into executable subtasks.

**File**: `orchestrator/orchestrator/core/task_planner.py`

```python
"""Task planner for decomposing complex tasks."""

from typing import List, Optional
from pydantic import BaseModel
from dataclasses import dataclass
import structlog
import openai

logger = structlog.get_logger()


@dataclass
class SubTask:
    """Single subtask in execution plan."""
    step_id: str
    description: str
    arm_type: str  # Which arm should execute this
    input_data: dict
    dependencies: List[str]  # Step IDs this depends on
    acceptance_criteria: List[str]


class ExecutionPlan(BaseModel):
    """Complete execution plan for a task."""
    plan_id: str
    subtasks: List[SubTask]
    estimated_duration_seconds: int
    estimated_cost_tokens: int


class TaskPlanner:
    """
    Decompose complex tasks into executable subtasks.

    Uses LLM to generate execution plans with:
    - Step-by-step breakdown
    - Arm assignments
    - Dependency graph
    - Acceptance criteria
    """

    def __init__(
        self,
        openai_api_key: str,
        model: str = "gpt-4",
        arm_capabilities: dict = None
    ):
        self.client = openai.AsyncOpenAI(api_key=openai_api_key)
        self.model = model
        self.arm_capabilities = arm_capabilities or self._default_capabilities()

    async def plan(
        self,
        goal: str,
        constraints: List[str],
        context: dict
    ) -> ExecutionPlan:
        """
        Generate execution plan for goal.

        Args:
            goal: Task goal
            constraints: Task constraints
            context: Additional context

        Returns:
            ExecutionPlan with subtasks
        """
        logger.info("task_planner.start", goal=goal)

        # Build planning prompt
        prompt = self._build_planning_prompt(goal, constraints, context)

        # Call LLM
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": prompt["system"]},
                {"role": "user", "content": prompt["user"]}
            ],
            temperature=0.7,
            response_format={"type": "json_object"}
        )

        # Parse plan
        plan_data = json.loads(response.choices[0].message.content)

        # Convert to ExecutionPlan
        subtasks = [
            SubTask(
                step_id=step["step_id"],
                description=step["description"],
                arm_type=step["arm_type"],
                input_data=step.get("input_data", {}),
                dependencies=step.get("dependencies", []),
                acceptance_criteria=step.get("acceptance_criteria", [])
            )
            for step in plan_data["subtasks"]
        ]

        plan = ExecutionPlan(
            plan_id=f"plan-{uuid.uuid4()}",
            subtasks=subtasks,
            estimated_duration_seconds=plan_data.get("estimated_duration_seconds", 60),
            estimated_cost_tokens=plan_data.get("estimated_cost_tokens", 1000)
        )

        logger.info(
            "task_planner.complete",
            plan_id=plan.plan_id,
            subtasks_count=len(subtasks)
        )

        return plan

    def _build_planning_prompt(
        self,
        goal: str,
        constraints: List[str],
        context: dict
    ) -> Dict[str, str]:
        """Build prompt for task planning."""

        arm_descriptions = "\n".join([
            f"- {name}: {info['description']}"
            for name, info in self.arm_capabilities.items()
        ])

        return {
            "system": f"""You are a task planner for a distributed AI system.
Decompose complex tasks into executable subtasks.

Available arms:
{arm_descriptions}

Return JSON with this structure:
{{
  "subtasks": [
    {{
      "step_id": "step_1",
      "description": "What to do in this step",
      "arm_type": "planner|retriever|coder|executor|judge",
      "input_data": {{}},
      "dependencies": ["step_id_1"],
      "acceptance_criteria": ["criteria 1"]
    }}
  ],
  "estimated_duration_seconds": 120,
  "estimated_cost_tokens": 5000
}}

Guidelines:
- Break down into 3-7 steps
- Assign appropriate arm to each step
- Define clear dependencies
- Include acceptance criteria
- Consider constraints""",
            "user": f"""Goal: {goal}

Constraints:
{chr(10).join(f"- {c}" for c in constraints)}

Context:
{json.dumps(context, indent=2)}"""
        }

    def _default_capabilities(self) -> dict:
        """Default arm capabilities."""
        return {
            "planner": {
                "description": "Decompose tasks into subtasks"
            },
            "retriever": {
                "description": "Search and retrieve information"
            },
            "coder": {
                "description": "Generate, analyze, and refactor code"
            },
            "executor": {
                "description": "Execute commands and scripts in sandbox"
            },
            "judge": {
                "description": "Validate results and check quality"
            }
        }
```

### Arm Router

The Arm Router selects the best arm for each subtask.

**File**: `orchestrator/orchestrator/core/arm_router.py`

```python
"""Arm router for selecting optimal arm for each task."""

from typing import Optional, List
from dataclasses import dataclass
import structlog
import random

logger = structlog.get_logger()


@dataclass
class ArmScore:
    """Scoring for arm selection."""
    arm_id: str
    capability_match: float  # 0.0-1.0
    availability: float      # 0.0-1.0
    historical_success: float  # 0.0-1.0
    cost_efficiency: float   # 0.0-1.0
    total_score: float


class ArmRouter:
    """
    Route tasks to appropriate arms based on:
    - Capability matching
    - Arm availability
    - Historical success rates
    - Cost efficiency
    """

    def __init__(self, arm_registry: dict):
        self.arm_registry = arm_registry
        self.historical_stats = {}  # Track arm performance

    async def route(
        self,
        task_type: str,
        required_capabilities: List[str],
        priority: str = "medium"
    ) -> Optional[str]:
        """
        Select best arm for task.

        Args:
            task_type: Type of task (e.g., "coder", "executor")
            required_capabilities: Required capabilities
            priority: Task priority

        Returns:
            Selected arm ID or None if no suitable arm
        """
        logger.info(
            "arm_router.route",
            task_type=task_type,
            capabilities=required_capabilities
        )

        # Get candidate arms
        candidates = self._get_candidates(task_type)

        if not candidates:
            logger.warning("arm_router.no_candidates", task_type=task_type)
            return None

        # Score each candidate
        scores = [
            self._score_arm(arm_id, required_capabilities, priority)
            for arm_id in candidates
        ]

        # Sort by total score
        scores.sort(key=lambda s: s.total_score, reverse=True)

        selected = scores[0]

        logger.info(
            "arm_router.selected",
            arm_id=selected.arm_id,
            score=selected.total_score
        )

        return selected.arm_id

    def _get_candidates(self, task_type: str) -> List[str]:
        """Get candidate arms for task type."""
        return [
            arm_id
            for arm_id, arm_info in self.arm_registry.items()
            if arm_info.get("arm_type") == task_type
        ]

    def _score_arm(
        self,
        arm_id: str,
        required_capabilities: List[str],
        priority: str
    ) -> ArmScore:
        """
        Score arm for task.

        Scoring factors:
        - Capability match (40%)
        - Availability (20%)
        - Historical success (30%)
        - Cost efficiency (10%)
        """
        arm_info = self.arm_registry[arm_id]

        # Capability matching
        arm_capabilities = set(arm_info.get("capabilities", []))
        required_set = set(required_capabilities)
        capability_match = (
            len(arm_capabilities & required_set) / len(required_set)
            if required_set else 1.0
        )

        # Availability (simple health check for now)
        availability = 1.0 if arm_info.get("status") == "healthy" else 0.0

        # Historical success rate
        stats = self.historical_stats.get(arm_id, {"success": 10, "total": 10})
        historical_success = stats["success"] / stats["total"]

        # Cost efficiency (inverse of cost tier)
        cost_tier = arm_info.get("cost_tier", 3)
        cost_efficiency = 1.0 - (cost_tier / 5.0)

        # Weighted total
        total_score = (
            capability_match * 0.4 +
            availability * 0.2 +
            historical_success * 0.3 +
            cost_efficiency * 0.1
        )

        return ArmScore(
            arm_id=arm_id,
            capability_match=capability_match,
            availability=availability,
            historical_success=historical_success,
            cost_efficiency=cost_efficiency,
            total_score=total_score
        )

    def update_stats(self, arm_id: str, success: bool):
        """Update historical statistics for arm."""
        if arm_id not in self.historical_stats:
            self.historical_stats[arm_id] = {"success": 0, "total": 0}

        stats = self.historical_stats[arm_id]
        stats["total"] += 1
        if success:
            stats["success"] += 1

        logger.debug(
            "arm_router.stats_updated",
            arm_id=arm_id,
            success_rate=stats["success"] / stats["total"]
        )
```

---

## API Implementation

### FastAPI Setup

**File**: `orchestrator/orchestrator/main.py`

```python
"""Main FastAPI application for orchestrator."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import structlog
from contextlib import asynccontextmanager

from orchestrator.config import settings
from orchestrator.api import tasks, health

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer() if settings.log_format == "json"
        else structlog.dev.ConsoleRenderer()
    ]
)

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    # Startup
    logger.info("orchestrator.startup", version="1.0.0")

    # Initialize connections
    await initialize_connections()

    yield

    # Shutdown
    logger.info("orchestrator.shutdown")
    await cleanup_connections()


# Create FastAPI app
app = FastAPI(
    title="OctoLLM Orchestrator",
    description="Central orchestrator for distributed AI system",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Include routers
app.include_router(tasks.router, prefix="/api/v1", tags=["tasks"])
app.include_router(health.router, tags=["health"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "octollm-orchestrator",
        "version": "1.0.0",
        "status": "operational"
    }


async def initialize_connections():
    """Initialize database and cache connections."""
    # Initialize PostgreSQL pool
    # Initialize Redis connection
    # Initialize Qdrant client
    logger.info("orchestrator.connections.initialized")


async def cleanup_connections():
    """Clean up connections on shutdown."""
    logger.info("orchestrator.connections.cleanup")
```

### Task Endpoints

**File**: `orchestrator/orchestrator/api/tasks.py`

```python
"""Task management endpoints."""

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from uuid import uuid4
import structlog

logger = structlog.get_logger()

router = APIRouter()


class TaskRequest(BaseModel):
    """Task submission request."""
    goal: str = Field(..., min_length=10, max_length=2000)
    constraints: List[str] = Field(default_factory=list, max_items=20)
    context: Dict[str, Any] = Field(default_factory=dict)
    priority: str = Field(default="medium")
    budget: Dict[str, int] = Field(
        default_factory=lambda: {
            "max_tokens": 4000,
            "max_time_seconds": 60
        }
    )


class TaskResponse(BaseModel):
    """Task submission response."""
    task_id: str
    status: str
    estimated_duration_seconds: int
    created_at: str


@router.post("/tasks", response_model=TaskResponse, status_code=202)
async def submit_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """
    Submit new task for execution.

    Returns immediately with task ID. Task executes asynchronously.
    """
    task_id = f"task-{uuid4()}"

    logger.info(
        "task.submitted",
        task_id=task_id,
        goal=request.goal[:100],
        priority=request.priority
    )

    # Queue task for background execution
    background_tasks.add_task(
        execute_task_async,
        task_id=task_id,
        request=request
    )

    return TaskResponse(
        task_id=task_id,
        status="accepted",
        estimated_duration_seconds=60,
        created_at=datetime.utcnow().isoformat()
    )


@router.get("/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status and results."""
    # Query from state manager
    task_state = await get_task_from_db(task_id)

    if not task_state:
        raise HTTPException(status_code=404, detail="Task not found")

    return task_state


@router.post("/tasks/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel running task."""
    logger.info("task.cancel", task_id=task_id)

    # Implement cancellation logic
    await cancel_task_execution(task_id)

    return {"task_id": task_id, "status": "cancelled"}


async def execute_task_async(task_id: str, request: TaskRequest):
    """Execute task asynchronously (background task)."""
    try:
        # This would call the execution engine
        result = await execute_task(task_id, request)

        logger.info("task.complete", task_id=task_id)

    except Exception as e:
        logger.error("task.failed", task_id=task_id, error=str(e))
```

---

## Summary

This guide provides a foundation for building the OctoLLM Orchestrator. Key takeaways:

1. **Modular Design**: Separate components for parsing, planning, routing, and execution
2. **Async-First**: Use async/await throughout for performance
3. **Structured Logging**: Use structlog for observability
4. **Error Handling**: Implement retries and fallbacks
5. **Testing**: Write comprehensive tests at all levels

### Next Steps

- Complete the execution engine implementation
- Add memory integration
- Implement comprehensive testing
- Set up monitoring and metrics
- Deploy with Kubernetes

For more details, see:
- [Integration Patterns](./integration-patterns.md) - Connect components
- [Custom Arms Guide](./custom-arms.md) - Build specialized arms
- [Testing Guide](./testing-guide.md) - Test your orchestrator
- [Deployment Guide](../operations/deployment-guide.md) - Deploy to production

---

**Document Maintainers**: OctoLLM Core Team
**Last Updated**: 2025-11-10
**Next Review**: 2025-12-10
