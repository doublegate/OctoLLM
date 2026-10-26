"""
Memory / Curator arm.

The first arm in this repository that does something. Qdrant has been in the compose
stack since Phase 0 with nothing reading or writing it; this is what makes the
"distributed memory" in every architecture diagram real.

Two write paths and one read path:

  POST /remember   commit an artifact, for a caller that has one in hand
  (ring)           `artifact` consumed from the Neural Ring, which is how work
                   reaches memory without anyone calling it
  POST /recall     similarity search over episodic memory, bounded by the caller's
                   clearance

Both HTTP routes require a capability token. Memory holds every arm's output, so an
open recall endpoint is a read of the whole system's work — and Stage 5's rule is that
an arm adopts the gate in the stage that builds it. This is that stage.

`/health`, `/ready`, `/capabilities` and `/metrics` stay open, because a health check
that needs a credential is a health check that reports "down" whenever authorization is
misconfigured.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from typing import Any

import structlog
from fastapi import Depends, FastAPI, HTTPException, Request, status
from octollm_common import create_arm_app
from octollm_common.capability import CapabilityClaims, CapabilityVerifier, InMemoryCallCounter
from octollm_common.errors import error_body
from octollm_common.llm import create_provider
from octollm_common.models.contracts import (
    RecallRequest,
    RecallResponse,
    RememberRequest,
    RememberResponse,
)
from octollm_common.models.provenance import Sensitivity
from octollm_common.roster import spec_for
from octollm_common.security import CapabilityPolicy, RequireCapability, clearance_from

from .config import get_settings
from .service import ARM_ID, ConflictingArtifactError, MemoryService, UnsupportedScopeError

logger = structlog.get_logger(__name__)

SPEC = spec_for("memory")

#: Scopes. `call:recall` matches what the orchestrator derives from the roster
#: endpoint; the write scope is separate so that a token permitting recall does not
#: also permit rewriting the record it reads from.
RECALL_SCOPE = "call:recall"
WRITE_SCOPE = "memory:write"


class Runtime:
    """Everything the arm owns between startup and shutdown."""

    def __init__(self) -> None:
        self.service: MemoryService | None = None
        self.consumer: Any = None
        self.ring_retry_task: asyncio.Task[None] | None = None
        self.engine: Any = None
        self.qdrant: Any = None
        self.provider: Any = None
        self.redis: Any = None


RUNTIME = Runtime()
_CALL_COUNTER = InMemoryCallCounter()


def _verifier() -> CapabilityVerifier:
    """
    Built on first use, not at import.

    An unconfigured deployment must still serve `/health`: "authorization is not set
    up" and "this service is down" are different problems with different fixes.
    `CapabilityPolicy` defers to this and turns a config error into 503.
    """
    settings = get_settings()
    return CapabilityVerifier(
        {settings.capability_kid: settings.capability_secret or ""},
        audience=ARM_ID,
        counter=_CALL_COUNTER,
    )


RECALL_POLICY = CapabilityPolicy(verifier_factory=_verifier, scope=RECALL_SCOPE)
WRITE_POLICY = CapabilityPolicy(verifier_factory=_verifier, scope=WRITE_SCOPE)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Open the two stores and, unless disabled, start draining the ring."""
    settings = get_settings()
    from qdrant_client import AsyncQdrantClient
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from .store import SemanticStore
    from .vectors import EpisodicStore

    RUNTIME.engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(RUNTIME.engine, expire_on_commit=False)
    RUNTIME.qdrant = AsyncQdrantClient(url=settings.qdrant_url, timeout=settings.qdrant_timeout)
    RUNTIME.provider = create_provider()

    RUNTIME.service = MemoryService(
        semantic=SemanticStore(session_factory),
        episodic=EpisodicStore(RUNTIME.qdrant, RUNTIME.provider),
    )
    logger.info("memory_started", qdrant=settings.qdrant_url, ring=settings.ring_enabled)

    if settings.ring_enabled:
        await _start_ring(settings)
        if RUNTIME.consumer is None:
            RUNTIME.ring_retry_task = asyncio.create_task(
                _retry_ring_until_attached(settings),
                name="memory-ring-reconnect",
            )

    try:
        yield
    finally:
        if RUNTIME.ring_retry_task is not None:
            RUNTIME.ring_retry_task.cancel()
            with suppress(asyncio.CancelledError):
                await RUNTIME.ring_retry_task
            RUNTIME.ring_retry_task = None
        if RUNTIME.consumer is not None:
            await RUNTIME.consumer.stop()
        if RUNTIME.redis is not None:
            await RUNTIME.redis.aclose()
        if RUNTIME.qdrant is not None:
            await RUNTIME.qdrant.close()
        if RUNTIME.provider is not None:
            await RUNTIME.provider.aclose()
        if RUNTIME.engine is not None:
            await RUNTIME.engine.dispose()
        logger.info("memory_stopped")


