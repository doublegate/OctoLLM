"""
A minimal, honest service skeleton for arms that have no implementation yet.

Five arm images existed with Dockerfiles whose `CMD` pointed at modules that were
never written — `uvicorn services.arms.planner.src.main:app` against a directory
holding only a `.gitkeep`. Every one of those containers crash-looped, so
`docker compose up` could never reach a healthy state, and the compose file, the
architecture diagrams and both SDKs all described a stack that had never once run.

This gives those images something real to serve. It is deliberately *not* a
framework: the shared arm framework — app factory, LLM provider, Neural Ring
client, the common contract models — is Stage 4, and this exists only so the stack
can come up and a task can round-trip before then.

What a stub arm does:

  GET  /health        always 200 while the process is alive
  GET  /ready         200, with `implemented: false` stated in the body
  GET  /capabilities  the arm's declared identity, so the registry has something
                      truthful to read
  GET  /metrics       Prometheus exposition, empty but well-formed
  POST /execute       **501 Not Implemented**, naming the stage that will build it

The last one is the point. A stub that returns a plausible fake result is worse
than no stub at all: it makes an unimplemented arm indistinguishable from a working
one, which is the exact failure this repository is being dug out of. A 501 carrying
the stage number is a fact a caller can act on.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse, PlainTextResponse

__all__ = ["create_stub_app"]


def create_stub_app(
    *,
    arm_id: str,
    name: str,
    description: str,
    port: int,
    capabilities: list[str],
    implemented_in_stage: int,
) -> FastAPI:
    """
    Build the stub application for one arm.

    Args:
        arm_id: Stable identifier used by the orchestrator's registry.
        name: Human-readable name.
        description: What this arm will do once it exists.
        port: The port this arm binds, per the canonical port map.
        capabilities: Routing tags the registry will match against.
        implemented_in_stage: Which v1.0.0 stage builds the real thing. Reported in
            every 501 so a caller is told when to expect it, not merely that it is
            missing.
    """
    app = FastAPI(
        title=f"OctoLLM {name} (stub)",
        description=f"{description}\n\nNot implemented; scheduled for Stage {implemented_in_stage}.",
        version="0.5.0",
    )

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return {"status": "healthy", "arm_id": arm_id, "implemented": False}

    @app.get("/ready")
    async def ready() -> dict[str, Any]:
        # Ready to serve what it can serve, which is its identity and nothing else.
        # Reporting `implemented: false` here keeps "the container is up" and "the
        # arm works" from being the same signal.
        return {
            "ready": True,
            "arm_id": arm_id,
            "implemented": False,
            "checks": {"process": True},
        }

    @app.get("/capabilities")
    async def capabilities_() -> dict[str, Any]:
        return {
            "arm_id": arm_id,
            "name": name,
            "description": description,
            "port": port,
            "capabilities": capabilities,
            "implemented": False,
            "implemented_in_stage": implemented_in_stage,
        }

    @app.get("/metrics", response_class=PlainTextResponse)
    async def metrics() -> str:
        # Well-formed and empty rather than absent: Prometheus scrapes this endpoint
        # from the moment the container starts, and a 404 in the scrape log is noise
        # that hides a real one.
        return (
            f"# HELP octollm_arm_stub Whether this arm is a stub (1) or implemented (0).\n"
            f"# TYPE octollm_arm_stub gauge\n"
            f'octollm_arm_stub{{arm_id="{arm_id}"}} 1\n'
        )

    @app.post("/execute")
    async def execute() -> JSONResponse:
        return JSONResponse(
            status_code=501,
            content={
                "error": {
                    "code": "not_implemented",
                    "message": (
                        f"The {name} arm is not implemented. It is scheduled for "
                        f"Stage {implemented_in_stage} of the v1.0.0 plan."
                    ),
                    "details": {"arm_id": arm_id, "implemented_in_stage": implemented_in_stage},
                }
            },
        )

    return app
