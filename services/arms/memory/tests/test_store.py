"""
Tests for the semantic store: the knowledge graph and the provenance log, in Postgres.

Against a real Postgres, because everything asserted here is a property of the engine:
`ON CONFLICT DO NOTHING` against a named unique constraint, JSONB round-tripping, and
`TIMESTAMPTZ`. SQLite has none of those, and a suite that passed against it would be
testing an agreement with a substitute.
"""

from __future__ import annotations

from datetime import UTC, datetime

from octollm_common.models.provenance import (
    InputSource,
    ModelInfo,
    Transformation,
    ValidationStatus,
)

from tests.conftest import make_artifact


async def test_remembering_an_artifact_records_its_provenance(semantic) -> None:
    artifact = make_artifact(created_by="coder", task_id="task-7")

    assert await semantic.remember(artifact) is True

    row = await semantic.provenance_for(artifact.artifact_id)
    assert row is not None
    assert row.arm_id == "coder"
    assert row.task_id == "task-7"
    assert row.action_type == "code"
    assert row.content_sha256 == artifact.content_sha256


async def test_the_second_delivery_of_one_artifact_is_reported_not_raised(semantic) -> None:
    """
    Ring delivery is at-least-once, so a redelivery is normal operation.

    Without the unique constraint and the upsert this would either raise
    `IntegrityError` -- the `store_task_result` defect, which turned a resumed graph
    into a permanently stuck task -- or silently double the record.
    """
    artifact = make_artifact(created_by="coder")

    assert await semantic.remember(artifact) is True
    assert await semantic.remember(artifact) is False
    assert await semantic.remember(artifact) is False

    assert await semantic.count() == 1


async def test_a_redelivery_does_not_overwrite_the_original_record(semantic) -> None:
    """
    `DO NOTHING`, not `DO UPDATE`.

    Provenance records what happened. A later copy of an artifact carrying a different
    producer must not rewrite the audit trail of the original -- that would make the
    log editable by anyone who can replay a message.
    """
    original = make_artifact(created_by="coder", artifact_id="fixed-id", task_id="task-1")
    await semantic.remember(original)

    impostor = make_artifact(created_by="red-team", artifact_id="fixed-id", task_id="task-999")
    assert await semantic.remember(impostor) is False

    row = await semantic.provenance_for("fixed-id")
    assert row is not None
    assert row.arm_id == "coder", "the audit trail was rewritten by a replay"
    assert row.task_id == "task-1"


async def test_sensitivity_is_stored_as_the_producer_labelled_it(semantic) -> None:
    """The diode is only enforceable if the label survives the write."""
    artifact = make_artifact(created_by="red-team", sensitivity="restricted")
    await semantic.remember(artifact)

    row = await semantic.provenance_for(artifact.artifact_id)
    assert row is not None
    assert row.sensitivity == "restricted"


async def test_the_full_provenance_envelope_round_trips_through_jsonb(semantic) -> None:
    """
    Every field, not a representative one.

    The envelope is what an audit reads; a field that silently fails to serialise is
    one an incident review will not have.
    """
    artifact = make_artifact(created_by="coder")
    artifact.provenance.trace_id = "trace-abc"
    artifact.provenance.engagement_id = "eng-1"
    artifact.provenance.parent_task_id = "task-0"
    artifact.provenance.promoted_from = "art-0"
    artifact.provenance.input_sources = [
        InputSource(source_id="d1", source_type="memory", relevance_score=0.9)
    ]
    artifact.provenance.transformations = [
        Transformation(step=1, operation="generate", tool="coder_v1")
    ]
    artifact.provenance.model_info = ModelInfo(model_name="fake-1", provider="fake", tokens_used=42)
    artifact.provenance.validation_status = ValidationStatus(
        validated=True, validator="judge", confidence=0.9, checks_passed=["syntax"]
    )

    await semantic.remember(artifact)
    row = await semantic.provenance_for(artifact.artifact_id)

    assert row is not None
    details = row.action_details
    assert details["trace_id"] == "trace-abc"
    assert details["engagement_id"] == "eng-1"
    assert details["parent_task_id"] == "task-0"
    assert details["promoted_from"] == "art-0"
    assert details["input_sources"][0]["source_id"] == "d1"
    assert details["transformations"][0]["operation"] == "generate"
    assert details["model_info"]["tokens_used"] == 42
    assert row.result["validated"] is True
    assert row.result["validator"] == "judge"


