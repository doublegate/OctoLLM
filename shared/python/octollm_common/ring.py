"""
The Neural Ring: artifacts on Redis Streams, bounded by declared topology.

The octopus biomimicry the documents are built on (`Project-Overview.md:24`,
`system-overview.md:155`, `data-flow.md:387`) has arms coordinating without routing
every message through the brain. The design before this module ignored that entirely:
every interaction was a star through the orchestrator, which is both the latency
bottleneck the architecture exists to avoid and a single point whose failure stops
work that did not need it.

Redis Streams rather than pub/sub, for three reasons that are not interchangeable:
messages persist, so a consumer that was down does not silently miss work; consumer
groups give at-least-once delivery with explicit acknowledgement, so a crash mid-handler
redelivers rather than drops; and the stream is replayable, which is what makes an
audit of "what did the arms say to each other" possible at all.

## Topology is declared, not discovered

`ArmSpec.publishes` and `ArmSpec.subscribes` are the whole of what an arm may put on
or take off the ring, and both are checked here rather than trusted. The orchestrator
reads the same declarations through the `GET /capabilities` call it already makes, so
the ring topology arrives over a protocol that already existed -- and an edge nobody
declared is unreachable rather than merely undocumented.

This is publication intent, not authorization. Authorization for a *direct* peer call
is a capability token (`octollm_common.capability`); the ring is broadcast, and its
control is which types an arm may emit and consume.

## At-least-once, and what that obliges

Delivery is at-least-once, so **handlers must be idempotent.** An artifact carries a
stable `artifact_id` and a content hash precisely so a repeat can be recognised. A
handler that appends without checking will double-count on the first redelivery, and
redelivery is normal operation, not an incident.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import structlog

from .app import ArmSpec
from .models.provenance import Artifact

logger = structlog.get_logger(__name__)

__all__ = [
    "RING_PREFIX",
    "RingConsumer",
    "RingError",
    "RingMessage",
    "RingPublisher",
    "RingTopologyError",
    "stream_key",
]

#: One stream per artifact type. Keyed by type rather than by producer so a consumer
#: subscribes to *what it needs* rather than to *who happens to make it* -- adding a
#: second producer of `code` must not require every consumer to learn about it.
RING_PREFIX = "octollm:ring"

#: Streams are capped. Unbounded retention turns a busy task into an unbounded memory
#: commitment on a Redis that other things share. Approximate trimming (`~`) is used
#: because exact trimming is O(n) per write for no benefit here.
DEFAULT_MAXLEN = 10_000


def stream_key(artifact_type: str) -> str:
    return f"{RING_PREFIX}:{artifact_type}"


class RingError(Exception):
    """Base for ring failures."""


class RingTopologyError(RingError):
    """
    An arm tried to publish or consume a type it does not declare.

    A programming error, not a runtime condition: the fix is to declare the edge in
    the roster, where the orchestrator can see it, rather than to widen this check.
    """


class RingMessage:
    """One delivered artifact, with what is needed to acknowledge it."""

    __slots__ = ("artifact", "artifact_type", "message_id")

    def __init__(self, *, message_id: str, artifact_type: str, artifact: Artifact) -> None:
        self.message_id = message_id
        self.artifact_type = artifact_type
        self.artifact = artifact

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return (
            f"RingMessage(message_id={self.message_id!r}, "
            f"artifact_type={self.artifact_type!r}, "
            f"artifact_id={self.artifact.artifact_id!r})"
        )


def _as_str(value: Any) -> str:
    """
    Normalise a Redis reply to `str`.

    redis-py returns `bytes` unless the client was built with `decode_responses=True`,
    and which of those a caller passes us is not something to depend on. Getting this
    wrong produces `b'1-0'` as a message id, which then fails to acknowledge -- quietly,
    because XACK of an unknown id returns 0 rather than raising.
    """
    return value.decode() if isinstance(value, bytes | bytearray) else str(value)


class RingPublisher:
    """
    Publishes an arm's artifacts.

    Args:
        redis: An async redis client (`redis.asyncio.Redis`).
        spec: The publishing arm's declaration. `spec.publishes` is the allowlist.
        maxlen: Approximate stream cap.
    """

    def __init__(self, redis: Any, spec: ArmSpec, *, maxlen: int = DEFAULT_MAXLEN) -> None:
        self._redis = redis
        self._spec = spec
        self._maxlen = maxlen

    async def publish(self, artifact: Artifact) -> str:
        """
        Put one artifact on the ring.

        Returns:
            The Redis stream message id.

        Raises:
            RingTopologyError: this arm does not declare `artifact.artifact_type`.
            ValueError: the artifact was produced by a different arm than the one
                publishing it. Provenance that does not match the publisher is worse
                than absent provenance, because it will be believed.
        """
        artifact_type = artifact.artifact_type
        if artifact_type not in self._spec.publishes:
            raise RingTopologyError(
                f"{self._spec.arm_id} publishes {sorted(self._spec.publishes)}, "
                f"not {artifact_type!r}. Declare it in the roster so the orchestrator "
                "sees the edge, rather than widening this check."
            )
        if artifact.provenance.created_by != self._spec.arm_id:
            raise ValueError(
                f"{self._spec.arm_id} cannot publish an artifact whose provenance "
                f"names {artifact.provenance.created_by!r} as its producer."
            )

        message_id = await self._redis.xadd(
            stream_key(artifact_type),
            {"artifact": artifact.to_json()},
            maxlen=self._maxlen,
            approximate=True,
        )
        message_id = _as_str(message_id)
        logger.debug(
            "ring_published",
            arm_id=self._spec.arm_id,
            artifact_type=artifact_type,
            artifact_id=artifact.artifact_id,
            task_id=artifact.provenance.task_id,
            message_id=message_id,
        )
        return message_id


class RingConsumer:
    """
    Consumes the types an arm subscribes to, as a member of a consumer group.

    The group is named for the arm, so every replica of one arm shares a group and an
    artifact is handled once across the deployment. A second *kind* of arm subscribing
    to the same type gets its own group and its own copy, which is the behaviour that
    makes `subscribes` a fan-out rather than a queue.

    Args:
        redis: An async redis client.
        spec: The consuming arm's declaration. `spec.subscribes` is the allowlist.
        consumer_name: Distinct per replica. Two replicas sharing a name will each
            believe the other's in-flight messages are their own on recovery.
    """

    def __init__(
        self,
        redis: Any,
        spec: ArmSpec,
        *,
        consumer_name: str,
        group: str | None = None,
        reclaim_idle_ms: int = 30_000,
    ) -> None:
        self._redis = redis
        self._spec = spec
        self._group = group or f"{spec.arm_id}-group"
        self._consumer = consumer_name
        self._reclaim_idle_ms = reclaim_idle_ms

    @property
    def group(self) -> str:
        return self._group

    async def ensure_groups(self) -> None:
        """
        Create the consumer group on each subscribed stream, idempotently.

        `mkstream=True` creates the stream if no producer has written to it yet --
        without it, a consumer that starts before its producer raises `NOGROUP` and
        the startup order of two independent services becomes load-bearing.

        An existing group is not an error. redis-py surfaces that as a `ResponseError`
        whose message begins `BUSYGROUP`, and it is matched on the message because
        redis-py does not raise a distinct type for it. Any other `ResponseError`
        propagates.
        """
        for artifact_type in self._spec.subscribes:
            try:
                await self._redis.xgroup_create(
                    name=stream_key(artifact_type),
                    groupname=self._group,
                    id="0",
                    mkstream=True,
                )
            except Exception as exc:  # noqa: BLE001 - narrowed immediately below
                if "BUSYGROUP" not in str(exc):
                    raise
                logger.debug(
                    "ring_group_exists",
                    arm_id=self._spec.arm_id,
                    group=self._group,
                    artifact_type=artifact_type,
                )

    async def consume(self, *, count: int = 10, block_ms: int = 1000) -> list[RingMessage]:
        """
        Read pending and undelivered artifacts for this group.

        Pending messages are recovered before reading `">"`: idle entries from dead or
        stalled consumers are reclaimed via `XAUTOCLAIM`, and this consumer's own
        unacknowledged entries are re-read with `"0"`. Returns an empty list when the
        block expires with nothing new, which is the normal idle path and not an error.

        A message whose payload does not parse is **acknowledged and dropped**, with a
        warning. Leaving it pending would make it redeliver forever, and one
        unparsable message would then stall the arm behind it -- a poison pill that
        looks exactly like an arm that has stopped working.
        """
        if not self._spec.subscribes:
            return []

        messages: list[RingMessage] = []
        seen: set[tuple[str, str]] = set()

        if hasattr(self._redis, "xautoclaim"):
            for artifact_type in self._spec.subscribes:
                if len(messages) >= count:
                    break
                key = stream_key(artifact_type)
                claimed = await self._redis.xautoclaim(
                    key,
                    self._group,
                    self._consumer,
                    min_idle_time=self._reclaim_idle_ms,
                    start_id="0-0",
                    count=count - len(messages),
                )
                entries = (
                    claimed[1] if isinstance(claimed, tuple | list) and len(claimed) >= 2 else []
                )
                deleted = (
                    claimed[2] if isinstance(claimed, tuple | list) and len(claimed) >= 3 else []
                )
                for raw_deleted in deleted:
                    await self._redis.xack(key, self._group, _as_str(raw_deleted))
                await self._collect_entries(key, artifact_type, entries, messages, seen)

        if len(messages) < count:
            pending_streams = {stream_key(t): "0" for t in self._spec.subscribes}
            pending_response = await self._redis.xreadgroup(
                groupname=self._group,
                consumername=self._consumer,
                streams=pending_streams,
                count=count - len(messages),
            )
            await self._collect_response(pending_response, messages, seen)

        if len(messages) < count:
            streams = {stream_key(t): ">" for t in self._spec.subscribes}
            response = await self._redis.xreadgroup(
                groupname=self._group,
                consumername=self._consumer,
                streams=streams,
                count=count - len(messages),
                block=block_ms if not messages else None,
            )
            await self._collect_response(response, messages, seen)

        return messages

    async def _collect_response(
        self,
        response: Any,
        messages: list[RingMessage],
        seen: set[tuple[str, str]],
    ) -> None:
        if not response:
            return
        for raw_stream, entries in response:
            key = _as_str(raw_stream)
            artifact_type = key.removeprefix(f"{RING_PREFIX}:")
            await self._collect_entries(key, artifact_type, entries, messages, seen)

    async def _collect_entries(
        self,
        key: str,
        artifact_type: str,
        entries: Any,
        messages: list[RingMessage],
        seen: set[tuple[str, str]],
    ) -> None:
        for raw_id, fields in entries:
            message_id = _as_str(raw_id)
            if (key, message_id) in seen:
                continue
            seen.add((key, message_id))
            payload = _field(fields, "artifact")
            if payload is None:
                await self._drop(key, message_id, "no artifact field")
                continue
            try:
                artifact = Artifact.from_json(payload)
            except ValueError as exc:
                await self._drop(key, message_id, str(exc))
                continue
            messages.append(
                RingMessage(
                    message_id=message_id,
                    artifact_type=artifact_type,
                    artifact=artifact,
                )
            )

    async def ack(self, messages: Sequence[RingMessage]) -> int:
        """
        Acknowledge handled messages.

        Call this **after** the handler succeeds, never before. Acknowledging on
        receipt converts at-least-once into at-most-once and loses work on a crash,
        which is the opposite of the trade this transport was chosen for.
        """
        if not messages:
            return 0
        by_stream: dict[str, list[str]] = {}
        for message in messages:
            by_stream.setdefault(stream_key(message.artifact_type), []).append(message.message_id)
        acked = 0
        for key, ids in by_stream.items():
            acked += int(await self._redis.xack(key, self._group, *ids))
        return acked

    async def _drop(self, key: str, message_id: str, reason: str) -> None:
        logger.warning(
            "ring_message_dropped",
            arm_id=self._spec.arm_id,
            stream=key,
            message_id=message_id,
            reason=reason,
        )
        await self._redis.xack(key, self._group, message_id)


def _field(fields: Any, name: str) -> str | None:
    """Pull one field out of a stream entry, tolerating bytes or str keys."""
    if not isinstance(fields, dict):
        return None
    for key, value in fields.items():
        if _as_str(key) == name:
            return _as_str(value)
    return None
