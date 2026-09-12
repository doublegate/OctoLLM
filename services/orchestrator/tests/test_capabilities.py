"""
Tests for the orchestrator's capability-signing authority.

The property this file exists for is in
`test_an_arm_cannot_widen_its_own_reach_through_the_registry`: authorization reads the
**static roster**, never the live registry, because the registry carries what each arm
says about itself.

That is the direct application of Stage 4's lesson. The security review there found
that refusing an unknown `arm_id` on `POST /arms/register` while accepting `base_url`
on a known one was the same escalation by a shorter route -- *getting a principle right
in one place is not the same as applying it everywhere it holds.* The registry's
`peers` field is the next place that principle holds.
"""

from __future__ import annotations

import time

import pytest
from octollm_common.capability import (
    MAX_TTL_SECONDS,
    CapabilityConfigError,
    CapabilityDenied,
    CapabilityIssuer,
    CapabilityVerifier,
    InMemoryCallCounter,
)
from octollm_common.roster import SPECS

from app.capabilities import (
    ORCHESTRATOR_AUDIENCE,
    REGISTRY_WRITE_SCOPE,
    RingAuthority,
    UndeclaredEdge,
    scope_for,
)
from app.registry import ArmRegistry, RegisterArmRequest

SIGNING_KEY = "octollm-test-capability-" * 2


@pytest.fixture
def authority() -> RingAuthority:
    return RingAuthority(secret=SIGNING_KEY, kid="k1")


def verifier_for(arm_id: str) -> CapabilityVerifier:
    return CapabilityVerifier({"k1": SIGNING_KEY}, audience=arm_id, counter=InMemoryCallCounter())


# ---------------------------------------------------------------------------
# Fail closed
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "secret", ["", "short", "change_me", "secret"], ids=["empty", "short", "placeholder", "word"]
)
def test_an_unusable_secret_stops_the_authority_from_existing(secret: str) -> None:
    """
    At construction, so a misconfigured deployment fails to start.

    A service that starts and fails on the first real request has already told the
    orchestrator it is healthy.
    """
    with pytest.raises(CapabilityConfigError):
        RingAuthority(secret=secret)


# ---------------------------------------------------------------------------
# The roster is the authorization source
# ---------------------------------------------------------------------------


def test_a_declared_edge_gets_a_token(authority: RingAuthority) -> None:
    """Coder -> Judge is the validation loop the documents name."""
    assert "judge" in SPECS["coder"].peers
    assert authority.issue_peer_token(caller="coder", callee="judge", task_id="t1")


@pytest.mark.parametrize(
    ("caller", "callee"),
    [
        ("coder", "executor"),
        ("judge", "executor"),
        ("planner", "judge"),
        ("safety-guardian", "red-team"),
    ],
)
def test_an_undeclared_edge_is_refused(authority: RingAuthority, caller: str, callee: str) -> None:
    """
    An undeclared edge is unreachable, not merely undocumented.

    This is what bounds lateral movement: a compromised Coder can reach the arms the
    roster says it may reach, and there is no request it can make that widens that.
    """
    assert callee not in SPECS[caller].peers, "fixture assumption: this edge is undeclared"
    with pytest.raises(UndeclaredEdge, match=callee):
        authority.issue_peer_token(caller=caller, callee=callee, task_id="t1")


@pytest.mark.parametrize(
    ("caller", "callee"),
    [("ghost", "judge"), ("coder", "ghost"), ("ghost", "phantom")],
)
def test_an_unknown_arm_is_refused(authority: RingAuthority, caller: str, callee: str) -> None:
    with pytest.raises(UndeclaredEdge):
        authority.issue_peer_token(caller=caller, callee=callee, task_id="t1")


def test_an_arm_cannot_widen_its_own_reach_through_the_registry(
    authority: RingAuthority,
) -> None:
    """
    **The property this module exists to hold.**

    `ArmRegistry` accepts `peers` from an arm's own `/capabilities` response -- it has
    to, since its job is to report what each arm says about itself. That makes
    `registry.get(arm).peers` arm-controlled data.

    A compromised Coder answering its next probe with `peers: ["executor"]` would, if
    the issuer trusted the registry, mint itself a path to the sandbox. So the issuer
    reads the static roster, and this test is the proof: the registry genuinely
    changes, and the answer genuinely does not.
    """
    registry = ArmRegistry()
    registry.register(RegisterArmRequest(arm_id="coder", peers=["executor", "red-team"]))

    # The lie landed in the registry, exactly as an attacker would arrange.
    assert "executor" in registry.get("coder").peers

    # And buys nothing.
    with pytest.raises(UndeclaredEdge):
        authority.issue_peer_token(caller="coder", callee="executor", task_id="t1")
    assert authority.declared_edge("coder", "executor") is False


# ---------------------------------------------------------------------------
# What a minted token actually says
# ---------------------------------------------------------------------------


async def test_a_peer_token_verifies_at_the_callee(authority: RingAuthority) -> None:
    """End to end: what the orchestrator mints is what the Judge will accept."""
    token = authority.issue_peer_token(caller="coder", callee="judge", task_id="t1")
    claims = await verifier_for("judge").verify(
        token, required_scope=scope_for("judge"), task_id="t1"
    )

    assert claims.sub == "coder"
    assert claims.aud == "judge"
    assert claims.task_id == "t1"


