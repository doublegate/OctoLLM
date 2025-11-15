"""
OctoLLM Orchestrator Service - Main FastAPI Application

The central brain of OctoLLM responsible for strategic planning, task delegation,
and coordination across all specialized arms.

Endpoints:
- POST /submit - Submit a new task
- GET /tasks/{task_id} - Get task status and result
- GET /health - Health check (Kubernetes liveness)
- GET /ready - Readiness check (Kubernetes readiness)
- GET /metrics - Prometheus metrics

Usage:
    uvicorn app.main:app --reload --port 8000
"""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import structlog
from fastapi import FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.config import get_settings
from app.database import (
    create_task,
    get_database,
    get_task,
    get_task_count_by_status,
)
from app.models import (
    HealthResponse,
    ReadinessResponse,
    TaskContract,
    TaskRequest,
    TaskResponse,
    TaskStatus,
    TaskSubmitResponse,
)
from app.reflex_client import ReflexCircuitBreakerOpen, ReflexClient, ReflexServiceUnavailable

logger = structlog.get_logger(__name__)

# ==============================================================================
# Prometheus Metrics
# ==============================================================================

TASK_SUBMIT_COUNTER = Counter(
    "orchestrator_tasks_submitted_total",
    "Total number of tasks submitted",
    ["priority"],
)

TASK_STATUS_COUNTER = Counter(
    "orchestrator_task_status_total",
    "Total number of tasks by status",
    ["status"],
)

TASK_PROCESSING_TIME = Histogram(
    "orchestrator_task_processing_seconds",
    "Task processing time in seconds",
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)

HTTP_REQUEST_DURATION = Histogram(
    "orchestrator_http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint", "status"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

REFLEX_CALL_COUNTER = Counter(
    "orchestrator_reflex_calls_total",
    "Total number of Reflex Layer calls",
    ["status"],
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
        "orchestrator.startup",
        version=settings.version,
        environment=settings.environment,
    )

    # Initialize database
    db = get_database()
    try:
        await db.create_tables()
        logger.info("orchestrator.database_ready")
    except Exception as e:
        logger.error("orchestrator.database_init_failed", error=str(e))
        raise

    # Initialize Reflex client
    if settings.enable_reflex_integration:
        app.state.reflex_client = ReflexClient(
            base_url=settings.reflex_layer_url,
            timeout=settings.reflex_layer_timeout,
            max_retries=settings.reflex_layer_max_retries,
            circuit_breaker_threshold=settings.reflex_layer_circuit_breaker_threshold,
            circuit_breaker_reset_timeout=settings.reflex_layer_circuit_breaker_reset_timeout,
        )
        logger.info("orchestrator.reflex_client_ready")
    else:
        app.state.reflex_client = None
        logger.warning("orchestrator.reflex_integration_disabled")

    yield

    # Shutdown
    logger.info("orchestrator.shutdown")
    if app.state.reflex_client:
        await app.state.reflex_client.close()
    await db.close()


# ==============================================================================
# FastAPI Application
# ==============================================================================

settings = get_settings()

app = FastAPI(
    title="OctoLLM Orchestrator",
    description="Central brain for OctoLLM distributed AI orchestration",
    version=settings.version,
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# ==============================================================================
# Middleware
# ==============================================================================


@app.middleware("http")
async def add_request_id(request: Request, call_next: Any) -> Response:
    """Add unique request ID to each request."""
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    request.state.request_id = request_id

    # Add to structured logging context
    with structlog.contextvars.bound_contextvars(request_id=request_id):
        response: Response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


@app.middleware("http")
async def log_requests(request: Request, call_next: Any) -> Response:
    """Log all HTTP requests with timing."""
    start_time = time.time()

    response: Response = await call_next(request)

    duration = time.time() - start_time

    logger.info(
        "http.request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration * 1000,
    )

    # Record Prometheus metrics
    HTTP_REQUEST_DURATION.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).observe(duration)

    return response


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# Exception Handlers
# ==============================================================================


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Handle HTTP exceptions."""
    logger.warning(
        "http.exception",
        status_code=exc.status_code,
        detail=exc.detail,
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "request_id": getattr(request.state, "request_id", None)},
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle uncaught exceptions."""
    logger.error(
        "http.uncaught_exception",
        error=str(exc),
        error_type=type(exc).__name__,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "request_id": getattr(request.state, "request_id", None),
        },
    )


# ==============================================================================
# API Endpoints
# ==============================================================================


