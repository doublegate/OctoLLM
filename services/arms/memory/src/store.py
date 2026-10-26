"""
Semantic memory: the knowledge graph and the provenance record, in Postgres.

Everything Memory is asked to remember lands here, whether or not it is worth a vector.
`action_log` is the authoritative answer to "what has this system produced, who produced
it, under what task, and how sensitive was it" -- a question with an exact answer, which
is why it lives in a relational store rather than alongside the embeddings.

## Writes are idempotent, and that is not optional

The ring delivers at-least-once. A consumer that crashes after handling an artifact but
before acknowledging it will see that artifact again, and that is normal operation, not
an incident. So `remember` is an upsert keyed on `artifact_id`, and it reports whether
the row already existed rather than hiding it.

This is the same defect class as `store_task_result` in the orchestrator, which INSERTed
unconditionally into a table with a unique `task_id` -- a resumed graph re-running its
final node turned a recoverable task into a permanently stuck one. The fix there was an
upsert; it is an upsert here for the same reason, before the traffic that would expose it.
"""

from __future__ import annotations

from typing import Any

import structlog
from octollm_common.models.provenance import Artifact
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from .models import ActionLog, Entity, Relationship, TaskHistory

logger = structlog.get_logger(__name__)

__all__ = ["SemanticStore"]


class SemanticStore:
    """The knowledge graph and provenance log, over one async session factory."""

    def __init__(self, session_factory: Any) -> None:
        self._session_factory = session_factory

    async def remember(self, artifact: Artifact) -> bool:
        """
        Record one artifact's provenance.

        Returns True when this was a new artifact, False when it had already been
        stored -- the caller reports that as `duplicate` rather than treating it as an
        error, because a redelivery is expected.
        """
        provenance = artifact.provenance
        values = {
            "artifact_id": artifact.artifact_id,
            "task_id": provenance.task_id,
            "arm_id": provenance.created_by,
            "action_type": artifact.artifact_type,
            "action_details": {
                "trace_id": provenance.trace_id,
                "engagement_id": provenance.engagement_id,
                "promoted_from": provenance.promoted_from,
                "parent_task_id": provenance.parent_task_id,
                "input_sources": [s.model_dump(mode="json") for s in provenance.input_sources],
                "transformations": [t.model_dump(mode="json") for t in provenance.transformations],
                "model_info": provenance.model_info.model_dump(mode="json"),
            },
            "result": provenance.validation_status.model_dump(mode="json"),
            "sensitivity": str(provenance.sensitivity),
            "content_sha256": artifact.content_sha256,
            "timestamp": provenance.created_at,
        }

        async with self._session_factory() as session:
            statement = (
                pg_insert(ActionLog)
                .values(**values)
                # DO NOTHING rather than DO UPDATE: provenance is a record of what
                # happened, and a second delivery of the same artifact is the same
                # event. Overwriting would let a later, altered copy of an artifact
                # silently rewrite the audit trail of the original.
                .on_conflict_do_nothing(index_elements=["artifact_id"])
                .returning(ActionLog.id)
            )
            result = await session.execute(statement)
            inserted = result.scalar_one_or_none()
            await session.commit()

        created = inserted is not None
        if not created:
            logger.debug(
                "memory_duplicate_artifact",
                artifact_id=artifact.artifact_id,
                task_id=provenance.task_id,
            )
        return created

    async def provenance_for(self, artifact_id: str) -> ActionLog | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ActionLog).where(ActionLog.artifact_id == artifact_id)
            )
            row: ActionLog | None = result.scalar_one_or_none()
            return row

    async def count(self) -> int:
        """How many artifacts memory holds. Used by `/ready` and by the smoke test."""
        async with self._session_factory() as session:
            result = await session.execute(select(func.count()).select_from(ActionLog))
            return int(result.scalar_one())

    async def record_task(
        self,
        *,
        task_id: str,
        goal: str,
        plan: dict[str, Any],
        results: dict[str, Any],
        success: bool,
        duration_ms: int,
        cost_tokens: int | None = None,
    ) -> None:
        """
        Record a completed task.

        Called by the execution engine's `memory_write` node from Stage 7. It exists
        now because the table does, and a table nothing can write to is the kind of
        claim this repository is being dug out of.
        """
        async with self._session_factory() as session:
            session.add(
                TaskHistory(
                    task_id=task_id,
                    goal=goal,
                    plan=plan,
                    results=results,
                    success=success,
                    duration_ms=duration_ms,
                    cost_tokens=cost_tokens,
                )
            )
            await session.commit()

    async def upsert_entity(
        self, *, entity_type: str, name: str, properties: dict[str, Any] | None = None
    ) -> Entity:
        """
        Add or update one node in the knowledge graph.

        Matched on `(entity_type, name)`: the graph's identity for a thing is what kind
        it is and what it is called. Without that, ingesting the same tool twice
        produces two nodes and every relationship built on either is half the truth.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(Entity).where(Entity.entity_type == entity_type, Entity.name == name)
            )
            entity = result.scalar_one_or_none()
            if entity is None:
                entity = Entity(entity_type=entity_type, name=name, properties=properties or {})
                session.add(entity)
            elif properties:
                entity.properties = {**entity.properties, **properties}
            await session.commit()
            await session.refresh(entity)
            found: Entity = entity
            return found

    async def relate(
        self,
        *,
        from_entity_id: Any,
        to_entity_id: Any,
        relationship_type: str,
        properties: dict[str, Any] | None = None,
    ) -> Relationship:
        async with self._session_factory() as session:
            edge = Relationship(
                from_entity_id=from_entity_id,
                to_entity_id=to_entity_id,
                relationship_type=relationship_type,
                properties=properties or {},
            )
            session.add(edge)
            await session.commit()
            await session.refresh(edge)
            return edge
