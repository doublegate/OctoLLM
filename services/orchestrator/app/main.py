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
from fastapi.responses import PlainTextResponse
from octollm_common.errors import error_body, install_error_handlers
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.config import get_settings
from app.database import create_task, get_database, get_task, get_task_count_by_status
from app.models import (
    HealthResponse,
    Priority,
    ReadinessResponse,
    ResourceBudget,
    TaskContract,
    TaskRequest,
    TaskResponse,
    TaskStatus,
    TaskSubmitResponse,
)
from app.reflex_client import ReflexCircuitBreakerOpen, ReflexClient, ReflexServiceUnavailable
from app.registry import (
    ListArmsResponse,
    RegisterArmRequest,
    RegisterArmResponse,
    UnknownArm,
    get_registry,
)

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

# `app.state.reflex_client` is assigned by the lifespan handler, but several request
# handlers read it unconditionally. Seed it here so the attribute always exists: any ASGI
# runner that does not emit lifespan events (httpx's ASGITransport, among others) would
# otherwise turn every one of those reads into an AttributeError at request time.
app.state.reflex_client = None

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

# One envelope, shared with all eight arms:
#
#   {"error": {"code", "message", "details", "request_id", "timestamp"}}
#
# This service previously had its own: `{"error": <string-or-object>}` for
# HTTPException and FastAPI's default `{"detail": [...]}` for request-validation
# failures, so the shape a client saw depended on which kind of error occurred and
# `error` was sometimes a string and sometimes an object. `docs/api/CONTRACT.md`
# declared the nested envelope for both services in Stage 3; this is the service
# catching up with its own contract.
install_error_handlers(app)


# ==============================================================================
# API Endpoints
# ==============================================================================


@app.post(
    "/submit",
    response_model=TaskSubmitResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["tasks"],
)
async def submit_task(request: TaskRequest, http_request: Request) -> TaskSubmitResponse:
    """
    Submit a new task for processing.

    The task will be validated by the Reflex Layer (PII/injection check),
    then stored in the database and queued for background processing.

    Returns:
        202 Accepted with task_id and status
    """
    settings = get_settings()
    db = get_database()

    # Create TaskContract from request.
    #
    # `budget` and `priority` are non-optional on TaskContract and carry model defaults;
    # the omitted-field case must therefore fall back to those defaults rather than to
    # None. Passing `or None` (as this did) made every submission that left `budget` out
    # of the payload fail validation and return 500.
    contract = TaskContract(
        goal=request.goal,
        constraints=request.constraints or {},
        context=request.context,
        acceptance_criteria=request.acceptance_criteria or [],
        budget=request.budget or ResourceBudget(),
        priority=request.priority or Priority.MEDIUM,
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
                    # Pre-built envelope: the handler passes an already-wrapped body
                    # through untouched, so this reaches the client in the same shape
                    # as every other error rather than nested one level deeper.
                    #
                    # `matched_text` is stripped from each finding. The reflex layer
                    # returns the offending span, and echoing it back would put the
                    # detected credential or SSN into the caller's logs -- inside the
                    # very response that exists to say it must not travel.
                    detail=error_body(
                        code="blocked_by_policy",
                        message="Task blocked by security policy",
                        request_id=getattr(http_request.state, "request_id", "unknown"),
                        details={
                            "pii_detected": reflex_response.pii_detected,
                            "injection_detected": reflex_response.injection_detected,
                            "pii_matches": [
                                m.model_dump(exclude={"matched_text"})
                                for m in reflex_response.pii_matches
                            ],
                            "injection_matches": [
                                m.model_dump(exclude={"matched_text"})
                                for m in reflex_response.injection_matches
                            ],
                        },
                    ),
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


# ==============================================================================
# Arm registry
# ==============================================================================


@app.get("/arms", response_model=ListArmsResponse, tags=["registry"])
async def list_arms(refresh: bool = False) -> ListArmsResponse:
    """
    List every arm the orchestrator knows about.

    Both SDKs have shipped this call since Phase 0 against an endpoint that did not
    exist, and they disagreed about its path: TypeScript asked for `/arms`, Python for
    `/capabilities`. `/arms` wins -- `/capabilities` means *this service's own
    declaration* on every arm, and a near-collision like that produces a wrong client
    later.

    Args:
        refresh: Probe each arm's `/capabilities` first. Off by default so the common
            call is a memory read: this endpoint is polled, and eight HTTP requests
            per poll would make the registry a source of load rather than of answers.

    Returns:
        Every arm in the roster, including the two that are not built yet, each
        carrying the stage that builds it. An arm that is down reports `unavailable`
        rather than disappearing -- "down" and "does not exist" are different facts.
    """
    registry = get_registry()
    arms = await registry.refresh() if refresh else registry.all()
    return ListArmsResponse(arms=arms)


@app.post("/arms/register", response_model=RegisterArmResponse, tags=["registry"])
async def register_arm(request: RegisterArmRequest) -> RegisterArmResponse:
    """
    Update what the orchestrator knows about an arm.

    This deliberately **cannot introduce an arm**. An endpoint that lets a caller add
    an arm to the routing table is a privilege escalation with extra steps: the
    orchestrator is the sole signing authority for capability tokens, so an arm it can
    be told about is an arm it can be told to trust. An unknown `arm_id` gets 403
    naming Stage 5, which adds token-gated dynamic registration -- not a silent accept.

    Raises:
        403: The `arm_id` is not in the roster.
    """
    try:
        arm = get_registry().register(request)
    except UnknownArm as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                f"Unknown arm '{request.arm_id}'. Registration updates an arm in the "
                "roster; it cannot introduce one. Dynamic registration arrives in "
                "Stage 5 of the v1.0.0 plan, gated on an orchestrator-issued "
                "capability token."
            ),
        ) from exc
    return RegisterArmResponse(arm=arm)


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
async def readiness_check(http_request: Request) -> ReadinessResponse:
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
            # Which dependency is down belongs in `details`, not at the top level: a
            # probe reads the status code, and an operator reads the body, and both
            # of them read every other error in this stack the same way.
            detail=error_body(
                code="unavailable",
                message="One or more dependencies are not ready.",
                request_id=getattr(http_request.state, "request_id", "unknown"),
                details={"ready": False, "checks": checks},
            ),
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