async def test_timestamps_keep_their_timezone(semantic) -> None:
    """
    A provenance record whose time has no zone cannot be ordered against another host's.

    The design document specifies a naive `TIMESTAMP`; this schema uses `TIMESTAMPTZ`
    and that difference is deliberate, so it is asserted rather than assumed.
    """
    artifact = make_artifact(created_by="coder")
    await semantic.remember(artifact)

    row = await semantic.provenance_for(artifact.artifact_id)
    assert row is not None
    assert row.timestamp.tzinfo is not None
    assert abs((row.timestamp - datetime.now(UTC)).total_seconds()) < 60


async def test_an_unknown_artifact_has_no_provenance(semantic) -> None:
    assert await semantic.provenance_for("never-stored") is None


async def test_counting_an_empty_store_is_zero_not_an_error(semantic) -> None:
    assert await semantic.count() == 0


# ---------------------------------------------------------------------------
# Knowledge graph
# ---------------------------------------------------------------------------


async def test_an_entity_is_matched_on_type_and_name(semantic) -> None:
    """
    Identity in the graph is what a thing is plus what it is called.

    Without that, ingesting the same tool twice produces two nodes and every
    relationship built on either is half the truth.
    """
    first = await semantic.upsert_entity(
        entity_type="tool", name="nmap", properties={"version": "7.94"}
    )
    second = await semantic.upsert_entity(
        entity_type="tool", name="nmap", properties={"category": "scanner"}
    )

    assert first.id == second.id
    assert second.properties == {"version": "7.94", "category": "scanner"}


async def test_the_same_name_under_a_different_type_is_a_different_entity(semantic) -> None:
    tool = await semantic.upsert_entity(entity_type="tool", name="curl")
    concept = await semantic.upsert_entity(entity_type="concept", name="curl")
    assert tool.id != concept.id


async def test_entities_can_be_related(semantic) -> None:
    scanner = await semantic.upsert_entity(entity_type="tool", name="nmap")
    target = await semantic.upsert_entity(entity_type="host", name="example.test")

    edge = await semantic.relate(
        from_entity_id=scanner.id,
        to_entity_id=target.id,
        relationship_type="scanned",
        properties={"ports": [80, 443]},
    )

    assert edge.relationship_type == "scanned"
    assert edge.properties["ports"] == [80, 443]


async def test_deleting_an_entity_cascades_to_its_relationships(semantic, session_factory) -> None:
    """
    `ON DELETE CASCADE`, as the design document specifies.

    An edge pointing at a deleted node is a dangling reference the graph cannot answer
    a query about, and it would accumulate silently.
    """
    from sqlalchemy import delete, func, select
    from src.models import Entity, Relationship

    a = await semantic.upsert_entity(entity_type="tool", name="a")
    b = await semantic.upsert_entity(entity_type="tool", name="b")
    await semantic.relate(from_entity_id=a.id, to_entity_id=b.id, relationship_type="uses")

    async with session_factory() as session:
        await session.execute(delete(Entity).where(Entity.id == a.id))
        await session.commit()
        remaining = await session.scalar(select(func.count()).select_from(Relationship))

    assert remaining == 0


async def test_a_completed_task_is_recorded(semantic, session_factory) -> None:
    """
    `task_history` exists because Stage 7's `memory_write` node writes to it.

    Exercised now rather than left until then: a table nothing can write to is exactly
    the kind of claim this repository is being dug out of.
    """
    from sqlalchemy import select
    from src.models import TaskHistory

    await semantic.record_task(
        task_id="task-42",
        goal="scan the lab",
        plan={"steps": [{"arm_id": "executor"}]},
        results={"findings": 3},
        success=True,
        duration_ms=1234,
        cost_tokens=987,
    )

    async with session_factory() as session:
        row = (
            await session.execute(select(TaskHistory).where(TaskHistory.task_id == "task-42"))
        ).scalar_one()

    assert row.success is True
    assert row.duration_ms == 1234
    assert row.cost_tokens == 987
    assert row.plan["steps"][0]["arm_id"] == "executor"
    assert row.results["findings"] == 3