async def _start_ring(settings: Any) -> None:
    """
    Attach to the ring.

    A failure here is logged and **not** raised: the HTTP surface is independently
    useful, and an arm that refuses to start because Redis is slow to come up would
    make the compose stack's startup order load-bearing.
    """
    import redis.asyncio as redis_asyncio
    from octollm_common.ring import RingConsumer, RingPublisher

    from .consumer import ArtifactConsumer

    try:
        RUNTIME.redis = redis_asyncio.from_url(settings.redis_url)
        await RUNTIME.redis.ping()
        assert RUNTIME.service is not None  # noqa: S101 - set immediately above
        RUNTIME.consumer = ArtifactConsumer(
            service=RUNTIME.service,
            consumer=RingConsumer(RUNTIME.redis, SPEC, consumer_name=f"{ARM_ID}-{id(RUNTIME):x}"),
            publisher=RingPublisher(RUNTIME.redis, SPEC),
            batch=settings.ring_batch,
            block_ms=settings.ring_block_ms,
        )
        await RUNTIME.consumer.start()
    except Exception as exc:  # noqa: BLE001
        logger.warning("ring_unavailable", error=str(exc))
        RUNTIME.consumer = None


async def _retry_ring_until_attached(settings: Any) -> None:
    """Keep retrying ring attachment in the background if Redis was unavailable at boot."""
    while RUNTIME.consumer is None:
        await asyncio.sleep(2.0)
        await _start_ring(settings)


def _service() -> MemoryService:
    if RUNTIME.service is None:  # pragma: no cover - lifespan always sets it
        raise RuntimeError("Memory service is not initialised; lifespan did not run.")
    return RUNTIME.service


async def _readiness() -> dict[str, Any]:
    if RUNTIME.service is None:
        return {"stores": False}
    checks = await RUNTIME.service.health()
    if RUNTIME.consumer is not None:
        checks.update(RUNTIME.consumer.stats())
    checks["ring_attached"] = RUNTIME.consumer is not None
    return checks


async def recall(
    body: RecallRequest,
    request: Request,
    claims: CapabilityClaims = Depends(RequireCapability(RECALL_POLICY)),
) -> RecallResponse:
    """
    Search episodic memory.

    `caller` and `clearance` come from the verified token, never from the body. A
    caller that states its own clearance is the same escalation as an arm that states
    its own peers, and `RecallRequest` deliberately has no field for either.
    """
    request_id = getattr(request.state, "request_id", "unknown")
    try:
        return await _service().recall(
            body,
            request_id=request_id,
            caller=claims.sub,
            clearance=Sensitivity(clearance_from(claims)),
        )
    except UnsupportedScopeError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=error_body(
                code="not_implemented",
                message=str(exc),
                request_id=request_id,
            ),
        ) from exc


async def remember(
    body: RememberRequest,
    request: Request,
    claims: CapabilityClaims = Depends(RequireCapability(WRITE_POLICY)),
) -> RememberResponse:
    """Commit one artifact. Idempotent: a redelivery is reported, not rejected."""
    request_id = getattr(request.state, "request_id", "unknown")
    if (
        body.artifact.provenance.task_id != claims.task_id
        or body.artifact.provenance.created_by != claims.sub
    ):
        logger.warning(
            "capability_denied",
            reason="artifact_provenance_mismatch",
            token_sub=claims.sub,
            artifact_created_by=body.artifact.provenance.created_by,
            token_task_id=claims.task_id,
            artifact_task_id=body.artifact.provenance.task_id,
            path=request.url.path,
            request_id=request_id,
        )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=error_body(
                code="forbidden",
                message="The presented capability token does not authorize this request.",
                request_id=request_id,
            ),
        )
    try:
        return await _service().remember(body, request_id=request_id)
    except ConflictingArtifactError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=error_body(
                code="conflict",
                message=str(exc),
                request_id=request_id,
            ),
        ) from exc


app = create_arm_app(
    SPEC,
    handler=recall,
    request_model=RecallRequest,
    response_model=RecallResponse,
    lifespan=lifespan,
    readiness=_readiness,
)

app.add_api_route(
    "/remember",
    remember,
    methods=["POST"],
    response_model=RememberResponse,
    tags=[ARM_ID],
    summary="Commit one artifact to memory",
)
