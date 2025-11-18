"""
OctoLLM Planner Arm Service - Main FastAPI Application

The task decomposition specialist responsible for breaking complex goals into
sequential subtasks with clear acceptance criteria and dependencies.

Endpoints:
- POST /plan - Generate execution plan from goal
- GET /health - Health check (Kubernetes liveness)
- GET /ready - Readiness check (Kubernetes readiness)
- GET /metrics - Prometheus metrics
- GET /capabilities - Arm capabilities information

Usage:
    uvicorn src.main:app --reload --port 8001
"""

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime

import structlog
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from src.config import get_settings
from src.models import (
    CapabilitiesResponse,
    HealthResponse,
    PlanRequest,
    PlanResponse,
    ReadinessResponse,
)
from src.planner import InvalidDependencyError, LLMError, PlannerArm, PlanningError

logger = structlog.get_logger(__name__)

# ==============================================================================
# Prometheus Metrics
# ==============================================================================

PLAN_REQUEST_COUNTER = Counter(
    "planner_arm_requests_total",
    "Total number of plan requests",
)

PLAN_SUCCESS_COUNTER = Counter(
    "planner_arm_success_total",
    "Total number of successful plan generations",
)

PLAN_ERROR_COUNTER = Counter(
    "planner_arm_errors_total",
    "Total number of plan generation errors",
    ["error_type"],
)

PLAN_DURATION_HISTOGRAM = Histogram(
    "planner_arm_duration_seconds",
    "Plan generation duration in seconds",
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

HTTP_REQUEST_DURATION = Histogram(
    "planner_arm_http_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

# ==============================================================================
# Application Lifecycle
# ==============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """
    Application lifespan manager.

    Handles startup and shutdown events.
    """
    settings = get_settings()

    # Startup
    logger.info(
        "planner_arm.startup",
        service=settings.service_name,
        version=settings.version,
        environment=settings.environment,
        model=settings.llm_model,
    )

    # Initialize planner
    planner = PlannerArm(settings)
    app.state.planner = planner

    logger.info("planner_arm.startup.complete")

    yield

    # Shutdown
    logger.info("planner_arm.shutdown")


# ==============================================================================
# FastAPI Application
# ==============================================================================

app = FastAPI(
    title="OctoLLM Planner Arm",
    description="Task decomposition specialist for distributed AI orchestration",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Middleware
# ==============================================================================


@app.middleware("http")
async def logging_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Log all HTTP requests with timing."""
    start_time = time.time()
    request_id = request.headers.get("X-Request-ID", "unknown")

    logger.info(
        "http.request.start",
        method=request.method,
        path=request.url.path,
        request_id=request_id,
    )

    try:
        response = await call_next(request)
        duration = time.time() - start_time

        HTTP_REQUEST_DURATION.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code,
        ).observe(duration)

        logger.info(
            "http.request.complete",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=int(duration * 1000),
            request_id=request_id,
        )

        return response

    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            "http.request.error",
            method=request.method,
            path=request.url.path,
            error=str(e),
            duration_ms=int(duration * 1000),
            request_id=request_id,
        )
        raise


# ==============================================================================
# API Endpoints
# ==============================================================================


@app.post("/plan", response_model=PlanResponse, status_code=status.HTTP_200_OK)
async def create_plan(request: PlanRequest) -> PlanResponse:
    """
    Generate execution plan for a given goal.

    Takes a goal, constraints, and context, and returns an ordered sequence of
    subtasks with dependencies and acceptance criteria.

    Args:
        request: Plan request with goal, constraints, and context

    Returns:
        PlanResponse with ordered subtasks

    Raises:
        HTTPException: 400 for validation errors, 500 for planning failures
    """
    PLAN_REQUEST_COUNTER.inc()

    logger.info(
        "plan.request",
        request_id=request.request_id,
        goal=request.goal[:100],
        constraints_count=len(request.constraints),
    )

    start_time = time.time()

    try:
        plan: PlanResponse = await app.state.planner.generate_plan(
            goal=request.goal,
            constraints=request.constraints,
            context=request.context,
        )

        duration = time.time() - start_time
        PLAN_DURATION_HISTOGRAM.observe(duration)
        PLAN_SUCCESS_COUNTER.inc()

        logger.info(
            "plan.success",
            request_id=request.request_id,
            steps=len(plan.plan),
            duration_ms=int(duration * 1000),
            confidence=plan.confidence,
            complexity=plan.complexity_score,
        )

        return plan

    except InvalidDependencyError as e:
        PLAN_ERROR_COUNTER.labels(error_type="invalid_dependency").inc()
        logger.error("plan.validation_error", request_id=request.request_id, error=str(e))
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    except LLMError as e:
        PLAN_ERROR_COUNTER.labels(error_type="llm_error").inc()
        logger.error("plan.llm_error", request_id=request.request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM service error: {e}",
        ) from e

    except PlanningError as e:
        PLAN_ERROR_COUNTER.labels(error_type="planning_error").inc()
        logger.error("plan.error", request_id=request.request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Planning failed: {e}",
        ) from e

    except Exception as e:
        PLAN_ERROR_COUNTER.labels(error_type="unknown").inc()
        logger.error("plan.unexpected_error", request_id=request.request_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        ) from e


@app.get("/health", response_model=HealthResponse, status_code=status.HTTP_200_OK)
async def health_check() -> HealthResponse:
    """
    Health check endpoint for Kubernetes liveness probes.

    Returns basic service information and health status.
    """
    settings = get_settings()

    return HealthResponse(
        status="healthy",
        version=settings.version,
        model=settings.llm_model,
        timestamp=datetime.now(UTC).isoformat(),
    )


@app.get("/ready", response_model=ReadinessResponse, status_code=status.HTTP_200_OK)
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check endpoint for Kubernetes readiness probes.

    Verifies that the service is ready to accept requests.
    """
    checks = {
        "planner_initialized": hasattr(app.state, "planner"),
        "api_key_configured": bool(get_settings().openai_api_key),
    }

    ready = all(checks.values())

    return ReadinessResponse(ready=ready, checks=checks)


@app.get("/metrics", response_class=PlainTextResponse)
async def metrics() -> Response:
    """
    Prometheus metrics endpoint.

    Returns metrics in Prometheus exposition format.
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )


@app.get("/capabilities", response_model=CapabilitiesResponse, status_code=status.HTTP_200_OK)
async def get_capabilities() -> CapabilitiesResponse:
    """
    Return arm capabilities information.

    Provides metadata about this arm's capabilities, performance, and cost.
    """
    return CapabilitiesResponse(
        arm_id="planner",
        capabilities=[
            "planning",
            "task_decomposition",
            "dependency_resolution",
            "arm_selection",
            "cost_estimation",
        ],
        cost_tier=2,
        average_latency_ms=1500,
        success_rate=0.92,
    )


# ==============================================================================
# Error Handlers
# ==============================================================================


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Global exception handler for unhandled errors."""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_type=type(exc).__name__,
    )

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )
