"""
Tests for the arm registry and its two endpoints.

Both SDKs have shipped a `listArms()` call since Phase 0 against an endpoint that did
not exist -- and against two different paths. These tests pin the path that won, the
shape it returns, and the one thing registration must never be able to do.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.registry import ArmRegistry, RegisterArmRequest, UnknownArm, reset_registry


@pytest.fixture(autouse=True)
def _fresh_registry():
    """The registry is process-wide; a test that mutated it must not leak."""
    reset_registry()
    yield
    reset_registry()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /arms
# ---------------------------------------------------------------------------


def test_listing_arms_returns_the_whole_roster(client: TestClient):
    body = client.get("/arms").json()

    assert [arm["arm_id"] for arm in body["arms"]] == [
        "planner",
        "retriever",
        "coder",
        "judge",
        "safety-guardian",
        "executor",
        "memory",
        "red-team",
    ]


def test_the_unbuilt_arms_are_listed_rather_than_omitted(client: TestClient):
    """
    A roster that silently omits the arms nobody has written is how a system comes to
    be described by its aspirations. Memory and Red Team appear, each naming its stage.
    """
    arms = {arm["arm_id"]: arm for arm in client.get("/arms").json()["arms"]}

    assert arms["memory"]["implemented"] is False
    assert arms["memory"]["implemented_in_stage"] == 6
    assert arms["red-team"]["implemented_in_stage"] == 11


def test_an_unprobed_arm_reports_unavailable_with_no_probe_timestamp(client: TestClient):
    """Not "healthy" by default. Nothing has checked, and the registry says so."""
    planner = client.get("/arms").json()["arms"][0]

    assert planner["status"] == "unavailable"
    assert planner["last_probed_at"] is None


def test_the_listed_schemas_come_from_the_shared_contract_models(client: TestClient):
    """
    Generated from `octollm_common.models.contracts` -- the same classes the arms use
    as their FastAPI models. A hand-written schema here would be a claim; this is the
    model itself, so it cannot describe a request the arm would reject.
    """
    planner = client.get("/arms").json()["arms"][0]

    assert "goal" in planner["input_schema"]["properties"]
    assert "steps" in planner["output_schema"]["properties"]


def test_an_arm_with_no_contract_yet_publishes_an_empty_schema(client: TestClient):
    """
    Memory has no contract models until Stage 6. An invented schema would be worse
    than an empty one, because a client can act on it.
    """
    arms = {arm["arm_id"]: arm for arm in client.get("/arms").json()["arms"]}

    assert arms["memory"]["input_schema"] == {}


def test_endpoint_is_a_path_and_base_url_is_where_the_arm_listens(client: TestClient):
    """
    Both SDKs documented `endpoint` as "Kubernetes service endpoint", meaning a URL,
    while every arm returns a path. Two meanings under one name is how a client comes
    to request `http://planner-arm:8001http://planner-arm:8001/plan`.
    """
    planner = client.get("/arms").json()["arms"][0]

    assert planner["endpoint"] == "/plan"
    assert planner["base_url"] == "http://planner-arm:8001"
    assert planner["port"] == 8001


def test_the_response_is_an_object_not_a_bare_array(client: TestClient):
    """A top-level array cannot grow a field without breaking every client."""
    assert isinstance(client.get("/arms").json(), dict)


# ---------------------------------------------------------------------------
# POST /arms/register
# ---------------------------------------------------------------------------


def test_registering_a_known_arm_updates_it(client: TestClient):
    response = client.post(
        "/arms/register",
        json={"arm_id": "planner", "implemented": True, "capabilities": ["planning"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "updated"
    assert body["arm"]["implemented"] is True
    assert body["arm"]["capabilities"] == ["planning"]
    assert body["arm"]["last_probed_at"] is not None


def test_registration_cannot_introduce_an_arm(client: TestClient):
    """
    The security property this endpoint is shaped around.

    An endpoint that adds an arm to the routing table is a privilege escalation with
    extra steps: the orchestrator is the sole signing authority for capability tokens,
    so an arm it can be told about is an arm it can be told to trust.
    """
    response = client.post("/arms/register", json={"arm_id": "attacker-arm"})

    assert response.status_code == 403
    assert "Stage 5" in response.json()["error"]["message"]
    assert len(client.get("/arms").json()["arms"]) == 8, "nothing was added"


def test_an_arm_cannot_move_its_own_port_or_endpoint(client: TestClient):
    """
    Those are roster facts. An arm that could restate them could redirect its own
    traffic, which makes the roster advisory and the registry authoritative in the
    wrong direction.
    """
    response = client.post("/arms/register", json={"arm_id": "planner", "port": 9999})

    assert response.status_code == 422, "the field is not accepted at all"


def test_omitted_fields_are_left_alone_rather_than_cleared(client: TestClient):
    """
    A registration that names only `implemented` must not blank the capabilities. The
    difference between PATCH and PUT semantics is not academic when the cleared field
    is what routing matches on.
    """
    before = client.get("/arms").json()["arms"][0]["capabilities"]

    after = client.post("/arms/register", json={"arm_id": "planner", "implemented": True})

    assert after.json()["arm"]["capabilities"] == before


# ---------------------------------------------------------------------------
# Probing
# ---------------------------------------------------------------------------


async def test_a_probe_records_what_the_arm_said(monkeypatch: pytest.MonkeyPatch):
    registry = ArmRegistry(host_template="http://{service}:{port}")

    async def fake_get(self, url: str, **kwargs):
        return httpx.Response(
            200,
            json={
                "arm_id": "planner",
                "capabilities": ["planning", "decomposition"],
                "implemented": True,
                "peers": ["judge"],
                # Roster facts an arm does not get to restate about itself.
                "port": 9999,
                "endpoint": "/hijacked",
            },
            request=httpx.Request("GET", url),
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    arms = {arm.arm_id: arm for arm in await registry.refresh()}

    assert arms["planner"].status == "healthy"
    assert arms["planner"].implemented is True
    assert arms["planner"].peers == ["judge"]
    assert arms["planner"].port == 8001, "an arm cannot restate its own port"
    assert arms["planner"].endpoint == "/plan"


async def test_a_failed_probe_marks_the_arm_unavailable_without_removing_it(
    monkeypatch: pytest.MonkeyPatch,
):
    """
    "This arm is down" and "this arm does not exist" are different facts, and the
    registry is the only place that can tell them apart. Dropping the entry would
    collapse them.
    """
    registry = ArmRegistry()

    async def fake_get(self, url: str, **kwargs):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    arms = await registry.refresh()

    assert len(arms) == 8
    assert all(arm.status == "unavailable" for arm in arms)
    assert all(arm.last_probed_at is not None for arm in arms)


async def test_a_probe_returning_malformed_json_is_a_failure_not_a_crash(
    monkeypatch: pytest.MonkeyPatch,
):
    registry = ArmRegistry()

    async def fake_get(self, url: str, **kwargs):
        return httpx.Response(
            200, content=b"<html>gateway</html>", request=httpx.Request("GET", url)
        )

    monkeypatch.setattr(httpx.AsyncClient, "get", fake_get)

    arms = await registry.refresh()

    assert all(arm.status == "unavailable" for arm in arms)


def test_listing_does_not_probe(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    """
    This endpoint is polled. Eight HTTP requests per poll would make the registry a
    source of load rather than of answers, so probing is opt-in.
    """

    async def explode(self, url: str, **kwargs):
        raise AssertionError("GET /arms must not probe without ?refresh=true")

    monkeypatch.setattr(httpx.AsyncClient, "get", explode)

    assert client.get("/arms").status_code == 200


# ---------------------------------------------------------------------------
# The registry object
# ---------------------------------------------------------------------------


def test_getting_an_unknown_arm_raises():
    with pytest.raises(UnknownArm):
        ArmRegistry().get("planer")


def test_registering_an_unknown_arm_raises():
    with pytest.raises(UnknownArm):
        ArmRegistry().register(RegisterArmRequest(arm_id="nope"))


def test_the_host_template_is_configurable():
    """Kubernetes DNS differs from compose; a hardcoded hostname would spread."""
    registry = ArmRegistry(host_template="http://{service}.octollm.svc:{port}")

    assert registry.get("coder").base_url == "http://coder-arm.octollm.svc:8003"
