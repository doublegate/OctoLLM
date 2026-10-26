"""
Tests for the ring consumer: Memory's other write path.

This is the first place the Neural Ring carries real work, so these run against a real
Redis, a real Postgres and a real Qdrant at once. The properties asserted here are
exactly the ones a double cannot show: that an unacknowledged message redelivers, that
an acknowledged one does not, and that a crash between the write and the acknowledgement
costs a duplicate detection rather than a duplicate row.

`drain_once` is driven explicitly rather than starting the background loop. A test that
races a `while True` is a test that fails on a slow machine and passes on review.
"""

from __future__ import annotations

import os
import uuid

import pytest
from octollm_common.models.provenance import Artifact
from octollm_common.ring import RingConsumer, RingPublisher, stream_key

from tests.conftest import make_artifact

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

redis_asyncio = pytest.importorskip("redis.asyncio", reason="redis-py is not installed")


@pytest.fixture
async def redis():
    client = redis_asyncio.from_url(REDIS_URL)
    try:
        await client.ping()
    except Exception as exc:  # noqa: BLE001
        await client.aclose()
        pytest.skip(f"no Redis at {REDIS_URL}: {exc}")
    yield client
    await client.aclose()


@pytest.fixture
def artifact_type() -> str:
    """
    A unique artifact type per test, so each gets its own stream.

    Namespaced rather than FLUSHDB'd: a test run must not be able to empty a Redis a
    developer is using for something else.
    """
    return f"test_artifact_{uuid.uuid4().hex[:10]}"


@pytest.fixture
def specs(artifact_type):
    """A producer and a Memory whose topology is namespaced to this test."""
    from octollm_common.roster import spec_for

    memory = spec_for("memory").model_copy(
        update={"subscribes": [artifact_type], "publishes": ["memory_write_ack"]}
    )
    producer = spec_for("coder").model_copy(update={"publishes": [artifact_type]})
    return producer, memory


@pytest.fixture
async def consumer(redis, service, specs, artifact_type):
    from src.consumer import ArtifactConsumer

    producer_spec, memory_spec = specs
    ring_consumer = RingConsumer(redis, memory_spec, consumer_name="test-memory")
    art = ArtifactConsumer(
        service=service,
        consumer=ring_consumer,
        publisher=RingPublisher(redis, memory_spec),
        block_ms=300,
    )
    await ring_consumer.ensure_groups()
    yield art
    await redis.delete(stream_key(artifact_type), stream_key("memory_write_ack"))


@pytest.fixture
async def publish(redis, specs, artifact_type):
    producer_spec, _ = specs
    publisher = RingPublisher(redis, producer_spec)

    async def _publish(**kwargs) -> Artifact:
        artifact = make_artifact(created_by="coder", **kwargs)
        artifact = artifact.model_copy(update={"artifact_type": artifact_type})
        # Re-validate so the content hash is recomputed for the changed model.
        artifact = Artifact.model_validate(artifact.model_dump())
        await publisher.publish(artifact)
        return artifact

    return _publish


async def cleanup_collection(qdrant, episodic) -> None:
    name = episodic.collection_for("coder")
    if await qdrant.collection_exists(name):
        await qdrant.delete_collection(name)


async def test_an_artifact_on_the_ring_reaches_memory(
    consumer, publish, semantic, qdrant, episodic
) -> None:
    """
    Nobody called Memory. That is the point of the ring.

    A producer publishes what it made and does not need to know a memory exists.
    """
    try:
        artifact = await publish(content="def parse(): ...")

        stored = await consumer.drain_once()

        assert stored == 1
        row = await semantic.provenance_for(artifact.artifact_id)
        assert row is not None
        assert row.arm_id == "coder"
    finally:
        await cleanup_collection(qdrant, episodic)


async def test_a_handled_message_is_acknowledged(
    consumer, publish, redis, artifact_type, qdrant, episodic
) -> None:
    try:
        await publish()
        await consumer.drain_once()

        pending = await redis.xpending(stream_key(artifact_type), consumer._consumer.group)
        assert pending["pending"] == 0
    finally:
        await cleanup_collection(qdrant, episodic)


async def test_a_redelivered_artifact_is_counted_as_a_duplicate_not_stored_twice(
    consumer, publish, semantic, redis, artifact_type, qdrant, episodic
) -> None:
    """
    The whole reason `remember` is idempotent.

    Publishing the same artifact twice is what a producer retrying after a timeout
    does, and the record must not double.
    """
    try:
        artifact = await publish(content="once")
        await consumer.drain_once()

        # The identical artifact arrives again, as a retry would deliver it.
        from octollm_common.ring import RingPublisher
        from octollm_common.roster import spec_for

        producer = spec_for("coder").model_copy(update={"publishes": [artifact_type]})
        await RingPublisher(redis, producer).publish(artifact)

        await consumer.drain_once()

        assert await semantic.count() == 1
        assert consumer.stored == 1
        assert consumer.duplicates == 1
    finally:
        await cleanup_collection(qdrant, episodic)


async def test_storing_publishes_an_acknowledgement_on_the_ring(
    consumer, publish, redis, qdrant, episodic
) -> None:
    """
    `memory_write_ack` lets a producer establish that something reached memory without
    querying memory -- and it is declared in the roster, so the orchestrator sees the edge.
    """
    try:
        artifact = await publish()
        await consumer.drain_once()

        entries = await redis.xrange(stream_key("memory_write_ack"))
        assert len(entries) == 1
        payload = Artifact.from_json(entries[0][1][b"artifact"])
        assert payload.artifact_type == "memory_write_ack"
        assert payload.content == artifact.artifact_id
        assert payload.provenance.created_by == "memory"
        assert payload.provenance.promoted_from == artifact.artifact_id
    finally:
        await cleanup_collection(qdrant, episodic)


async def test_the_acknowledgement_inherits_the_artifacts_sensitivity(
    consumer, publish, redis, qdrant, episodic
) -> None:
    """
    Which restricted artifacts exist is itself information the diode is meant to bound.

    An acknowledgement that carried a restricted artifact's id at `internal` would leak
    the existence of the thing it acknowledges.
    """
    try:
        await publish(sensitivity="restricted")
        await consumer.drain_once()

        entries = await redis.xrange(stream_key("memory_write_ack"))
        ack = Artifact.from_json(entries[0][1][b"artifact"])
        assert str(ack.provenance.sensitivity) == "restricted"
    finally:
        await cleanup_collection(qdrant, episodic)


async def test_a_failed_write_leaves_the_message_pending_for_redelivery(
    consumer, publish, redis, artifact_type, monkeypatch, qdrant, episodic
) -> None:
    """
    Not acknowledged, so Redis redelivers.

    Acknowledging a message whose write failed would lose the artifact silently, which
    is the opposite of the trade at-least-once delivery was chosen for.
    """
    try:
        await publish()

        async def boom(*args, **kwargs):
            raise RuntimeError("postgres is unreachable")

        monkeypatch.setattr(consumer._service, "remember", boom)
        stored = await consumer.drain_once()

        assert stored == 0
        assert consumer.failed == 1
        pending = await redis.xpending(stream_key(artifact_type), consumer._consumer.group)
        assert pending["pending"] == 1, "a failed write was acknowledged"
    finally:
        await cleanup_collection(qdrant, episodic)


async def test_an_incomplete_episodic_write_leaves_the_message_pending_for_redelivery(
    consumer, publish, redis, artifact_type, monkeypatch, qdrant, episodic
) -> None:
    """
    When Qdrant or the embedding provider fails during `remember`, `episodic_written` is
    `False`. The ring consumer must NOT acknowledge the message until the vector write
    succeeds, because Postgres stores only the hash, not the content needed to rebuild it.
    """
    try:
        artifact = await publish(content="needs vector indexing")
        real_index = episodic.index
        calls = {"n": 0}

        async def flaky_index(art):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("qdrant temporarily unavailable")
            await real_index(art)

        monkeypatch.setattr(episodic, "index", flaky_index)

        stored_first = await consumer.drain_once()
        assert stored_first == 0
        assert consumer.failed == 1
        pending = await redis.xpending(stream_key(artifact_type), consumer._consumer.group)
        assert pending["pending"] == 1, "partial write without episodic vector was acknowledged"

        # Next drain recovers the pending message, repairs the episodic vector, and acks.
        await consumer.drain_once()
        pending_after = await redis.xpending(stream_key(artifact_type), consumer._consumer.group)
        assert pending_after["pending"] == 0
        hits, _ = await episodic.search(
            arm_id="coder",
            query="needs vector indexing",
            limit=5,
            clearance=artifact.provenance.sensitivity,
        )
        assert [h["artifact_id"] for h in hits] == [artifact.artifact_id]
    finally:
        await cleanup_collection(qdrant, episodic)


async def test_an_empty_ring_is_not_an_error(consumer) -> None:
    """The idle path. A consumer that raised on quiet would restart forever."""
    assert await consumer.drain_once() == 0


async def test_a_batch_is_drained_in_one_pass(
    consumer, publish, semantic, qdrant, episodic
) -> None:
    try:
        for i in range(5):
            await publish(content=f"artifact {i}")

        stored = await consumer.drain_once()

        assert stored == 5
        assert await semantic.count() == 5
    finally:
        await cleanup_collection(qdrant, episodic)


async def test_a_failing_acknowledgement_does_not_fail_the_write(
    consumer, publish, semantic, monkeypatch, qdrant, episodic
) -> None:
    """
    Best-effort, because the artifact is already durably stored.

    Failing the drain would redeliver an artifact that does not need storing again, and
    an unreachable ack stream would stall ingestion behind it.
    """
    try:
        await publish()

        async def boom(*args, **kwargs):
            raise RuntimeError("ack stream unavailable")

        monkeypatch.setattr(consumer._publisher, "publish", boom)
        stored = await consumer.drain_once()

        assert stored == 1
        assert await semantic.count() == 1
    finally:
        await cleanup_collection(qdrant, episodic)


async def test_stats_report_what_the_consumer_actually_did(
    consumer, publish, qdrant, episodic
) -> None:
    """
    Exposed on `/ready`, so that "the consumer is running" and "the consumer is doing
    anything" are never the same signal.
    """
    try:
        await publish()
        await consumer.drain_once()

        stats = consumer.stats()
        assert stats["ring_stored"] == 1
        assert stats["ring_duplicates"] == 0
        assert stats["ring_failed"] == 0
    finally:
        await cleanup_collection(qdrant, episodic)
