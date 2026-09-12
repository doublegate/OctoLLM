"""
Every arm's request and response models, defined exactly once.

This module is the seam. Arms import these as their FastAPI request and response
models; the orchestrator imports the same classes as its client models. There is no
second definition to drift from, so a field rename is a type error at import time
rather than a 422 in production six weeks later.

That is not a hypothetical concern here. The orchestrator's reflex client and the
reflex layer maintained separate definitions of the same payload, and the two
disagreed on four points at once -- the client could not parse a single real response
for the entire life of both services, while 39 of its tests passed against mocks
built from its own models.

## The common envelope

Every arm response carries `arm_id`, `request_id`, `usage` and `confidence`.

`usage` is the load-bearing one. Once arms call each other directly over the Neural
Ring (Stage 5), an arm's own response is the only place its peer's spend can be
reported -- the orchestrator never sees that call. An arm that invokes a peer returns
the **cumulative** usage of both, which is why this is on the base class rather than
on the arms that happen to call a model today.

`confidence` is computed from observable signals by the arm, never taken from a
model's self-report. A model asked to rate its own confidence produces a number that
correlates with fluency, not correctness.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

__all__ = [
    "ArmRequest",
    "ArmResponse",
    "CheckRequest",
    "CheckResponse",
    "CodeRequest",
    "CodeResponse",
    "ExecuteRequest",
    "ExecuteResponse",
    "PlanRequest",
    "PlanResponse",
    "PlanStep",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "UsageReport",
    "ValidateRequest",
    "ValidateResponse",
    "Verdict",
]


class UsageReport(BaseModel):
    """
    What a request cost, cumulatively.

    Mirrors `octollm_common.llm.Usage` on the wire. It is a separate model rather than
    the dataclass because this one crosses a network boundary and must version
    independently of the internal one.
    """

    model_config = ConfigDict(extra="forbid")

    provider: str = Field(..., description="Provider, or 'mixed' when peers used others")
    model: str = Field(..., description="Model, or 'mixed'")
    input_tokens: int = Field(0, ge=0)
    output_tokens: int = Field(0, ge=0)
    peer_calls: int = Field(
        0,
        ge=0,
        description="Direct arm-to-arm calls made while serving this request. The "
        "orchestrator cannot observe these any other way.",
    )


class ArmRequest(BaseModel):
    """Fields every arm accepts, whatever else it needs."""

    model_config = ConfigDict(extra="forbid")

    task_id: str | None = Field(None, description="Owning task; bare UUIDv4")
    request_id: str | None = Field(None, description="Echoed back for correlation")
    budget_tokens: int | None = Field(None, ge=1, description="Ceiling for this request")
    deadline_ms: int | None = Field(None, ge=1, description="Wall-clock budget")


class ArmResponse(BaseModel):
    """Fields every arm returns, whatever else it produces."""

    model_config = ConfigDict(extra="forbid")

    arm_id: str = Field(..., description="Which arm answered")
    request_id: str = Field(..., description="Correlates with the request")
    usage: UsageReport = Field(..., description="Cumulative cost, including peer calls")
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Computed from observable signals, never a model's self-report",
    )
    produced_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


# ---------------------------------------------------------------------------
# Planner :8001 -- POST /plan
# ---------------------------------------------------------------------------


class PlanStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    step_id: str = Field(..., description="Unique within the plan")
    arm_id: str = Field(..., description="Which arm executes this step")
    instruction: str = Field(..., min_length=1)
    depends_on: list[str] = Field(
        default_factory=list,
        description="step_ids that must complete first. The orchestrator topologically "
        "sorts these and refuses a cycle -- in pure Python, with no model involved.",
    )


class PlanRequest(ArmRequest):
    goal: str = Field(..., min_length=1, max_length=10_000)
    constraints: list[str] = Field(default_factory=list)
    context: str | None = Field(None, max_length=50_000)


class PlanResponse(ArmResponse):
    steps: list[PlanStep] = Field(default_factory=list)
    rationale: str = Field("", description="Why this decomposition")


# ---------------------------------------------------------------------------
# Retriever :8002 -- POST /search
# ---------------------------------------------------------------------------


class SearchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_id: str
    content: str
    score: float = Field(..., ge=0.0, le=1.0, description="Fused rank score")
    source: str = Field("", description="Where it came from")


class SearchRequest(ArmRequest):
    query: str = Field(..., min_length=1)
    top_k: int = Field(10, ge=1, le=100)
    filters: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(ArmResponse):
    results: list[SearchResult] = Field(default_factory=list)
    # The Retriever ranks; the Memory arm stores. Naming the strategy in the response
    # is what lets a ranking regression be attributed to the fusion rather than to the
    # corpus.
    strategy: Literal["bm25", "vector", "fused"] = "fused"


# ---------------------------------------------------------------------------
# Coder :8003 -- POST /code
# ---------------------------------------------------------------------------


class CodeRequest(ArmRequest):
    instruction: str = Field(..., min_length=1)
    language: str = Field("python")
    existing_code: str | None = Field(None, max_length=200_000)
    mode: Literal["generate", "debug", "refactor", "explain"] = "generate"


class CodeResponse(ArmResponse):
    code: str = Field("")
    explanation: str = Field("")
    language: str = Field("python")


# ---------------------------------------------------------------------------
# Judge :8004 -- POST /validate
# ---------------------------------------------------------------------------


class Verdict(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    NEEDS_REVISION = "needs_revision"


class ValidateRequest(ArmRequest):
    content: str = Field(..., min_length=1)
    criteria: list[str] = Field(default_factory=list)
    # `schema` is deterministic jsonschema validation; `criteria` and `quality` are
    # model judgements. `facts` is deliberately absent: verifying a claim means
    # fetching task-supplied URLs from inside an arm, which is an SSRF primitive.
    # Deferred to v1.1 and routed through the retriever instead.
    check: Literal["schema", "criteria", "quality"] = "criteria"
    json_schema: dict[str, Any] | None = Field(None, description="Required when check='schema'")


class ValidateResponse(ArmResponse):
    verdict: Verdict
    score: float = Field(..., ge=0.0, le=1.0)
    issues: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Safety Guardian :8005 -- POST /check
# ---------------------------------------------------------------------------


class CheckRequest(ArmRequest):
    content: str = Field(..., min_length=1)
    direction: Literal["egress"] = Field(
        "egress",
        description="Ingress belongs to the reflex layer. The two gates are split by "
        "traffic direction, and this arm only ever sees output.",
    )


class CheckResponse(ArmResponse):
    allowed: bool
    redacted_content: str = Field("", description="Content with findings redacted")
    findings: list[str] = Field(default_factory=list)
    # PII detection is delegated to the reflex layer rather than duplicated here; a
    # second regex corpus would drift from the first. This records whether that
    # delegation succeeded, because the Guardian fails CLOSED if reflex is down.
    reflex_consulted: bool = True


# ---------------------------------------------------------------------------
# Executor :8006 -- POST /execute
# ---------------------------------------------------------------------------


class ExecuteRequest(ArmRequest):
    # argv only. There is never a shell, so shell metacharacters are structurally
    # irrelevant rather than escaped.
    argv: list[str] = Field(..., min_length=1, description="Command and arguments, unsplit")
    stdin: str | None = None
    timeout_ms: int = Field(30_000, ge=1, le=600_000)
    network: bool = Field(False, description="Off by default; requires an explicit capability")


class ExecuteResponse(ArmResponse):
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    timed_out: bool = False
    duration_ms: int = Field(0, ge=0)