@app.post(
    "/submit",
    response_model=TaskSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["tasks"],
)
async def submit_task(request: TaskRequest) -> TaskSubmitResponse:
    """
    Submit a new task for processing.

    The task will be validated by the Reflex Layer (PII/injection check),
    then stored in the database and queued for background processing.

    Returns:
        202 Accepted with task_id and status
    """
    settings = get_settings()
    db = get_database()

    # Create TaskContract from request
    contract = TaskContract(
        goal=request.goal,
        constraints=request.constraints or {},
        context=request.context,
        acceptance_criteria=request.acceptance_criteria or [],
        budget=request.budget or None,
        priority=request.priority or None,
        metadata=request.metadata or {},
    )

    # Call Reflex Layer for PII/injection detection
    if settings.enable_reflex_integration and app.state.reflex_client:
        try:
            reflex_response = await app.state.reflex_client.process(
                text=contract.goal,
                user_id=None,
                context={"task_id": contract.task_id},
            )

            REFLEX_CALL_COUNTER.labels(status=reflex_response.status.value).inc()

            # Check if request was blocked
            if reflex_response.is_blocked:
                logger.warning(
                    "task.blocked_by_reflex",
                    task_id=contract.task_id,
                    pii_detected=reflex_response.pii_detected,
                    injection_detected=reflex_response.injection_detected,
                )
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail={
                        "message": "Task blocked by security policy",
                        "pii_detected": reflex_response.pii_detected,
                        "injection_detected": reflex_response.injection_detected,
                        "details": {
                            "pii_matches": [m.model_dump() for m in reflex_response.pii_matches],
                            "injection_matches": [
                                m.model_dump() for m in reflex_response.injection_matches
                            ],
                        },
                    },
                )

            logger.info(
                "task.passed_reflex_check",
                task_id=contract.task_id,
                cache_hit=reflex_response.cache_hit,
            )

        except ReflexCircuitBreakerOpen:
            logger.error("task.reflex_circuit_breaker_open", task_id=contract.task_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Reflex Layer temporarily unavailable (circuit breaker open)",
            ) from None

        except ReflexServiceUnavailable:
            logger.error("task.reflex_unavailable", task_id=contract.task_id)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Reflex Layer service unavailable",
            ) from None

    # Store task in database
    async with db.session() as session:
        task = await create_task(session, contract)

    TASK_SUBMIT_COUNTER.labels(priority=contract.priority.value).inc()
    TASK_STATUS_COUNTER.labels(status=TaskStatus.PENDING.value).inc()

    logger.info(
        "task.submitted",
        task_id=str(task.id),
        goal=contract.goal[:50],
        priority=contract.priority.value,
    )

    return TaskSubmitResponse(
        task_id=str(task.id),
        status=TaskStatus.PENDING,
        message="Task submitted successfully and queued for processing",
    )


@app.get(
    "/tasks/{task_id}",
    response_model=TaskResponse,
    tags=["tasks"],
)
async def get_task_status(task_id: str) -> TaskResponse:
    """
    Get task status and result.

    Args:
        task_id: Task identifier

    Returns:
        Task status and result (if completed)

    Raises:
        404: Task not found
    """
    db = get_database()

    async with db.session() as session:
        task = await get_task(session, task_id)

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Task {task_id} not found",
        )

    return task.to_response()


@app.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint for Kubernetes liveness probe.

    Returns:
        200 OK if service is alive
    """
    settings = get_settings()
    return HealthResponse(
        status="healthy",
        version=settings.version,
    )


@app.get("/ready", response_model=ReadinessResponse, tags=["health"])
async def readiness_check() -> ReadinessResponse:
    """
    Readiness check endpoint for Kubernetes readiness probe.

    Checks if all dependencies (database, Reflex Layer) are available.

    Returns:
        200 OK if service is ready to accept requests
        503 Service Unavailable if dependencies are not ready
    """
    settings = get_settings()
    db = get_database()

    checks: dict[str, bool] = {}

    # Check database connection
    checks["database"] = await db.health_check()

    # Check Reflex Layer (if enabled)
    if settings.enable_reflex_integration and app.state.reflex_client:
        checks["reflex_layer"] = await app.state.reflex_client.health_check()
    else:
        checks["reflex_layer"] = True  # Not required if disabled

    # Service is ready if all checks pass
    is_ready = all(checks.values())

    if not is_ready:
        logger.warning("orchestrator.not_ready", checks=checks)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"ready": False, "checks": checks},
        )

    return ReadinessResponse(ready=True, checks=checks)


@app.get("/metrics", tags=["metrics"])
async def metrics() -> PlainTextResponse:
    """
    Prometheus metrics endpoint.

    Returns:
        Prometheus metrics in text format
    """
    return PlainTextResponse(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    """Root endpoint redirect to docs."""
    return {
        "service": "OctoLLM Orchestrator",
        "version": settings.version,
        "docs": "/docs",
        "health": "/health",
        "ready": "/ready",
        "metrics": "/metrics",
    }


# ==============================================================================
# Development-only endpoints
# ==============================================================================

if settings.debug:

    @app.get("/debug/stats", tags=["debug"])
    async def debug_stats() -> dict[str, Any]:
        """Get debug statistics (development only)."""
        db = get_database()

        async with db.session() as session:
            counts = await get_task_count_by_status(session)

        reflex_metrics = app.state.reflex_client.get_metrics() if app.state.reflex_client else None

        return {
            "task_counts": counts,
            "reflex_metrics": reflex_metrics,
        }
