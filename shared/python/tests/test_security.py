"""
Tests for `RequireCapability`, the callee-side HTTP gate.

These run against a real FastAPI app over a real ASGI transport rather than calling the
dependency directly. The dependency in isolation cannot show that the app returns the
shared error envelope, that the status code distinguishes 401 from 403, or that the
denial reason stays out of the body -- and those are the parts a client sees.
"""

from __future__ import annotations

import httpx
import pytest
from fastapi import Depends, FastAPI
from octollm_common.capability import (
    MIN_SECRET_LENGTH,
    CapabilityClaims,
    CapabilityIssuer,
    CapabilityVerifier,
    InMemoryCallCounter,
    PeerConstraints,
)
from octollm_common.errors import install_error_handlers
from octollm_common.security import CapabilityPolicy, RequireCapability, bearer_token

SECRET = "a" * MIN_SECRET_LENGTH


@pytest.fixture
def issuer() -> CapabilityIssuer:
    return CapabilityIssuer(SECRET, kid="k1")


def build_app(*, scope: str | None = "call:validate", bind_task: bool = True) -> FastAPI:
    app = FastAPI()
    install_error_handlers(app)
    verifier = CapabilityVerifier({"k1": SECRET}, audience="judge", counter=InMemoryCallCounter())
    policy = CapabilityPolicy(verifier, scope=scope, bind_task=bind_task)

    @app.post("/validate")
    async def validate(claims: CapabilityClaims = Depends(RequireCapability(policy))) -> dict:
        # Echoes what the gate proved, which is what a real handler would attribute
        # its work to -- never what the request body claims about itself.
        return {"caller": claims.sub, "task_id": claims.task_id, "jti": claims.jti}

    return app


async def call(
    app: FastAPI, *, token: str | None = None, task_id: str | None = "task-1"
) -> httpx.Response:
    headers = {}
    if token is not None:
        headers["authorization"] = f"Bearer {token}"
    if task_id is not None:
        headers["x-task-id"] = task_id
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://arm") as client:
        return await client.post("/validate", json={}, headers=headers)


async def test_a_valid_token_reaches_the_handler(issuer: CapabilityIssuer) -> None:
    token = issuer.issue(caller="coder", callee="judge", task_id="task-1", scope=["call:validate"])
    response = await call(build_app(), token=token)

    assert response.status_code == 200
    assert response.json()["caller"] == "coder"
    assert response.json()["task_id"] == "task-1"


async def test_no_token_is_401_so_a_client_knows_to_obtain_one() -> None:
    response = await call(build_app())
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_a_bad_token_is_403_so_a_client_does_not_spin(issuer: CapabilityIssuer) -> None:
    """
    Retrying with the same rejected token cannot succeed.

    A client that reads 401 as "refresh and retry" would loop forever against a token
    that is simply for the wrong audience.
    """
    token = issuer.issue(caller="coder", callee="executor", task_id="task-1", scope=["x"])
    response = await call(build_app(), token=token)
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


@pytest.mark.parametrize(
    ("caller", "callee", "scope", "task", "sent_task"),
    [
        ("coder", "executor", ["call:validate"], "task-1", "task-1"),
        ("coder", "judge", ["exec:offensive"], "task-1", "task-1"),
        ("coder", "judge", ["call:validate"], "task-1", "task-2"),
    ],
    ids=["wrong-audience", "wrong-scope", "wrong-task"],
)
async def test_the_denial_reason_never_reaches_the_caller(
    issuer: CapabilityIssuer,
    caller: str,
    callee: str,
    scope: list[str],
    task: str,
    sent_task: str,
) -> None:
    """
    "Expired" versus "wrong audience" tells a forger which half to work on.

    Every denial returns the same generic message; the specific reason is logged.
    """
    token = issuer.issue(caller=caller, callee=callee, task_id=task, scope=scope)
    response = await call(build_app(), token=token, task_id=sent_task)

    assert response.status_code == 403
    body = response.text.lower()
    for leak in ("audience", "scope", "expired", "signature", "issuer", "jti"):
        assert leak not in body, f"denial body leaked {leak!r}: {response.text}"


async def test_a_non_bearer_scheme_is_treated_as_no_token(issuer: CapabilityIssuer) -> None:
    app = build_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://arm") as client:
        response = await client.post(
            "/validate",
            json={},
            headers={"authorization": "Basic dXNlcjpwYXNz", "x-task-id": "task-1"},
        )
    assert response.status_code == 401


async def test_task_binding_is_required_when_the_policy_says_so(
    issuer: CapabilityIssuer,
) -> None:
    """
    Without the header there is nothing to bind the token to.

    Admitting the request "because the token is otherwise fine" would make a live token
    for one task usable against every other task running at that moment.
    """
    token = issuer.issue(caller="coder", callee="judge", task_id="task-1", scope=["call:validate"])
    response = await call(build_app(), token=token, task_id=None)
    assert response.status_code == 403


async def test_a_route_can_opt_out_of_task_binding(issuer: CapabilityIssuer) -> None:
    """Used by endpoints that are not task-scoped, such as the orchestrator's registry."""
    token = issuer.issue(
        caller="operator", callee="judge", task_id="task-1", scope=["call:validate"]
    )
    response = await call(build_app(bind_task=False), token=token, task_id=None)
    assert response.status_code == 200


async def test_the_call_budget_is_enforced_over_http(issuer: CapabilityIssuer) -> None:
    """The bound holds across requests, not merely within one verifier call."""
    app = build_app()
    token = issuer.issue(
        caller="coder",
        callee="judge",
        task_id="task-1",
        scope=["call:validate"],
        constraints=PeerConstraints(max_calls=2),
    )
    assert (await call(app, token=token)).status_code == 200
    assert (await call(app, token=token)).status_code == 200
    assert (await call(app, token=token)).status_code == 403


def test_bearer_token_extraction() -> None:
    class FakeRequest:
        def __init__(self, header: str) -> None:
            self.headers = {"authorization": header}

    assert bearer_token(FakeRequest("Bearer abc")) == "abc"  # type: ignore[arg-type]
    assert bearer_token(FakeRequest("bearer abc")) == "abc"  # type: ignore[arg-type]
    assert bearer_token(FakeRequest("Basic abc")) == ""  # type: ignore[arg-type]
    assert bearer_token(FakeRequest("")) == ""  # type: ignore[arg-type]
