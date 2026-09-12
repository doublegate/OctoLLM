"""
The ring consumer: Memory's other write path.

Memory subscribes to `artifact` on the Neural Ring, which is how work reaches it without
anyone calling it. That is the point of the ring — an arm publishes what it produced and
does not need to know that a memory exists — and it is why Memory was built before the
arms that will feed it.

## Acknowledge after the write, never before

`RingConsumer.consume` reads; this acknowledges only once `remember` has returned. A
crash in between redelivers the artifact, which is correct and expected: `remember` is
idempotent precisely so that redelivery costs a duplicate detection rather than a
duplicate row.

Acknowledging on receipt would convert at-least-once into at-most-once and lose the
artifact on any crash — the opposite of the trade Redis Streams were chosen for.

## A failed write is left pending on purpose

If `remember` raises, the message is **not** acknowledged, so Redis redelivers it. The
exception is a message that cannot be parsed at all, which `RingConsumer` drops for us:
an unparsable artifact would redeliver forever and stall every artifact behind it, and a
poison pill looks exactly like an arm that has stopped working.

## `memory_write_ack` closes the loop

Every stored artifact produces an acknowledgement on the ring. It is what lets a
producer, or an auditor, establish that something reached memory without querying
memory — and it is declared in the roster, so the orchestrator can see the edge.
"""

from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from octollm_common.models.contracts import RememberRequest
from octollm_common.models.provenance import Artifact, Provenance
from octollm_common.ring import RingConsumer, RingPublisher

from .service import ARM_ID, MemoryService

logger = structlog.get_logger(__name__)

__all__ = ["ArtifactConsumer"]


class ArtifactConsumer:
    """Drains `artifact` from the ring into memory, and acknowledges what it stored."""

    def __init__(
        self,
        *,
        service: MemoryService,
        consumer: RingConsumer,
        publisher: RingPublisher,
        batch: int = 32,
        block_ms: int = 2000,
    ) -> None:
        self._service = service
        self._consumer = consumer
        self._publisher = publisher
        self._batch = batch
        self._block_ms = block_ms
        self._task: asyncio.Task[None] | None = None
        self._stopping = asyncio.Event()
        #: Counters, exposed on `/ready` so that "the consumer is running" and "the
        #: consumer is doing anything" are never the same signal.
        self.stored = 0
        self.duplicates = 0
        self.failed = 0

    async def start(self) -> None:
        await self._consumer.ensure_groups()
        self._task = asyncio.create_task(self._run(), name="memory-ring-consumer")
        logger.info("ring_consumer_started", group=self._consumer.group)

    async def stop(self) -> None:
        """
        Stop draining and wait for the current batch.

        The in-flight batch is allowed to finish rather than cancelled mid-write: a
        cancelled `remember` between the Postgres write and the acknowledgement is the
        one case that would leave a message pending after it was already stored, which
        redelivery then resolves -- but finishing is cheaper and quieter.
        """
        self._stopping.set()
        if self._task is not None:
            try:
                await asyncio.wait_for(self._task, timeout=10.0)
            except TimeoutError:
                self._task.cancel()
                logger.warning("ring_consumer_stop_timeout")
            self._task = None
        logger.info("ring_consumer_stopped", stored=self.stored, failed=self.failed)

    async def _run(self) -> None:
        while not self._stopping.is_set():
            try:
                await self.drain_once()
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 - the loop must outlive one failure
                # A Redis blip must not kill the consumer: the task dying silently
                # would leave an arm that reports healthy and remembers nothing.
                logger.warning("ring_consumer_iteration_failed", error=str(exc))
                await asyncio.sleep(1.0)

    async def drain_once(self) -> int:
        """
        Handle one batch. Returns how many artifacts were stored.

        Public and separately callable so a test can drive exactly one batch rather
        than racing a background loop.
        """
        messages = await self._consumer.consume(count=self._batch, block_ms=self._block_ms)
        if not messages:
            return 0

        handled = []
        stored = 0
        for message in messages:
            try:
                response = await self._service.remember(
                    RememberRequest(artifact=message.artifact),
                    request_id=f"ring-{message.message_id}",
                )
            except Exception as exc:  # noqa: BLE001 - leave it pending for redelivery
                self.failed += 1
                logger.warning(
                    "memory_ring_write_failed",
                    artifact_id=message.artifact.artifact_id,
                    message_id=message.message_id,
                    error=str(exc),
                )
                continue

            if response.duplicate:
                self.duplicates += 1
            else:
                self.stored += 1
                stored += 1
            handled.append(message)
            await self._acknowledge_on_ring(message.artifact)

        # Acknowledged only after the write returned. See the module docstring.
        if handled:
            await self._consumer.ack(handled)
        return stored

    async def _acknowledge_on_ring(self, artifact: Artifact) -> None:
        """
        Publish `memory_write_ack`.

        Best-effort: a failure here is logged and swallowed, because the artifact is
        already durably stored and failing the drain would redeliver an artifact that
        does not need storing again.
        """
        ack = Artifact(
            artifact_id=str(uuid.uuid4()),
            artifact_type="memory_write_ack",
            content=artifact.artifact_id,
            provenance=Provenance(
                created_by=ARM_ID,
                task_id=artifact.provenance.task_id,
                trace_id=artifact.provenance.trace_id,
                # The acknowledgement inherits the artifact's sensitivity. It carries
                # the artifact's id, and which restricted artifacts exist is itself
                # information the diode is meant to bound.
                sensitivity=artifact.provenance.sensitivity,
                promoted_from=artifact.artifact_id,
            ),
        )
        try:
            await self._publisher.publish(ack)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "memory_ack_publish_failed",
                artifact_id=artifact.artifact_id,
                error=str(exc),
            )

    def stats(self) -> dict[str, Any]:
        return {
            "ring_stored": self.stored,
            "ring_duplicates": self.duplicates,
            "ring_failed": self.failed,
        }
