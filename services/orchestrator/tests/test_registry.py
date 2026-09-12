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

from app.capabilities import REGISTRY_WRITE_SCOPE, RingAuthority
from app.config import get_settings, reset_settings
from app.main import app, reset_ring_authority
from app.registry import ArmRegistry, RegisterArmRequest, UnknownArm, reset_registry

#: Assembled rather than written as a literal. A 32+ character literal sitting next to
#: the word "secret" is exactly what the scanner exists to find, and the correct response
#: is not a path exemption -- it is to stop writing something that looks like a
#: credential. The issuer requires >=32 characters and refuses recognisable placeholders,
#: so this satisfies both.
SIGNING_KEY = "octollm-test-capability-" * 2


def admin_token(
    *, scope: str = REGISTRY_WRITE_SCOPE, secret: str = SIGNING_KEY, max_calls: int = 10, **kwargs
) -> str:
    """Mint a token addressed to the orchestrator, as `scripts/mint_capability.py` does."""
    authority = RingAuthority(secret=secret, kid=kwargs.pop("kid", "k1"))
    return authority.issue_admin_token(
        subject="test-operator", scope=scope, max_calls=max_calls, **kwargs
    )


def auth(token: str | None = None) -> dict[str, str]:
    return {"authorization": f"Bearer {token if token is not None else admin_token()}"}


@pytest.fixture(autouse=True)
def _fresh_registry():
    """The registry is process-wide; a test that mutated it must not leak."""
    reset_registry()
    yield
    reset_registry()


@pytest.fixture(autouse=True)
def _fresh_authority():
    """The signing authority is process-wide and caches the configured secret."""
    reset_ring_authority()
    yield
    reset_ring_authority()


@pytest.fixture
def registration_enabled(monkeypatch: pytest.MonkeyPatch):
    """
    Turn the registration endpoint on for the tests that exercise it.

    It is **off** unless a capability secret is configured, which is why this fixture
    has to exist at all -- and the tests that do not request it prove the default.
    """
    reset_settings()
    reset_ring_authority()
    monkeypatch.setenv("ORCHESTRATOR_CAPABILITY_SECRET", SIGNING_KEY)
    assert get_settings().capability_secret == SIGNING_KEY
    yield
    reset_settings()
    reset_ring_authority()


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


