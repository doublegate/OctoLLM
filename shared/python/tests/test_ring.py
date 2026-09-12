"""
Tests for the Neural Ring.

**These run against a real Redis**, not a fake one. The topology checks would pass
against any object with an `xadd` method, but the things worth knowing about a stream
transport -- that a consumer group survives a restart, that an unacknowledged message
redelivers, that `mkstream` lets a consumer start before its producer -- are properties
of Redis, and a fake would simply implement whatever this module already assumes.

That is the same trap as mocking the transport in an SDK test: the double is built from
the same belief as the code, so agreement between them proves nothing. Seventeen
Redis-backed Rust tests in this repository were `#[ignore]`d and had never executed
anywhere, which is how `token_bucket.lua` reached production unrun.

Skipped when no Redis is reachable, and **CI runs them** -- `test-shared` has a
`redis:8-alpine` service, so a skip locally is never a skip in the gate.
"""

from __future__ import annotations

import os
import uuid

import pytest
from octollm_common.app import ArmSpec
from octollm_common.models.provenance import Artifact, Provenance
from octollm_common.ring import (
    RING_PREFIX,
    RingConsumer,
    RingPublisher,
    RingTopologyError,
    stream_key,
)

redis_asyncio = pytest.importorskip("redis.asyncio", reason="redis-py is not installed")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")


CODER = ArmSpec(
    arm_id="coder",
    name="Coder",
    description="test",
    port=8003,
    endpoint="/code",
    implemented_in_stage=8,
    publishes=["code"],
    subscribes=["plan_step"],
    peers=["judge"],
)

JUDGE = ArmSpec(
    arm_id="judge",
    name="Judge",
    description="test",
    port=8004,
    endpoint="/validate",
    implemented_in_stage=8,
    publishes=["verdict"],
    subscribes=["code"],
    peers=[],
)


@pytest.fixture
async def redis():
    """
    A live client, or skip.

    Every test namespaces its artifact types with a uuid rather than calling FLUSHDB,
    so a developer running this against a Redis that holds something else does not lose
    it -- and so two tests running concurrently cannot see each other's streams.
    """
    client = redis_asyncio.from_url(REDIS_URL, decode_responses=False)
    try:
        await client.ping()
    except Exception as exc:  # noqa: BLE001 - any connection failure is a skip
        await client.aclose()
        pytest.skip(f"no Redis at {REDIS_URL}: {exc}")
    yield client
    await client.aclose()


@pytest.fixture
def artifact_type() -> str:
    return f"test_{uuid.uuid4().hex[:12]}"


def specs_for(artifact_type: str) -> tuple[ArmSpec, ArmSpec]:
    """Producer and consumer wired to a namespaced type."""
    producer = CODER.model_copy(update={"publishes": [artifact_type]})
    consumer = JUDGE.model_copy(update={"subscribes": [artifact_type]})
    return producer, consumer


def make_artifact(artifact_type: str, *, content: str = "def hello(): ...") -> Artifact:
    return Artifact(
        artifact_id=str(uuid.uuid4()),
        artifact_type=artifact_type,
        content=content,
        provenance=Provenance(created_by="coder", task_id="task-1"),
    )


async def cleanup(redis, artifact_type: str) -> None:
    await redis.delete(stream_key(artifact_type))


# ---------------------------------------------------------------------------
# Topology -- checked without touching Redis
# ---------------------------------------------------------------------------


async def test_an_arm_cannot_publish_a_type_it_does_not_declare(redis) -> None:
    """
    The orchestrator learns the topology from `publishes`/`subscribes`.

    An arm emitting a type outside its declaration is emitting onto an edge nobody
    reviewed and the orchestrator cannot see.
    """
    publisher = RingPublisher(redis, CODER)
    with pytest.raises(RingTopologyError, match="verdict"):
        await publisher.publish(
            Artifact(
                artifact_id="a1",
                artifact_type="verdict",
                content="",
                provenance=Provenance(created_by="coder", task_id="t"),
            )
        )


async def test_an_arm_cannot_publish_another_arms_provenance(redis) -> None:
    """
    Provenance that does not match the publisher is worse than none, because it will
    be believed -- and the whole audit trail is built on `created_by`.
    """
    publisher = RingPublisher(redis, CODER)
    forged = Artifact(
        artifact_id="a1",
        artifact_type="code",
        content="",
        provenance=Provenance(created_by="judge", task_id="t"),
    )
    with pytest.raises(ValueError, match="judge"):
        await publisher.publish(forged)


