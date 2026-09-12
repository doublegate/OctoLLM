"""
The eight arms, declared once.

`ARCHITECTURE.md` tabled six arms, the Project Overview named seven ("examples"), six
had directories, and every arm's OpenAPI spec named its neighbour's port. Four sources
disagreeing about what the system is made of is not a documentation problem; it is a
missing definition. This is that definition.

Each arm's `src/main.py` reads its spec from here, the orchestrator's registry reads
the whole roster from here, and `scripts/ci/check_port_map.py` checks this against the
Dockerfiles and the compose file -- which are what actually bind a socket, and
therefore win over anything written down.

Two of the eight do not exist yet as services: **Memory** (Stage 6) and **Red Team**
(Stage 11). They are listed anyway, with `implemented: False` and the stage that
builds them, because a roster that silently omits the unbuilt arms is how a system
comes to be described by its aspirations. `GET /arms` reports them as `unavailable`,
which is the truth.
"""

from __future__ import annotations

from .app import ArmSpec

__all__ = ["ROSTER", "SPECS", "arm_base_url", "spec_for"]


ROSTER: tuple[ArmSpec, ...] = (
    ArmSpec(
        arm_id="planner",
        name="Planner",
        description="Decomposes a goal into a dependency-ordered plan of arm calls.",
        port=8001,
        endpoint="/plan",
        capabilities=["task_planning", "goal_decomposition"],
        cost_tier=3,
        implemented=False,
        implemented_in_stage=8,
        publishes=["plan"],
        subscribes=["task"],
        peers=["executor", "retriever"],
    ),
    ArmSpec(
        arm_id="retriever",
        name="Retriever",
        description="Ranks candidates: BM25, vector search, and reciprocal-rank fusion.",
        port=8002,
        endpoint="/search",
        capabilities=["search", "ranking", "rank_fusion"],
        cost_tier=2,
        implemented=False,
        implemented_in_stage=8,
        publishes=["search_results"],
        subscribes=["query"],
        # Memory owns storage; the Retriever is a pure ranker over its corpus.
        peers=["memory"],
    ),
    ArmSpec(
        arm_id="coder",
        name="Coder",
        description="Generates, debugs, refactors and explains code.",
        port=8003,
        endpoint="/code",
        capabilities=["code_generation", "debugging", "refactoring"],
        cost_tier=4,
        implemented=False,
        implemented_in_stage=8,
        publishes=["code"],
        subscribes=["plan_step"],
        # The validation loop the docs name: Coder proposes, Judge validates, without
        # an orchestrator hop between each iteration.
        peers=["judge", "retriever"],
    ),
    ArmSpec(
        arm_id="judge",
        name="Judge",
        description="Validates output against a schema, criteria, or quality bar.",
        port=8004,
        endpoint="/validate",
        capabilities=["validation", "quality_scoring"],
        cost_tier=2,
        implemented=False,
        implemented_in_stage=8,
        publishes=["verdict"],
        subscribes=["code", "answer"],
        peers=["retriever"],
    ),
    ArmSpec(
        arm_id="safety-guardian",
        name="Safety Guardian",
        description="Egress gate: screens arm output, synthesized answers and generated code.",
        port=8005,
        endpoint="/check",
        capabilities=["egress_filtering", "pii_redaction", "policy"],
        cost_tier=1,
        implemented=False,
        implemented_in_stage=8,
        publishes=["egress_verdict"],
        subscribes=["answer", "code"],
        # PII detection is delegated to the reflex layer rather than duplicated here;
        # a second regex corpus would drift from the first.
        peers=["reflex"],
    ),
    ArmSpec(
        arm_id="executor",
        name="Executor",
        description="Runs allowlisted commands in a hardened, per-task sandbox.",
        port=8006,
        endpoint="/execute",
        capabilities=["command_execution", "sandboxing"],
        cost_tier=1,
        implemented=False,
        implemented_in_stage=9,
        publishes=["execution_result"],
        subscribes=["plan_step"],
        peers=[],
    ),
    ArmSpec(
        arm_id="memory",
        name="Memory / Curator",
        description="Episodic and semantic memory, provenance, and decision traces.",
        port=8007,
        endpoint="/recall",
        capabilities=["episodic_memory", "semantic_memory", "provenance"],
        cost_tier=1,
        implemented=False,
        implemented_in_stage=6,
        publishes=["memory_write_ack"],
        subscribes=["artifact"],
        peers=[],
    ),
    ArmSpec(
        arm_id="red-team",
        name="Red Team",
        description="External recon and attack simulation, inside a signed engagement scope.",
        port=8008,
        endpoint="/probe",
        capabilities=["recon", "vulnerability_analysis", "attack_simulation"],
        cost_tier=4,
        implemented=False,
        implemented_in_stage=11,
        publishes=["finding"],
        subscribes=["engagement"],
        # It never opens a socket itself: every probe is delegated to the executor's
        # hardened sandbox, which keeps the dangerous primitive in the memory-safe
        # language and means there is only one sandbox to harden.
        peers=["executor", "safety-guardian"],
    ),
)

#: By `arm_id`, which is how every other component refers to an arm.
SPECS: dict[str, ArmSpec] = {spec.arm_id: spec for spec in ROSTER}


def spec_for(arm_id: str) -> ArmSpec:
    """Look up one arm. Raises `KeyError` for an unknown id, which is the point."""
    return SPECS[arm_id]


def arm_base_url(arm_id: str, *, host_template: str = "http://{service}:{port}") -> str:
    """
    Where an arm listens inside the compose network.

    The compose service name is the arm id plus `-arm`, so `safety-guardian` is
    `safety-guardian-arm`. The template is a parameter rather than a literal because
    the same roster has to address arms under Kubernetes DNS later, and a hardcoded
    hostname is how a service discovery scheme ends up spread across nine files.
    """
    spec = SPECS[arm_id]
    return host_template.format(service=f"{arm_id}-arm", port=spec.port)