async def test_a_peer_token_is_refused_by_any_other_arm(authority: RingAuthority) -> None:
    """
    The audience check is what keeps a grant to call the Judge from being a grant to
    call anything. Asserted against every other arm rather than one, because the one
    that is forgotten is the one that matters.
    """
    token = authority.issue_peer_token(caller="coder", callee="judge", task_id="t1")
    for other in SPECS:
        if other == "judge":
            continue
        with pytest.raises(CapabilityDenied) as exc:
            await verifier_for(other).verify(token)
        assert exc.value.reason == "wrong_audience"


def test_the_scope_is_derived_from_the_roster_endpoint() -> None:
    """
    A hand-written scope table would be a fifth place the API surface is written down,
    and the four that already existed disagreed.
    """
    assert scope_for("judge") == "call:validate"
    assert scope_for("coder") == "call:code"
    assert scope_for("executor") == "call:execute"
    for arm_id, spec in SPECS.items():
        assert scope_for(arm_id) == f"call:{spec.endpoint.lstrip('/')}"


async def test_a_token_is_bound_to_one_task(authority: RingAuthority) -> None:
    token = authority.issue_peer_token(caller="coder", callee="judge", task_id="task-a")
    with pytest.raises(CapabilityDenied) as exc:
        await verifier_for("judge").verify(
            token, required_scope=scope_for("judge"), task_id="task-b"
        )
    assert exc.value.reason == "wrong_task"


async def test_the_call_budget_reaches_the_callee(authority: RingAuthority) -> None:
    verifier = verifier_for("judge")
    token = authority.issue_peer_token(caller="coder", callee="judge", task_id="t1", max_calls=2)
    scope = scope_for("judge")

    await verifier.verify(token, required_scope=scope, task_id="t1")
    await verifier.verify(token, required_scope=scope, task_id="t1")
    with pytest.raises(CapabilityDenied) as exc:
        await verifier.verify(token, required_scope=scope, task_id="t1")
    assert exc.value.reason == "call_budget_exhausted"


def test_the_default_ttl_is_capped_at_the_maximum() -> None:
    """
    A configured TTL above the ceiling is clamped rather than accepted.

    Config is operator input, so the ceiling has to hold here too and not only where
    a caller passes `ttl_seconds` explicitly.
    """
    authority = RingAuthority(secret=SIGNING_KEY, default_ttl_seconds=99_999)
    token = authority.issue_peer_token(caller="coder", callee="judge", task_id="t1")

    import jwt

    claims = jwt.decode(token, SIGNING_KEY, algorithms=["HS256"], audience="judge")
    assert claims["exp"] - claims["iat"] <= MAX_TTL_SECONDS


def test_a_short_lived_token_really_does_expire() -> None:
    """The expiry is real, not merely present in the claims."""
    issuer = CapabilityIssuer(SIGNING_KEY, kid="k1")
    token = issuer.issue(
        caller="coder",
        callee="judge",
        task_id="t1",
        scope=["call:validate"],
        ttl_seconds=1,
        now=int(time.time()) - 120,
    )
    with pytest.raises(CapabilityDenied) as exc:
        import asyncio

        asyncio.run(verifier_for("judge").verify(token))
    assert exc.value.reason == "expired"


# ---------------------------------------------------------------------------
# Admin tokens
# ---------------------------------------------------------------------------


async def test_an_admin_token_is_addressed_to_the_orchestrator(
    authority: RingAuthority,
) -> None:
    token = authority.issue_admin_token(subject="operator", scope=REGISTRY_WRITE_SCOPE)
    claims = await verifier_for(ORCHESTRATOR_AUDIENCE).verify(
        token, required_scope=REGISTRY_WRITE_SCOPE
    )

    assert claims.aud == ORCHESTRATOR_AUDIENCE
    assert claims.sub == "operator"


async def test_an_admin_token_cannot_be_presented_to_an_arm(
    authority: RingAuthority,
) -> None:
    """
    An operator token is authority over the orchestrator, not over the Executor.

    The same audience check that separates the arms separates this, which is why
    administrative authority did not need a second mechanism.
    """
    token = authority.issue_admin_token(subject="operator", scope=REGISTRY_WRITE_SCOPE)
    with pytest.raises(CapabilityDenied) as exc:
        await verifier_for("executor").verify(token)
    assert exc.value.reason == "wrong_audience"


async def test_an_admin_token_defaults_to_a_single_use(authority: RingAuthority) -> None:
    """
    An administrative action is one event.

    A token spendable five times is four more chances for a captured header to be
    replayed by somebody else.
    """
    verifier = verifier_for(ORCHESTRATOR_AUDIENCE)
    token = authority.issue_admin_token(subject="operator", scope=REGISTRY_WRITE_SCOPE)

    await verifier.verify(token, required_scope=REGISTRY_WRITE_SCOPE)
    with pytest.raises(CapabilityDenied) as exc:
        await verifier.verify(token, required_scope=REGISTRY_WRITE_SCOPE)
    assert exc.value.reason == "call_budget_exhausted"


def test_the_authority_exposes_a_verifier_for_its_own_audience(
    authority: RingAuthority,
) -> None:
    assert authority.verifier is not None
