"""
Tests for the Memory arm's HTTP surface.

Against the real app, over a real ASGI transport, with the real capability gate and the
real stores behind it. The parts a caller sees -- status codes, the error envelope, and
whether a token is actually required -- are not observable from the service object.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from octollm_common.capability import PeerConstraints

from tests.conftest import make_artifact

CALLER = "coder"


@pytest.fixture
async def client(service, monkeypatch):
    """
    The real app, with the runtime pointed at the fixtures' stores.

    The lifespan is bypassed rather than run: it would open a second engine and a
    second Qdrant client against the same services, and the point of this file is the
    HTTP layer, not connection management.
    """
    from src import main

    monkeypatch.setattr(main.RUNTIME, "service", service)
    transport = ASGITransport(app=main.app)
    async with AsyncClient(transport=transport, base_url="http://memory") as c:
        yield c


def token(issuer, scope: str, *, clearance: str = "internal", task: str = "task-1") -> str:
    scopes = [scope]
    if clearance:
        scopes.append(f"clearance:{clearance}")
    return issuer.issue(
        caller=CALLER,
        callee="memory",
        task_id=task,
        scope=scopes,
        constraints=PeerConstraints(max_calls=50),
    )


def headers(tok: str, task: str = "task-1") -> dict[str, str]:
    return {"authorization": f"Bearer {tok}", "x-task-id": task}


async def remember(client, issuer, artifact, **kw) -> object:
    return await client.post(
        "/remember",
        json={"artifact": artifact.model_dump(mode="json")},
        headers=headers(token(issuer, "memory:write", **kw)),
    )


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


async def test_health_needs_no_token(client) -> None:
    """
    A health check that needs a credential reports "down" whenever authorization is
    misconfigured, which is a different problem wearing the same signal.
    """
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["arm_id"] == "memory"


async def test_capabilities_needs_no_token(client) -> None:
    """The orchestrator's registry probes this before any token exists."""
    response = await client.get("/capabilities")
    assert response.status_code == 200
    assert response.json()["arm_id"] == "memory"


@pytest.mark.parametrize("path", ["/recall", "/remember"])
async def test_the_write_and_read_paths_require_a_token(client, path) -> None:
    """
    Memory holds every arm's output, so an open recall is a read of the whole system.

    Stage 5's rule is that an arm adopts the gate in the stage that builds it; this is
    that stage, and this is the assertion that it happened.
    """
    response = await client.post(path, json={"query": "x"})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


async def test_a_recall_token_does_not_authorize_a_write(client, issuer, arm_id) -> None:
    """
    Separate scopes, so that reading memory is not also permission to rewrite it.

    A single `call:recall` scope covering both would make every reader an editor of the
    record it reads from.
    """
    artifact = make_artifact(created_by=CALLER)
    response = await client.post(
        "/remember",
        json={"artifact": artifact.model_dump(mode="json")},
        headers=headers(token(issuer, "call:recall")),
    )
    assert response.status_code == 403


async def test_a_token_for_another_arm_is_refused(client, issuer) -> None:
    from octollm_common.capability import CapabilityIssuer

    from tests.conftest import CAPABILITY_SECRET

    other = CapabilityIssuer(CAPABILITY_SECRET, kid="k1").issue(
        caller=CALLER, callee="judge", task_id="task-1", scope=["call:recall"]
    )
    response = await client.post("/recall", json={"query": "x"}, headers=headers(other))
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# Remember
# ---------------------------------------------------------------------------


async def test_remembering_reports_both_stores(client, issuer, qdrant, episodic) -> None:
    artifact = make_artifact(created_by=CALLER, content="def parse(): ...")
    try:
        response = await remember(client, issuer, artifact)

        assert response.status_code == 200
        body = response.json()
        assert body["artifact_id"] == artifact.artifact_id
        assert body["semantic_written"] is True
        assert body["episodic_written"] is True
        assert body["duplicate"] is False
        assert body["arm_id"] == "memory"
    finally:
        name = episodic.collection_for(CALLER)
        if await qdrant.collection_exists(name):
            await qdrant.delete_collection(name)


async def test_the_second_write_of_one_artifact_reports_duplicate(
    client, issuer, qdrant, episodic
) -> None:
    """Not a 409. A redelivery is expected, and the caller needs the fact, not an error."""
    artifact = make_artifact(created_by=CALLER)
    try:
        first = await remember(client, issuer, artifact)
        second = await remember(client, issuer, artifact)

        assert first.json()["duplicate"] is False
        assert second.status_code == 200
        assert second.json()["duplicate"] is True
    finally:
        name = episodic.collection_for(CALLER)
        if await qdrant.collection_exists(name):
            await qdrant.delete_collection(name)


