"""
The arm registry.

Both SDKs have shipped a `listArms()` / `list_arms()` call since Phase 0. Neither
endpoint existed, and the two SDKs did not even agree on the path: the TypeScript one
asked for `GET /arms`, the Python one for `GET /capabilities`. This module is the
endpoint, and `GET /arms` is the path that won -- `/capabilities` means *this
service's own declaration* on every arm, and reusing it here for "the arms I know
about" is the kind of near-collision that produces a wrong client six months later.

## Where the entries come from

The roster is `octollm_common.roster`, shared with every arm's `main.py` and with
`scripts/ci/check_port_map.py`. The orchestrator does not maintain a second list, so
there is no second list to drift.

Input and output schemas are generated from `octollm_common.models.contracts` -- the
same classes the arms use as their FastAPI models. A registry that published a
hand-written schema would be publishing a claim; this publishes the model.

## Why registration cannot introduce an arm

`POST /arms/register` **updates** a known arm and **refuses an unknown `arm_id`**.

An endpoint that lets a caller add an arm to the routing table is a privilege
escalation with extra steps: the orchestrator is the sole signing authority for
capability tokens, and an arm it can be told about is an arm it can be told to trust.
Dynamic registration arrives in Stage 5 behind an orchestrator-issued token; until
then the answer is 403, naming the stage, rather than a silent accept.

## Probing

`refresh()` calls each arm's `GET /capabilities` and records what came back. A probe
that fails marks the arm `unavailable` -- it never removes it, because "this arm is
down" and "this arm does not exist" are different facts and the registry is the only
place that can tell them apart.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any, Literal

import httpx
import structlog
from octollm_common.models.contracts import (
    CheckRequest,
    CheckResponse,
    CodeRequest,
    CodeResponse,
    ExecuteRequest,
    ExecuteResponse,
    PlanRequest,
    PlanResponse,
    SearchRequest,
    SearchResponse,
    ValidateRequest,
    ValidateResponse,
)
from octollm_common.roster import ROSTER, arm_base_url
from pydantic import BaseModel, ConfigDict, Field

logger = structlog.get_logger(__name__)

__all__ = [
    "ArmCapability",
    "ArmRegistry",
    "ListArmsResponse",
    "RegisterArmRequest",
    "RegisterArmResponse",
    "UnknownArm",
    "get_registry",
    "reset_registry",
]

ArmStatus = Literal["healthy", "degraded", "unavailable"]

#: The contract models each arm's endpoint accepts and returns. Arms with no contract
#: yet (memory, red-team) are absent, and their schemas are published as `{}` rather
#: than as a guess -- an invented schema is worse than an empty one, because a client
#: can act on it.
_CONTRACT_MODELS: dict[str, tuple[type[BaseModel], type[BaseModel]]] = {
    "planner": (PlanRequest, PlanResponse),
    "retriever": (SearchRequest, SearchResponse),
    "coder": (CodeRequest, CodeResponse),
    "judge": (ValidateRequest, ValidateResponse),
    "safety-guardian": (CheckRequest, CheckResponse),
    "executor": (ExecuteRequest, ExecuteResponse),
}


class UnknownArm(LookupError):
    """An operation named an `arm_id` that is not in the roster."""


class ArmCapability(BaseModel):
    """
    One arm, as the registry reports it.

    Three shapes of this existed and disagreed: the TypeScript SDK carried
    `input_schema`/`output_schema` and no status, the Python SDK carried a status and
    no schemas, and the arms' own `/capabilities` returned neither. This is the one
    that wins, and it is the union of what is actually knowable.
    """

    model_config = ConfigDict(extra="forbid")

    arm_id: str
    name: str
    description: str
    capabilities: list[str] = Field(default_factory=list, description="Routing tags")
    cost_tier: int = Field(..., ge=1, le=5)

    # `endpoint` is the PATH on the arm, and `base_url` is where the arm listens. The
    # SDKs documented `endpoint` as "Kubernetes service endpoint", meaning a URL; two
    # meanings under one name is how a client builds `http://hosthttp://host/plan`.
    endpoint: str = Field(..., description="Path on the arm, e.g. '/plan'")
    base_url: str = Field(..., description="Where the arm listens")
    port: int = Field(..., ge=1, le=65535)

    input_schema: dict[str, Any] = Field(default_factory=dict)
    output_schema: dict[str, Any] = Field(default_factory=dict)

    implemented: bool = Field(..., description="Whether the endpoint does anything yet")
    implemented_in_stage: int = Field(..., description="Which v1.0.0 stage builds it")

    publishes: list[str] = Field(default_factory=list)
    subscribes: list[str] = Field(default_factory=list)
    peers: list[str] = Field(default_factory=list)

    status: ArmStatus = Field("unavailable", description="Result of the last probe")
    last_probed_at: datetime | None = Field(None, description="None if never probed")


class ListArmsResponse(BaseModel):
    """
    Wrapped in an object rather than returned as a bare array.

    A top-level JSON array cannot grow a field -- paging, a probe timestamp, a count --
    without breaking every client that parses it. Both SDKs already expect `{arms: [...]}`.
    """

    model_config = ConfigDict(extra="forbid")

    arms: list[ArmCapability]


class RegisterArmRequest(BaseModel):
    """
    What `POST /arms/register` accepts.

    Note what is **absent**: `base_url`, `port`, `endpoint` and `cost_tier`. Those are
    roster facts, derived from configuration the orchestrator owns. A caller able to
    restate where an arm listens could redirect that arm's traffic to a host it
    controls -- every task step routed there, carrying task content and, from Stage 5,
    a capability token. That is the same escalation the unknown-`arm_id` 403 prevents,
    and refusing one while permitting the other would have been no protection at all.

    An arm moves when its configuration moves, not when it says so.
    """

    model_config = ConfigDict(extra="forbid")

    arm_id: str = Field(..., min_length=1)
    capabilities: list[str] | None = Field(None, description="Replaces the routing tags")
    implemented: bool | None = Field(None, description="Whether the endpoint works yet")
    publishes: list[str] | None = None
    subscribes: list[str] | None = None
    peers: list[str] | None = Field(
        None,
        description="Declared ring edges. Advisory here: the orchestrator issues peer "
        "tokens from its own roster, so an arm cannot widen its own reach by "
        "registering a peer the roster does not name.",
    )


class RegisterArmResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["updated"] = "updated"
    arm: ArmCapability


def _schemas(arm_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    models = _CONTRACT_MODELS.get(arm_id)
    if models is None:
        return {}, {}
    request_model, response_model = models
    return request_model.model_json_schema(), response_model.model_json_schema()


class ArmRegistry:
    """The known arms, and the last thing each of them said about itself."""

    def __init__(self, *, host_template: str = "http://{service}:{port}") -> None:
        self._arms: dict[str, ArmCapability] = {}
        for spec in ROSTER:
            input_schema, output_schema = _schemas(spec.arm_id)
            self._arms[spec.arm_id] = ArmCapability(
                arm_id=spec.arm_id,
                name=spec.name,
                description=spec.description,
                capabilities=list(spec.capabilities),
                cost_tier=spec.cost_tier,
                endpoint=spec.endpoint,
                base_url=arm_base_url(spec.arm_id, host_template=host_template),
                port=spec.port,
                input_schema=input_schema,
                output_schema=output_schema,
                implemented=spec.implemented,
                implemented_in_stage=spec.implemented_in_stage,
                publishes=list(spec.publishes),
                subscribes=list(spec.subscribes),
                peers=list(spec.peers),
            )

    def all(self) -> list[ArmCapability]:
        """
        Every known arm, in roster order, which is port order.

        Named `all` rather than `list`: a method called `list` shadows the builtin for
        every annotation that follows it in the class body, so `-> list[ArmCapability]`
        below would resolve to this method instead of the type.
        """
        return list(self._arms.values())

    def get(self, arm_id: str) -> ArmCapability:
        try:
            return self._arms[arm_id]
        except KeyError as exc:
            raise UnknownArm(arm_id) from exc

    def register(self, request: RegisterArmRequest) -> ArmCapability:
        """
        Update a known arm.

        Raises:
            UnknownArm: the id is not in the roster. Deliberately not an upsert --
                see the module docstring.
        """
        current = self.get(request.arm_id)
        updates = request.model_dump(exclude_none=True, exclude={"arm_id"})
        updated = current.model_copy(update={**updates, "last_probed_at": _now()})
        self._arms[request.arm_id] = updated
        logger.info("arm_registered", arm_id=request.arm_id, fields=sorted(updates))
        return updated

    async def refresh(self, *, timeout: float = 2.0) -> list[ArmCapability]:
        """
        Probe every arm's `/capabilities` concurrently and record what came back.

        A failed probe marks the arm `unavailable` and never removes it: "down" and
        "does not exist" are different facts, and this is the only place that can
        distinguish them.
        """
        async with httpx.AsyncClient(timeout=timeout) as client:
            await asyncio.gather(
                *(self._probe(client, arm_id) for arm_id in self._arms),
                return_exceptions=True,
            )
        return self.all()

    async def _probe(self, client: httpx.AsyncClient, arm_id: str) -> None:
        arm = self._arms[arm_id]
        try:
            response = await client.get(f"{arm.base_url}/capabilities")
            response.raise_for_status()
            body = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            # Debug, not warning: five of these arms are known not to be running yet,
            # and a log line per arm per probe would drown the ones that matter.
            logger.debug("arm_probe_failed", arm_id=arm_id, error=str(exc))
            self._arms[arm_id] = arm.model_copy(
                update={"status": "unavailable", "last_probed_at": _now()}
            )
            return

        # Only the fields an arm is entitled to change about itself. It does not get
        # to rewrite its own port, endpoint or cost tier -- those are roster facts,
        # and an arm that could restate them could redirect its own traffic.
        allowed = {"capabilities", "implemented", "publishes", "subscribes", "peers"}
        updates = {key: value for key, value in body.items() if key in allowed}
        self._arms[arm_id] = arm.model_copy(
            update={**updates, "status": "healthy", "last_probed_at": _now()}
        )


def _now() -> datetime:
    return datetime.now(UTC)


_registry: ArmRegistry | None = None


def get_registry() -> ArmRegistry:
    """The process-wide registry."""
    global _registry
    if _registry is None:
        _registry = ArmRegistry()
    return _registry


def reset_registry() -> None:
    """Drop the registry. Used by tests; the roster is reloaded on next access."""
    global _registry
    _registry = None