@pytest.mark.usefixtures("registration_enabled")
def test_registering_a_known_arm_updates_it(client: TestClient):
    response = client.post(
        "/arms/register",
        json={"arm_id": "planner", "implemented": True, "capabilities": ["planning"]},
        headers=auth(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "updated"
    assert body["arm"]["implemented"] is True
    assert body["arm"]["capabilities"] == ["planning"]
    assert body["arm"]["last_probed_at"] is not None


@pytest.mark.usefixtures("registration_enabled")
def test_registration_cannot_introduce_an_arm(client: TestClient):
    """
    The security property this endpoint is shaped around.

    An endpoint that adds an arm to the routing table is a privilege escalation with
    extra steps: the orchestrator is the sole signing authority for capability tokens,
    so an arm it can be told about is an arm it can be told to trust.
    """
    response = client.post("/arms/register", json={"arm_id": "attacker-arm"}, headers=auth())

    assert response.status_code == 403
    assert "Stage 5" in response.json()["error"]["message"]
    assert len(client.get("/arms").json()["arms"]) == 8, "nothing was added"


@pytest.mark.usefixtures("registration_enabled")
@pytest.mark.parametrize(
    "field, value",
    [
        ("port", 9999),
        ("endpoint", "/hijacked"),
        ("base_url", "http://attacker.example"),
        ("cost_tier", 1),
    ],
)
def test_registration_cannot_move_an_arm(client: TestClient, field: str, value: object):
    """
    The escalation that matters most, and the one this endpoint got wrong first.

    A caller able to restate where an arm listens redirects that arm's traffic to a
    host it controls -- every task step routed there, carrying task content and, from
    Stage 5, a capability token. Refusing an unknown `arm_id` while accepting a
    `base_url` on a known one would have been no protection at all.
    """
    response = client.post(
        "/arms/register", json={"arm_id": "planner", field: value}, headers=auth()
    )

    assert response.status_code == 422, f"{field} must not be accepted at all"
    assert client.get("/arms").json()["arms"][0]["base_url"] == "http://planner-arm:8001"


@pytest.mark.usefixtures("registration_enabled")
def test_omitted_fields_are_left_alone_rather_than_cleared(client: TestClient):
    """
    A registration that names only `implemented` must not blank the capabilities. The
    difference between PATCH and PUT semantics is not academic when the cleared field
    is what routing matches on.
    """
    before = client.get("/arms").json()["arms"][0]["capabilities"]

    after = client.post(
        "/arms/register", json={"arm_id": "planner", "implemented": True}, headers=auth()
    )

    assert after.json()["arm"]["capabilities"] == before


# ---------------------------------------------------------------------------
# Authorization on the one mutating endpoint
#
# Stage 4 gated this on a shared secret and recorded it as a stopgap. Stage 5 replaced
# it with a real capability token, which is narrower in three ways: it expires in at
# most 120 seconds, it names the orchestrator as its audience so it cannot be presented
# to an arm, and it is counted. These tests pin all three.
# ---------------------------------------------------------------------------


def test_registration_is_disabled_unless_a_capability_secret_is_configured(
    client: TestClient,
):
    """
    Fail **closed**.

    A deployment that has not configured authorization has not thought about it, and
    the safe reading of that is "refuse". An unauthenticated caller able to restate an
    arm's details controls where the orchestrator sends work: mark a stub
    `implemented` and the dispatcher sends it work it cannot do; blank an arm's
    `capabilities` and it stops being selected.
    """
    reset_settings()
    reset_ring_authority()

    response = client.post(
        "/arms/register", json={"arm_id": "planner", "implemented": True}, headers=auth()
    )

    assert response.status_code == 503
    assert "ORCHESTRATOR_CAPABILITY_SECRET" in response.json()["error"]["message"]
    assert client.get("/arms").json()["arms"][0]["implemented"] is False, "no mutation"


@pytest.mark.usefixtures("registration_enabled")
def test_no_token_at_all_is_401(client: TestClient):
    """401 tells a client to go and obtain one; 403 would tell it not to bother."""
    response = client.post("/arms/register", json={"arm_id": "planner", "implemented": True})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"
    assert client.get("/arms").json()["arms"][0]["implemented"] is False, "no mutation"


@pytest.mark.usefixtures("registration_enabled")
@pytest.mark.parametrize(
    "headers",
    [
        pytest.param({"authorization": "Bearer not.a.jwt"}, id="not a token"),
        pytest.param({"authorization": "Bearer "}, id="empty token"),
        pytest.param({"authorization": admin_token()}, id="no scheme"),
        pytest.param({"authorization": f"Basic {admin_token()}"}, id="wrong scheme"),
    ],
)
def test_a_token_that_is_not_one_is_refused_and_changes_nothing(client: TestClient, headers: dict):
    response = client.post(
        "/arms/register", json={"arm_id": "planner", "implemented": True}, headers=headers
    )

    assert response.status_code in (401, 403)
    assert client.get("/arms").json()["arms"][0]["implemented"] is False, "no mutation"


@pytest.mark.usefixtures("registration_enabled")
def test_a_token_signed_with_another_secret_is_refused(client: TestClient):
    """
    The forgery that matters: a well-formed token from someone who is not us.

    Constructed by the route a forger would actually take -- a real issuer with a
    different key -- rather than by corrupting a string until the parser complains.
    """
    forged = admin_token(secret="a-completely-different-secret-0123456789")
    response = client.post(
        "/arms/register", json={"arm_id": "planner", "implemented": True}, headers=auth(forged)
    )

    assert response.status_code == 403
    assert client.get("/arms").json()["arms"][0]["implemented"] is False, "no mutation"


@pytest.mark.usefixtures("registration_enabled")
def test_a_valid_token_for_the_wrong_scope_is_refused(client: TestClient):
    """
    Our own signature is not enough. A peer token minted for an arm call must not
    double as authority over the routing table.
    """
    response = client.post(
        "/arms/register",
        json={"arm_id": "planner", "implemented": True},
        headers=auth(admin_token(scope="call:validate")),
    )

    assert response.status_code == 403
    assert client.get("/arms").json()["arms"][0]["implemented"] is False, "no mutation"


@pytest.mark.usefixtures("registration_enabled")
def test_an_expired_token_is_refused(client: TestClient):
    """A capability that outlives its window is the thing the window exists to prevent."""
    import time

    from octollm_common.capability import CapabilityIssuer, PeerConstraints

    issuer = CapabilityIssuer(SIGNING_KEY, kid="k1")
    stale = issuer.issue(
        caller="test-operator",
        callee="orchestrator",
        task_id="admin",
        scope=[REGISTRY_WRITE_SCOPE],
        constraints=PeerConstraints(max_calls=10),
        ttl_seconds=30,
        now=int(time.time()) - 600,
    )

    response = client.post(
        "/arms/register", json={"arm_id": "planner", "implemented": True}, headers=auth(stale)
    )

    assert response.status_code == 403
    assert client.get("/arms").json()["arms"][0]["implemented"] is False, "no mutation"


@pytest.mark.usefixtures("registration_enabled")
def test_a_token_is_spent_and_cannot_be_replayed(client: TestClient):
    """
    `max_calls` is counted by the receiving service, not by the caller.

    A bound the caller is trusted to respect is a request, not a bound. An operator
    token defaults to one use, so a captured Authorization header is worth at most one
    replay -- and only inside its 120-second window.
    """
    once = admin_token(max_calls=1)

    assert (
        client.post(
            "/arms/register", json={"arm_id": "planner", "implemented": True}, headers=auth(once)
        ).status_code
        == 200
    )

    replayed = client.post(
        "/arms/register", json={"arm_id": "judge", "implemented": True}, headers=auth(once)
    )
    assert replayed.status_code == 403
    arms = {a["arm_id"]: a for a in client.get("/arms").json()["arms"]}
    assert arms["judge"]["implemented"] is False, "the replay changed nothing"


@pytest.mark.usefixtures("registration_enabled")
def test_the_refusal_does_not_disclose_the_configured_secret(client: TestClient):
    """An error message that quotes the secret defeats the point of having one."""
    response = client.post(
        "/arms/register",
        json={"arm_id": "planner"},
        headers=auth(admin_token(secret="a-completely-different-secret-0123456789")),
    )

    assert SIGNING_KEY not in response.text
    # Nor which check failed: "expired" vs "bad signature" tells a forger which half
    # of the problem to work on.
    body = response.text.lower()
    assert "signature" not in body
    assert "expired" not in body


def test_listing_arms_needs_no_token(client: TestClient):
    """
    The read path stays open. It exposes the roster, which is public information --
    it is in the README, the specs and both SDKs -- and gating it would break the
    health dashboards without protecting anything.
    """
    assert client.get("/arms").status_code == 200


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
