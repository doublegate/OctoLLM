"""
The arm application factory.

Eight services need the same five endpoints, the same error envelope, the same
correlation id and the same capability declaration. Written eight times, they drift
eight ways; this is the one place they are written.

`create_arm_app` gives every arm:

  GET  /health        liveness while the process is up
  GET  /ready         readiness, stating `implemented` honestly
  GET  /capabilities  the ArmSpec the orchestrator's registry reads
  GET  /metrics       Prometheus exposition
  <handler>           the arm's own endpoint, at its canonical path

An arm with no handler yet serves that path with **501**, naming the stage that
implements it. Not a plausible fake: a stub that answers convincingly makes an
unimplemented arm indistinguishable from a working one, which is the failure this
repository is being dug out of.

## `ArmSpec` carries the ring topology

`publishes`, `subscribes` and `peers` are declared here and read by the orchestrator
through the `/capabilities` call it already makes. So the full Neural Ring topology
arrives over a protocol that already exists -- and the orchestrator will only issue a
capability token for an edge that appears in it, which makes an undeclared peer call
unreachable rather than merely discouraged.
"""

from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Any

from fastapi import APIRouter, FastAPI, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, ConfigDict, Field

from .errors import error_body, install_error_handlers

__all__ = ["ArmSpec", "create_arm_app"]


class ArmSpec(BaseModel):
    """What an arm declares about itself, and the whole of what the registry reads."""

    model_config = ConfigDict(extra="forbid")

    arm_id: str = Field(..., description="Stable identifier, e.g. 'planner'")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(...)
    port: int = Field(..., ge=1, le=65535, description="Canonical container port")
    endpoint: str = Field(..., description="This arm's own path, e.g. '/plan'")
    capabilities: list[str] = Field(default_factory=list, description="Routing tags")
    cost_tier: int = Field(1, ge=1, le=5, description="1 cheap, 5 expensive")

    implemented: bool = Field(False)
    implemented_in_stage: int = Field(..., description="Which v1.0.0 stage builds it")

    # --- Neural Ring topology, read by the orchestrator's registry ---------------
    publishes: list[str] = Field(
        default_factory=list, description="Artifact types this arm publishes to the ring"
    )
    subscribes: list[str] = Field(
        default_factory=list, description="Artifact types this arm consumes"
    )
    peers: list[str] = Field(
        default_factory=list,
        description="arm_ids this arm may call directly. The orchestrator issues peer "
        "tokens ONLY for edges named here, so an undeclared edge is unreachable.",
    )


def create_arm_app(
    spec: ArmSpec,
    *,
    handler: Callable[..., Awaitable[Any]] | None = None,
    request_model: type[BaseModel] | None = None,
    response_model: type[BaseModel] | None = None,
    version: str = "0.5.0",
) -> FastAPI:
    """
    Build an arm's application.

    Args:
        spec: The arm's declaration. Also what `/capabilities` returns.
        handler: The arm's own endpoint. When omitted the path returns 501, which is
            what every arm does until Stage 8 builds it.
        request_model / response_model: The shared contract models from
            `octollm_common.models.contracts`. Passing anything else defeats the
            single-definition seam those exist to provide.
        version: Kept in step with `VERSION` by `scripts/version_sync.py`.
    """
    app = FastAPI(
        title=f"OctoLLM {spec.name}",
        description=spec.description,
        version=version,
    )
    install_error_handlers(app)

    @app.middleware("http")
    async def _correlate(request: Request, call_next: Callable[[Request], Awaitable[Any]]) -> Any:
        # Accept an inbound id so a task's spans stitch across arms; mint one when
        # absent so an error is always quotable.
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    router = APIRouter()

    @router.get("/health", tags=["health"])
    async def health() -> dict[str, Any]:
        return {"status": "healthy", "arm_id": spec.arm_id, "version": version}

    @router.get("/ready", tags=["health"])
    async def ready() -> dict[str, Any]:
        # `implemented` is reported here so that "the container is up" and "the arm
        # does anything" are never the same signal.
        return {
            "ready": True,
            "arm_id": spec.arm_id,
            "implemented": spec.implemented,
            "checks": {"process": True},
        }

    @router.get("/capabilities", tags=["registry"])
    async def capabilities() -> ArmSpec:
        return spec

    @router.get("/metrics", response_class=PlainTextResponse, tags=["metrics"])
    async def metrics() -> str:
        # Well-formed and nearly empty rather than absent: Prometheus scrapes from the
        # first second, and a 404 in the scrape log is noise that hides a real one.
        return (
            "# HELP octollm_arm_implemented Whether this arm is implemented (1) or a stub (0).\n"
            "# TYPE octollm_arm_implemented gauge\n"
            f'octollm_arm_implemented{{arm_id="{spec.arm_id}"}} {int(spec.implemented)}\n'
        )

    app.include_router(router)

    if handler is not None:
        app.add_api_route(
            spec.endpoint,
            handler,
            methods=["POST"],
            response_model=response_model,
            tags=[spec.arm_id],
        )
    else:

        async def _not_implemented(request: Request) -> JSONResponse:
            return JSONResponse(
                status_code=501,
                content=error_body(
                    code="not_implemented",
                    message=(
                        f"The {spec.name} arm is not implemented. "
                        f"It is scheduled for Stage {spec.implemented_in_stage} "
                        "of the v1.0.0 plan."
                    ),
                    request_id=getattr(request.state, "request_id", "unknown"),
                    details={
                        "arm_id": spec.arm_id,
                        "implemented_in_stage": spec.implemented_in_stage,
                    },
                ),
            )

        # Registered with the real request model so the OpenAPI document describes the
        # endpoint this arm WILL serve. A 501 whose schema is `{}` teaches a caller
        # nothing about what to send once it works.
        app.add_api_route(
            spec.endpoint,
            _not_implemented,
            methods=["POST"],
            tags=[spec.arm_id],
            responses={501: {"description": "Not implemented yet"}},
            openapi_extra=(
                {
                    "requestBody": {
                        "content": {
                            "application/json": {"schema": request_model.model_json_schema()}
                        }
                    }
                }
                if request_model is not None
                else None
            ),
        )

    return app
