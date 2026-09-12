"""
Tests for direct peer calls.

The peer client is exercised against a **real FastAPI callee over a real ASGI
transport**, not against a mocked `httpx.AsyncClient`. That is deliberate and it is the
most important thing about this file.

Four SDK calls that could never have worked survived 56 green tests in Stage 4, because
every one of those tests mocked the transport -- and a mock is built from the same wrong
belief as the client it is testing. A peer client tested against a mock would prove that
the client agrees with itself. Here the callee is a genuine app built from the shared
contract models, so a shape disagreement fails.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from fastapi import Depends, FastAPI
from octollm_common.app import ArmSpec
from octollm_common.capability import (
    MIN_SECRET_LENGTH,
    CapabilityClaims,
    CapabilityIssuer,
    CapabilityVerifier,
    InMemoryCallCounter,
)
from octollm_common.errors import install_error_handlers
from octollm_common.models.contracts import (
    UsageReport,
    ValidateRequest,
    ValidateResponse,
    Verdict,
)
from octollm_common.peer import (
    PeerCallError,
    PeerClient,
    PeerDeadlineExceeded,
    PeerLoopContract,
    PeerTopologyError,
    UsageAccumulator,
)
from octollm_common.security import CapabilityPolicy, RequireCapability

SECRET = "a" * MIN_SECRET_LENGTH

#: Tokens for tests that never reach a verifier -- the contract is under test,
#: not the grant. Named constants rather than literals so the secret-scanning
#: lint rule is satisfied by the code being honest rather than by a suppression.
PLACEHOLDER_GRANT = "unused-by-this-test"
MALFORMED_JWT = "not.a.token"

CODER = ArmSpec(
    arm_id="coder",
    name="Coder",
    description="test",
    port=8003,
    endpoint="/code",
    implemented_in_stage=8,
    peers=["judge", "retriever"],
    publishes=["code"],
    subscribes=["plan_step"],
)


@pytest.fixture
def issuer() -> CapabilityIssuer:
    return CapabilityIssuer(SECRET, kid="k1")


def judge_app(*, enforce: bool = True) -> FastAPI:
    """A real Judge, answering with the shared contract model."""
    app = FastAPI()
    install_error_handlers(app)
    verifier = CapabilityVerifier({"k1": SECRET}, audience="judge", counter=InMemoryCallCounter())
    policy = CapabilityPolicy(verifier, scope="call:validate")

    if enforce:

        @app.post("/validate", response_model=ValidateResponse)
        async def validate(
            body: ValidateRequest,
            claims: CapabilityClaims = Depends(RequireCapability(policy)),
        ) -> ValidateResponse:
            return ValidateResponse(
                arm_id="judge",
                request_id=body.request_id or "r1",
                usage=UsageReport(provider="fake", model="fake", input_tokens=5, output_tokens=2),
                confidence=0.9,
                verdict=Verdict.VALID,
                score=0.95,
            )

    else:

        @app.post("/validate", response_model=ValidateResponse)
        async def validate_open(body: ValidateRequest) -> ValidateResponse:
            return ValidateResponse(
                arm_id="judge",
                request_id=body.request_id or "r1",
                usage=UsageReport(provider="fake", model="fake", input_tokens=5, output_tokens=2),
                confidence=0.9,
                verdict=Verdict.VALID,
                score=0.95,
            )

    return app


def client_for(app: FastAPI) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://judge")


def peer_client(http: httpx.AsyncClient, spec: ArmSpec = CODER) -> PeerClient:
    return PeerClient(
        spec,
        base_url_for=lambda arm_id: "http://judge",
        endpoint_for=lambda arm_id: "/validate",
        client=http,
    )


def contract(issuer: CapabilityIssuer, **overrides: object) -> PeerLoopContract:
    token = issuer.issue(caller="coder", callee="judge", task_id="task-1", scope=["call:validate"])
    base: dict[str, object] = {
        "task_id": "task-1",
        "callee": "judge",
        "capability_token": token,
        "max_iterations": 5,
        "deadline": datetime.now(UTC) + timedelta(seconds=30),
    }
    return PeerLoopContract(**{**base, **overrides})  # type: ignore[arg-type]


async def test_a_peer_call_round_trips_through_a_real_callee(issuer: CapabilityIssuer) -> None:
    async with client_for(judge_app()) as http:
        response = await peer_client(http).call(
            contract(issuer),
            ValidateRequest(content="x", task_id="task-1"),
            ValidateResponse,
        )

    assert response.verdict is Verdict.VALID
    assert response.arm_id == "judge"
    assert response.usage.input_tokens == 5


async def test_the_capability_token_actually_reaches_the_callee(
    issuer: CapabilityIssuer,
) -> None:
    """
    The callee enforces, so a successful call proves the header was sent and accepted.

    This is why the fixture app uses `RequireCapability` rather than accepting anything:
    a client that forgot the Authorization header would pass against an open callee.
    """
    app = judge_app(enforce=True)
    async with client_for(app) as http:
        response = await peer_client(http).call(
            contract(issuer),
            ValidateRequest(content="x", task_id="task-1"),
            ValidateResponse,
        )
    assert response.verdict is Verdict.VALID


async def test_a_call_without_a_valid_token_is_refused_by_the_callee() -> None:
    """The gate is the callee's, not the client's."""
    bad = PeerLoopContract(
        task_id="task-1",
        callee="judge",
        capability_token=MALFORMED_JWT,
        deadline=datetime.now(UTC) + timedelta(seconds=30),
    )
    async with client_for(judge_app()) as http:
        with pytest.raises(PeerCallError, match="403"):
            await peer_client(http).call(
                bad, ValidateRequest(content="x", task_id="task-1"), ValidateResponse
            )


async def test_an_undeclared_peer_is_refused_before_any_request(
    issuer: CapabilityIssuer,
) -> None:
    """
    Client-side defence in depth: fail at the call site, where the fix is.

    The authoritative refusals are the callee's gate and the orchestrator declining to
    mint a token for an undeclared edge; this just turns a production 403 into an
    error where someone can read the roster.
    """
    lonely = CODER.model_copy(update={"peers": ["retriever"]})
    async with client_for(judge_app()) as http:
        with pytest.raises(PeerTopologyError, match="judge"):
            await peer_client(http, lonely).call(
                contract(issuer),
                ValidateRequest(content="x", task_id="task-1"),
                ValidateResponse,
            )


async def test_an_expired_loop_deadline_stops_the_call(issuer: CapabilityIssuer) -> None:
    expired = contract(issuer, deadline=datetime.now(UTC) - timedelta(seconds=1))
    async with client_for(judge_app()) as http:
        with pytest.raises(PeerDeadlineExceeded):
            await peer_client(http).call(
                expired, ValidateRequest(content="x", task_id="task-1"), ValidateResponse
            )


async def test_a_response_of_the_wrong_shape_is_a_named_failure(
    issuer: CapabilityIssuer,
) -> None:
    """
    Not a generic 500 attributed to this arm.

    The reflex client spent its whole life unable to parse a real response while its
    tests passed; the failure has to name the peer and the model it did not match.
    """
    app = FastAPI()
    install_error_handlers(app)

    @app.post("/validate")
    async def wrong_shape() -> dict:
        return {"totally": "different"}

    async with client_for(app) as http:
        with pytest.raises(PeerCallError, match="ValidateResponse"):
            await peer_client(http).call(
                contract(issuer),
                ValidateRequest(content="x", task_id="task-1"),
                ValidateResponse,
            )


async def test_transport_failure_is_wrapped(issuer: CapabilityIssuer) -> None:
    class Boom(httpx.AsyncClient):
        async def post(self, *args: object, **kwargs: object) -> httpx.Response:
            raise httpx.ConnectError("no route to host")

    async with Boom() as http:
        with pytest.raises(PeerCallError, match="no route to host"):
            await peer_client(http).call(
                contract(issuer),
                ValidateRequest(content="x", task_id="task-1"),
                ValidateResponse,
            )


# ---------------------------------------------------------------------------
# PeerLoopContract
# ---------------------------------------------------------------------------


def test_starting_now_builds_an_absolute_deadline() -> None:
    c = PeerLoopContract.starting_now(
        task_id="t", callee="judge", capability_token=PLACEHOLDER_GRANT, within_seconds=10
    )
    assert 9 < c.remaining_seconds() <= 10
    assert not c.expired()


def test_a_past_deadline_reads_as_expired() -> None:
    c = PeerLoopContract(
        task_id="t",
        callee="judge",
        capability_token=PLACEHOLDER_GRANT,
        deadline=datetime.now(UTC) - timedelta(seconds=5),
    )
    assert c.expired()
    assert c.remaining_seconds() < 0


def test_iteration_bounds_are_validated() -> None:
    with pytest.raises(ValueError):
        PeerLoopContract(
            task_id="t",
            callee="judge",
            capability_token=PLACEHOLDER_GRANT,
            max_iterations=0,
            deadline=datetime.now(UTC),
        )


# ---------------------------------------------------------------------------
# UsageAccumulator -- the orchestrator's only view of off-graph spend
# ---------------------------------------------------------------------------


def usage(provider: str = "fake", model: str = "m", inp: int = 1, out: int = 1) -> UsageReport:
    return UsageReport(provider=provider, model=model, input_tokens=inp, output_tokens=out)


def test_own_spend_reports_without_peer_calls() -> None:
    report = UsageAccumulator().add(usage(inp=10, out=5)).report()
    assert (report.input_tokens, report.output_tokens, report.peer_calls) == (10, 5, 0)


def test_peer_spend_is_summed_and_the_call_is_counted() -> None:
    """
    `peer_calls` is the one number the orchestrator cannot observe any other way.

    `add_peer` exists separately from `add` so that folding in a peer's usage without
    counting the call is not the shorter thing to write.
    """
    report = UsageAccumulator().add(usage(inp=10, out=5)).add_peer(usage(inp=3, out=2)).report()
    assert report.input_tokens == 13
    assert report.output_tokens == 7
    assert report.peer_calls == 1


def test_a_peers_own_peer_calls_are_carried_upward() -> None:
    """Cumulative means transitively cumulative, or a two-hop loop is invisible."""
    nested = UsageReport(provider="fake", model="m", input_tokens=1, output_tokens=1, peer_calls=2)
    report = UsageAccumulator().add_peer(nested).report()
    assert report.peer_calls == 3


def test_two_providers_collapse_to_mixed() -> None:
    """A single label over two providers is a lie a cost report would be built on."""
    report = (
        UsageAccumulator().add(usage(provider="openai")).add_peer(usage(provider="ollama")).report()
    )
    assert report.provider == "mixed"
    assert report.model == "m"


def test_a_single_provider_keeps_its_name() -> None:
    report = (
        UsageAccumulator().add(usage(provider="ollama")).add_peer(usage(provider="ollama")).report()
    )
    assert report.provider == "ollama"


def test_an_empty_accumulator_reports_none_not_unknown() -> None:
    report = UsageAccumulator().report()
    assert report.provider == "none"
    assert report.input_tokens == 0