async def test_a_consumer_with_no_subscriptions_reads_nothing(redis) -> None:
    """An empty `streams` dict is an error in redis-py, not an empty read."""
    silent = JUDGE.model_copy(update={"subscribes": []})
    consumer = RingConsumer(redis, silent, consumer_name="c1")
    await consumer.ensure_groups()
    assert await consumer.consume(block_ms=10) == []


# ---------------------------------------------------------------------------
# Delivery, against real Redis
# ---------------------------------------------------------------------------


async def test_an_artifact_published_is_an_artifact_delivered(redis, artifact_type) -> None:
    producer, consumer_spec = specs_for(artifact_type)
    try:
        consumer = RingConsumer(redis, consumer_spec, consumer_name="c1")
        await consumer.ensure_groups()

        original = make_artifact(artifact_type)
        await RingPublisher(redis, producer).publish(original)

        messages = await consumer.consume(block_ms=500)
        assert len(messages) == 1
        assert messages[0].artifact.artifact_id == original.artifact_id
        assert messages[0].artifact.content == original.content
        assert messages[0].artifact_type == artifact_type
        # The envelope survives the round trip intact, hash included.
        assert messages[0].artifact.content_sha256 == original.content_sha256
        assert messages[0].artifact.provenance.task_id == "task-1"
    finally:
        await cleanup(redis, artifact_type)


async def test_a_consumer_can_start_before_any_producer(redis, artifact_type) -> None:
    """
    `mkstream=True`, or the startup order of two independent services is load-bearing.

    Without it the consumer raises NOGROUP against a stream that does not exist yet,
    and whether the deployment works depends on which container happened to win.
    """
    _, consumer_spec = specs_for(artifact_type)
    try:
        consumer = RingConsumer(redis, consumer_spec, consumer_name="c1")
        await consumer.ensure_groups()  # no producer has ever written
        assert await consumer.consume(block_ms=10) == []
    finally:
        await cleanup(redis, artifact_type)


async def test_ensure_groups_is_idempotent(redis, artifact_type) -> None:
    """BUSYGROUP on restart is normal, not an error. Every arm restart hits this."""
    _, consumer_spec = specs_for(artifact_type)
    try:
        consumer = RingConsumer(redis, consumer_spec, consumer_name="c1")
        await consumer.ensure_groups()
        await consumer.ensure_groups()
        await consumer.ensure_groups()
    finally:
        await cleanup(redis, artifact_type)


async def test_an_unacknowledged_message_is_redelivered(redis, artifact_type) -> None:
    """
    At-least-once is the property the transport was chosen for.

    A consumer that reads and then crashes must see the message again, which is also
    why handlers have to be idempotent.
    """
    producer, consumer_spec = specs_for(artifact_type)
    try:
        first = RingConsumer(redis, consumer_spec, consumer_name="c1")
        await first.ensure_groups()
        await RingPublisher(redis, producer).publish(make_artifact(artifact_type))

        delivered = await first.consume(block_ms=500)
        assert len(delivered) == 1  # read, and deliberately NOT acked

        pending = await redis.xpending(stream_key(artifact_type), first.group)
        assert pending["pending"] == 1
    finally:
        await cleanup(redis, artifact_type)


async def test_acknowledging_clears_the_pending_entry(redis, artifact_type) -> None:
    producer, consumer_spec = specs_for(artifact_type)
    try:
        consumer = RingConsumer(redis, consumer_spec, consumer_name="c1")
        await consumer.ensure_groups()
        await RingPublisher(redis, producer).publish(make_artifact(artifact_type))

        messages = await consumer.consume(block_ms=500)
        assert await consumer.ack(messages) == 1

        pending = await redis.xpending(stream_key(artifact_type), consumer.group)
        assert pending["pending"] == 0
    finally:
        await cleanup(redis, artifact_type)


async def test_acking_nothing_is_not_an_error(redis, artifact_type) -> None:
    _, consumer_spec = specs_for(artifact_type)
    consumer = RingConsumer(redis, consumer_spec, consumer_name="c1")
    assert await consumer.ack([]) == 0


