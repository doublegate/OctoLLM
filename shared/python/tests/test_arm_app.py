"""
Tests for the arm application factory.

Eight services are built by `create_arm_app`, so every property asserted here is
asserted for all eight at once -- and a regression here is a regression in all eight.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from octollm_common import ArmSpec, create_arm_app
from octollm_common.models.contracts import PlanRequest, PlanResponse, UsageReport

SPEC = ArmSpec(
    arm_id="planner",
    name="Planner",
    description="Decomposes a goal into a dependency-ordered plan.",
    port=8001,
    endpoint="/plan",
    capabilities=["planning", "decomposition"],
    cost_tier=2,
    implemented=False,
    implemented_in_stage=8,
    publishes=["plan"],
    subscribes=["goal"],
    peers=["judge"],
)


@pytest.fixture
def client() -> TestClient:
    """An arm with no handler -- which is every arm until Stage 8."""
    return TestClient(create_arm_app(SPEC, request_model=PlanRequest))


# ---------------------------------------------------------------------------
# The four endpoints every arm serves
# ---------------------------------------------------------------------------


def test_health_is_served(client: TestClient):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["arm_id"] == "planner"


def test_ready_states_that_the_arm_is_not_implemented(client: TestClient):
    """
    "The container is up" and "the arm does anything" must never be the same signal.

    Five arm images crash-looped for the life of this repository while the compose
    file, the diagrams and both SDKs described a stack that had never once run. The
    opposite failure -- a container reporting ready while implementing nothing -- is
    just as misleading, and this field is what prevents it.
    """
    body = client.get("/ready").json()

    assert body["ready"] is True
    assert body["implemented"] is False


def test_capabilities_returns_the_whole_spec_including_ring_topology(client: TestClient):
    """
    The orchestrator's registry reads this. `publishes`/`subscribes`/`peers` ride
    along on a call it was already making, so the full Neural Ring topology arrives
    over a protocol that already exists -- and a peer token is only ever issued for
    an edge named here.
    """
    body = client.get("/capabilities").json()

    assert body["arm_id"] == "planner"
    assert body["port"] == 8001
    assert body["endpoint"] == "/plan"
    assert body["publishes"] == ["plan"]
    assert body["subscribes"] == ["goal"]
    assert body["peers"] == ["judge"]


def test_metrics_are_well_formed_prometheus_exposition(client: TestClient):
    """
    Empty but well-formed rather than absent: Prometheus scrapes from the first
    second, and a 404 in the scrape log is noise that hides a real one.
    """
    text = client.get("/metrics").text

    assert "# HELP octollm_arm_implemented" in text
    assert "# TYPE octollm_arm_implemented gauge" in text
    assert 'octollm_arm_implemented{arm_id="planner"} 0' in text


def test_metrics_report_one_for_an_implemented_arm():
    async def handler(request: PlanRequest) -> PlanResponse:  # pragma: no cover - unused
        raise NotImplementedError

    spec = SPEC.model_copy(update={"implemented": True})
    client = TestClient(create_arm_app(spec, handler=handler, response_model=PlanResponse))

    assert 'octollm_arm_implemented{arm_id="planner"} 1' in client.get("/metrics").text


# ---------------------------------------------------------------------------
# The unimplemented endpoint
# ---------------------------------------------------------------------------


def test_an_unimplemented_arm_returns_501_naming_the_stage(client: TestClient):
    """
    Not a plausible fake.

    A stub that answers convincingly makes an unimplemented arm indistinguishable
    from a working one, which is the exact failure this repository is being dug out
    of. A 501 carrying the stage number is a fact a caller can act on.
    """
    response = client.post("/plan", json={"goal": "assess the repository"})

    assert response.status_code == 501
    error = response.json()["error"]
    assert error["code"] == "not_implemented"
    assert "Stage 8" in error["message"]
    assert error["details"]["implemented_in_stage"] == 8


def test_the_openapi_document_describes_what_the_endpoint_will_accept(client: TestClient):
    """
    A 501 whose request schema is `{}` teaches a caller nothing about what to send
    once it works. Both SDKs are generated from these documents.
    """
    schema = client.get("/openapi.json").json()
    body = schema["paths"]["/plan"]["post"]["requestBody"]

    assert "goal" in body["content"]["application/json"]["schema"]["properties"]


def test_a_handler_is_served_at_the_declared_endpoint():
    """The spec's `endpoint` is the single source of the path -- not a literal."""

    async def handler(request: PlanRequest) -> PlanResponse:
        return PlanResponse(
            arm_id="planner",
            request_id="req-1",
            usage=UsageReport(provider="fake", model="fake-1"),
            confidence=0.5,
            steps=[],
            rationale=f"echo: {request.goal}",
        )

    client = TestClient(create_arm_app(SPEC, handler=handler, response_model=PlanResponse))

    response = client.post("/plan", json={"goal": "assess the repository"})

    assert response.status_code == 200
    assert response.json()["rationale"] == "echo: assess the repository"


# ---------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------


def test_an_inbound_request_id_is_echoed_back(client: TestClient):
    """So a task's spans stitch across arms instead of restarting at each hop."""
    response = client.get("/health", headers={"x-request-id": "abc-123"})

    assert response.headers["x-request-id"] == "abc-123"


def test_a_request_id_is_minted_when_absent(client: TestClient):
    """An error a user can quote back is the difference from a guessing game."""
    response = client.get("/health")

    assert len(response.headers["x-request-id"]) >= 8


def test_the_501_body_carries_the_inbound_request_id(client: TestClient):
    response = client.post("/plan", json={"goal": "g"}, headers={"x-request-id": "abc-123"})

    assert response.json()["error"]["request_id"] == "abc-123"


# ---------------------------------------------------------------------------
# The spec itself
# ---------------------------------------------------------------------------


def test_a_spec_with_an_unknown_field_is_rejected():
    """
    `extra="forbid"`. A typo in an arm's declaration must be a startup failure, not a
    field the registry silently never sees.
    """
    with pytest.raises(ValueError, match="extra_forbidden|Extra inputs"):
        ArmSpec(
            arm_id="planner",
            name="Planner",
            description="d",
            port=8001,
            endpoint="/plan",
            implemented_in_stage=8,
            subscribe=["goal"],  # the field is `subscribes`
        )


def test_a_spec_rejects_an_impossible_port():
    with pytest.raises(ValueError, match="less than or equal to 65535"):
        ArmSpec(
            arm_id="planner",
            name="Planner",
            description="d",
            port=70000,
            endpoint="/plan",
            implemented_in_stage=8,
        )


def test_the_ring_topology_defaults_to_empty_rather_than_permissive():
    """
    An arm that declares nothing may call nothing. Default-deny is the only safe
    default for a field that gates token issuance.
    """
    spec = ArmSpec(
        arm_id="x", name="X", description="d", port=8009, endpoint="/x", implemented_in_stage=8
    )

    assert spec.peers == []
    assert spec.publishes == []
    assert spec.subscribes == []


# ---------------------------------------------------------------------------
# Errors from inside a handler
# ---------------------------------------------------------------------------


def test_a_handler_http_exception_gets_the_common_envelope():
    async def handler(request: PlanRequest) -> PlanResponse:
        raise HTTPException(status_code=429, detail="too many plans")

    client = TestClient(create_arm_app(SPEC, handler=handler, response_model=PlanResponse))

    response = client.post("/plan", json={"goal": "g"})

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "rate_limited"
    assert response.json()["error"]["message"] == "too many plans"