async def test_remember_refuses_an_artifact_whose_task_does_not_match_the_token(
    client, issuer
) -> None:
    """
    `X-Task-Id` matching the token is necessary but not sufficient.

    The artifact's own `provenance.task_id` must also match `claims.task_id`, or a
    holder of a task-1 grant can attribute writes to task-2.
    """
    forged = make_artifact(created_by=CALLER, task_id="task-2")
    response = await client.post(
        "/remember",
        json={"artifact": forged.model_dump(mode="json")},
        headers=headers(token(issuer, "memory:write", task="task-1"), task="task-1"),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_remember_rejects_a_conflicting_duplicate_before_indexing_episodic(
    client, issuer, qdrant, episodic
) -> None:
    """
    A replay with the same `artifact_id` but altered content or sensitivity is rejected.

    Otherwise `EpisodicStore.index()` would overwrite the searchable vector and
    downgrade its clearance label while Postgres kept the original audit row.
    """
    original = make_artifact(
        created_by=CALLER,
        artifact_id="conflict-id-1",
        content="secret rotation key",
        sensitivity="restricted",
    )
    downgraded = make_artifact(
        created_by=CALLER,
        artifact_id="conflict-id-1",
        content="secret rotation key",
        sensitivity="internal",
    )
    try:
        first = await remember(client, issuer, original)
        assert first.status_code == 200

        second = await remember(client, issuer, downgraded)
        assert second.status_code == 409
        assert second.json()["error"]["code"] == "conflict"

        internal = await client.post(
            "/recall",
            json={"query": "secret rotation key", "top_k": 5},
            headers=headers(token(issuer, "call:recall", clearance="internal")),
        )
        assert internal.json()["hits"] == []
        assert internal.json()["withheld"] == 1
    finally:
        name = episodic.collection_for(CALLER)
        if await qdrant.collection_exists(name):
            await qdrant.delete_collection(name)


async def test_an_artifact_can_be_recorded_without_a_vector(client, issuer) -> None:
    """`index_episodic=False` for artifacts not worth embedding, such as an ack."""
    artifact = make_artifact(created_by=CALLER, artifact_type="memory_write_ack", content="")
    response = await client.post(
        "/remember",
        json={"artifact": artifact.model_dump(mode="json"), "index_episodic": False},
        headers=headers(token(issuer, "memory:write")),
    )

    assert response.status_code == 200
    assert response.json()["semantic_written"] is True
    assert response.json()["episodic_written"] is False


# ---------------------------------------------------------------------------
# Recall, and where clearance comes from
# ---------------------------------------------------------------------------


async def test_recall_returns_what_was_remembered(client, issuer, qdrant, episodic) -> None:
    try:
        await remember(client, issuer, make_artifact(created_by=CALLER, content="the fox"))

        response = await client.post(
            "/recall",
            json={"query": "fox", "top_k": 5},
            headers=headers(token(issuer, "call:recall")),
        )

        assert response.status_code == 200
        body = response.json()
        assert body["scope"] == "episodic"
        assert len(body["hits"]) == 1
        assert body["hits"][0]["content"] == "the fox"
    finally:
        name = episodic.collection_for(CALLER)
        if await qdrant.collection_exists(name):
            await qdrant.delete_collection(name)


async def test_clearance_comes_from_the_token_not_the_request(
    client, issuer, qdrant, episodic
) -> None:
    """
    **The property this endpoint is shaped around.**

    A caller cannot ask for a higher clearance, because `RecallRequest` has no field
    for it and the extra key is rejected outright. Clearance is read from the grant the
    orchestrator signed -- the same reasoning that makes peer authorization read the
    static roster rather than an arm's own claim about itself.
    """
    try:
        await remember(
            client, issuer, make_artifact(created_by=CALLER, content="a", sensitivity="restricted")
        )
        await remember(
            client, issuer, make_artifact(created_by=CALLER, content="b", sensitivity="internal")
        )

        # An internal token sees one and is told one was withheld.
        internal = await client.post(
            "/recall",
            json={"query": "notes", "top_k": 10},
            headers=headers(token(issuer, "call:recall", clearance="internal")),
        )
        assert internal.status_code == 200
        assert internal.json()["withheld"] == 1
        assert [h["sensitivity"] for h in internal.json()["hits"]] == ["internal"]

        # Asking for more in the body is refused by the schema, not honoured.
        forged = await client.post(
            "/recall",
            json={"query": "notes", "top_k": 10, "max_sensitivity": "restricted"},
            headers=headers(token(issuer, "call:recall", clearance="internal")),
        )
        assert forged.status_code == 422, "the request model accepted a clearance field"

        # A token that actually grants it sees both.
        cleared = await client.post(
            "/recall",
            json={"query": "notes", "top_k": 10},
            headers=headers(token(issuer, "call:recall", clearance="restricted")),
        )
        assert cleared.json()["withheld"] == 0
        assert len(cleared.json()["hits"]) == 2
    finally:
        name = episodic.collection_for(CALLER)
        if await qdrant.collection_exists(name):
            await qdrant.delete_collection(name)


async def test_a_token_granting_no_clearance_gets_the_safer_default(
    client, issuer, qdrant, episodic
) -> None:
    """
    Absent a clearance scope, the caller is `internal` -- not `restricted`.

    A token that says nothing about clearance must not thereby receive the highest one.
    """
    try:
        await remember(
            client, issuer, make_artifact(created_by=CALLER, content="x", sensitivity="restricted")
        )

        response = await client.post(
            "/recall",
            json={"query": "x", "top_k": 5},
            headers=headers(token(issuer, "call:recall", clearance="")),
        )

        assert response.status_code == 200
        assert response.json()["hits"] == []
        assert response.json()["withheld"] == 1
    finally:
        name = episodic.collection_for(CALLER)
        if await qdrant.collection_exists(name):
            await qdrant.delete_collection(name)


async def test_recall_defaults_to_the_callers_own_memory(client, issuer, qdrant, episodic) -> None:
    """
    An arm recalling its own experience is the common case, so it names no arm at all.

    The default is the token's `sub`, which the caller cannot forge.
    """
    try:
        await remember(client, issuer, make_artifact(created_by=CALLER, content="mine"))

        response = await client.post(
            "/recall", json={"query": "mine"}, headers=headers(token(issuer, "call:recall"))
        )

        assert [h["created_by"] for h in response.json()["hits"]] == [CALLER]
    finally:
        name = episodic.collection_for(CALLER)
        if await qdrant.collection_exists(name):
            await qdrant.delete_collection(name)


async def test_confidence_is_zero_when_nothing_was_recalled(client, issuer) -> None:
    """
    A recall over an empty index is not a confident answer.

    Reporting 1.0 for "I found nothing" would mislead a caller deciding whether to
    trust it -- and `confidence` is computed from observable signals everywhere in this
    system, never asserted.
    """
    response = await client.post(
        "/recall",
        json={"query": "nothing is stored"},
        headers=headers(token(issuer, "call:recall")),
    )
    assert response.status_code == 200
    assert response.json()["hits"] == []
    assert response.json()["confidence"] == 0.0


async def test_the_readiness_probe_reports_both_stores(client) -> None:
    """
    An arm that says ready while its database is unreachable is the same failure as a
    green check over a suite that never ran.
    """
    response = await client.get("/ready")
    body = response.json()

    assert response.status_code == 200
    assert body["arm_id"] == "memory"
    assert body["checks"]["postgres"] is True
    assert body["checks"]["qdrant"] is True
    assert "artifacts" in body["checks"]


async def test_an_unconfigured_deployment_refuses_rather_than_allows(client, monkeypatch) -> None:
    """
    No capability secret means 503 on the gated routes, and a healthy `/health`.

    "Authorization is not set up" and "this service is down" are different problems
    with different fixes, and an arm that could not serve `/health` without a secret
    would report the wrong one.
    """
    from src import config, main

    config.reset_settings()
    monkeypatch.delenv("MEMORY_CAPABILITY_SECRET", raising=False)
    # The policies cache their verifier after first use; clear it so this exercises
    # the unconfigured path rather than a previously built verifier.
    monkeypatch.setattr(main.RECALL_POLICY, "_verifier", None)

    try:
        assert (await client.get("/health")).status_code == 200
        response = await client.post(
            "/recall", json={"query": "x"}, headers={"authorization": "Bearer x", "x-task-id": "t"}
        )
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "unavailable"
    finally:
        config.reset_settings()
        monkeypatch.setattr(main.RECALL_POLICY, "_verifier", None)