async def test_two_replicas_of_one_arm_share_the_work(redis, artifact_type) -> None:
    """
    One group per arm: an artifact is handled once across the deployment, not once
    per replica. Getting this wrong means every scaled-out arm does duplicate work.
    """
    producer, consumer_spec = specs_for(artifact_type)
    try:
        replica_a = RingConsumer(redis, consumer_spec, consumer_name="replica-a")
        replica_b = RingConsumer(redis, consumer_spec, consumer_name="replica-b")
        await replica_a.ensure_groups()

        publisher = RingPublisher(redis, producer)
        for _ in range(6):
            await publisher.publish(make_artifact(artifact_type))

        got_a = await replica_a.consume(count=3, block_ms=500)
        got_b = await replica_b.consume(count=3, block_ms=500)

        assert len(got_a) + len(got_b) == 6
        ids = {m.artifact.artifact_id for m in got_a} | {m.artifact.artifact_id for m in got_b}
        assert len(ids) == 6, "an artifact was delivered to both replicas"
    finally:
        await cleanup(redis, artifact_type)


async def test_two_different_arms_each_get_their_own_copy(redis, artifact_type) -> None:
    """
    `subscribes` is a fan-out across arms and a queue within one.

    The Judge and the Memory arm both consuming `code` must each see every artifact.
    """
    producer, consumer_spec = specs_for(artifact_type)
    memory_spec = consumer_spec.model_copy(update={"arm_id": "memory"})
    try:
        judge = RingConsumer(redis, consumer_spec, consumer_name="j1")
        memory = RingConsumer(redis, memory_spec, consumer_name="m1")
        await judge.ensure_groups()
        await memory.ensure_groups()
        assert judge.group != memory.group

        await RingPublisher(redis, producer).publish(make_artifact(artifact_type))

        assert len(await judge.consume(block_ms=500)) == 1
        assert len(await memory.consume(block_ms=500)) == 1
    finally:
        await cleanup(redis, artifact_type)


async def test_an_unparsable_message_is_dropped_rather_than_stalling_the_arm(
    redis, artifact_type
) -> None:
    """
    A poison pill that redelivers forever looks exactly like an arm that has stopped.

    The bad message is acknowledged and logged; the good one behind it still arrives.
    """
    producer, consumer_spec = specs_for(artifact_type)
    try:
        consumer = RingConsumer(redis, consumer_spec, consumer_name="c1")
        await consumer.ensure_groups()

        await redis.xadd(stream_key(artifact_type), {"artifact": "{not json"})
        await redis.xadd(stream_key(artifact_type), {"wrong_field": "no artifact here"})
        good = make_artifact(artifact_type, content="survivor")
        await RingPublisher(redis, producer).publish(good)

        messages = await consumer.consume(count=10, block_ms=500)
        assert [m.artifact.content for m in messages] == ["survivor"]

        # Both bad entries were acked, so neither will come back.
        pending = await redis.xpending(stream_key(artifact_type), consumer.group)
        assert pending["pending"] == 1  # only the good one, which we did not ack
    finally:
        await cleanup(redis, artifact_type)


async def test_the_stream_is_capped(redis, artifact_type) -> None:
    """
    Unbounded retention makes a busy task an unbounded memory commitment on a shared
    Redis. Trimming is approximate, so this asserts a bound rather than an exact length.
    """
    producer, _ = specs_for(artifact_type)
    try:
        publisher = RingPublisher(redis, producer, maxlen=10)
        for _ in range(200):
            await publisher.publish(make_artifact(artifact_type))
        assert await redis.xlen(stream_key(artifact_type)) < 200
    finally:
        await cleanup(redis, artifact_type)


async def test_decode_responses_clients_work_too(artifact_type) -> None:
    """
    redis-py returns bytes or str depending on how the client was built.

    Assuming one gives a message id like `b'1-0'`, which then fails to acknowledge --
    quietly, because XACK of an unknown id returns 0 rather than raising.
    """
    client = redis_asyncio.from_url(REDIS_URL, decode_responses=True)
    try:
        await client.ping()
    except Exception as exc:  # noqa: BLE001
        await client.aclose()
        pytest.skip(f"no Redis at {REDIS_URL}: {exc}")

    producer, consumer_spec = specs_for(artifact_type)
    try:
        consumer = RingConsumer(client, consumer_spec, consumer_name="c1")
        await consumer.ensure_groups()
        await RingPublisher(client, producer).publish(make_artifact(artifact_type))

        messages = await consumer.consume(block_ms=500)
        assert len(messages) == 1
        assert isinstance(messages[0].message_id, str)
        assert await consumer.ack(messages) == 1
    finally:
        await client.delete(stream_key(artifact_type))
        await client.aclose()


def test_stream_keys_are_namespaced() -> None:
    assert stream_key("code") == f"{RING_PREFIX}:code"
