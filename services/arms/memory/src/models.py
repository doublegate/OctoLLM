"""
The global semantic memory schema.

**Transcribed, not designed.** `docs/implementation/memory-systems.md` has carried a
complete, implementable SQL schema since before any of this was built -- four tables
with their indexes. Designing a fifth version of it would have produced exactly the
disagreement this repository spent its first phase in; these models are that SQL, in
SQLAlchemy, and a test asserts they still match the migration that creates them.

## Why a dedicated `memory` schema

The tables live in a Postgres schema called `memory`, not in `public` alongside the
orchestrator's. One line in the migration today; a data move later.

The reason is blast radius. Memory is the arm that ingests artifacts from every other
arm, which makes it the arm most exposed to content it did not produce. A database role
scoped to `GRANT USAGE ON SCHEMA memory` cannot read `public.tasks` however thoroughly
it is compromised. Sharing `public` would make that separation a migration rather than
a grant.

## What lives where

Postgres holds the **semantic** half: entities, the relationships between them, and the
provenance of everything that happened. It is the authoritative record, it is
relational, and it is queried by attribute.

Qdrant holds the **episodic** half: per-arm collections of artifact embeddings, queried
by similarity. See `vectors.py`.

The split is not arbitrary. "Which arm produced this and under what authorization" is a
question with an exact answer and belongs in a relational store; "what else is like
this" has no exact answer and belongs in a vector store. Putting either in the other
produces a system that answers both questions badly.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID as PyUUID
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

__all__ = [
    "MEMORY_SCHEMA",
    "ActionLog",
    "Base",
    "Entity",
    "Relationship",
    "TaskHistory",
    "utcnow",
]

#: The Postgres schema every table here lives in. Referenced by the Alembic migration
#: and by the drift test, so there is one spelling of it.
MEMORY_SCHEMA = "memory"


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """
    Declarative base for the memory schema.

    Separate from the orchestrator's `Base` on purpose: they are different services
    owning different schemas, and one shared metadata would let a stray import create
    the orchestrator's tables inside `memory` or the reverse.
    """


class Entity(Base):
    """A typed object in the knowledge graph."""

    __tablename__ = "entities"
    __table_args__ = (
        Index("idx_entities_type", "entity_type"),
        # Declared here as well as in the migration, and with the SAME construct, so
        # that `make migrate-check` can compare them. Writing the GIN indexes as raw
        # SQL in the migration only made the drift check report them as missing on
        # every run -- a gate that always fails teaches nothing.
        Index(
            "idx_entities_name",
            text("to_tsvector('english', name)"),
            postgresql_using="gin",
        ),
        Index("idx_entities_properties", "properties", postgresql_using="gin"),
        {"schema": MEMORY_SCHEMA},
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow, onupdate=utcnow
    )


class Relationship(Base):
    """A directed, typed edge between two entities."""

    __tablename__ = "relationships"
    __table_args__ = (
        Index("idx_relationships_from", "from_entity_id"),
        Index("idx_relationships_to", "to_entity_id"),
        Index("idx_relationships_type", "relationship_type"),
        {"schema": MEMORY_SCHEMA},
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    from_entity_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{MEMORY_SCHEMA}.entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    to_entity_id: Mapped[PyUUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{MEMORY_SCHEMA}.entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(String(50), nullable=False)
    properties: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class TaskHistory(Base):
    """What a task set out to do, what it did, and what it cost."""

    __tablename__ = "task_history"
    __table_args__ = (
        Index("idx_task_history_task_id", "task_id"),
        Index("idx_task_history_created_at", text("created_at DESC")),
        {"schema": MEMORY_SCHEMA},
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    plan: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    results: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    success: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    cost_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )


class ActionLog(Base):
    """
    Provenance for every artifact memory has seen.

    `artifact_id` carries a uniqueness constraint the design document does not have,
    and it is the reason writes are idempotent. Ring delivery is at-least-once, so the
    same artifact arriving twice is normal operation rather than an incident; without
    this constraint the second delivery would silently double the record and every
    later count built on it would be wrong.
    """

    __tablename__ = "action_log"
    __table_args__ = (
        UniqueConstraint("artifact_id", name="uq_action_log_artifact_id"),
        Index("idx_action_log_task_id", "task_id"),
        Index("idx_action_log_arm_id", "arm_id"),
        Index("idx_action_log_timestamp", text("timestamp DESC")),
        {"schema": MEMORY_SCHEMA},
    )

    id: Mapped[PyUUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    artifact_id: Mapped[str] = mapped_column(String(255), nullable=False)
    task_id: Mapped[str] = mapped_column(String(255), nullable=False)
    arm_id: Mapped[str] = mapped_column(String(50), nullable=False)
    action_type: Mapped[str] = mapped_column(String(50), nullable=False)
    action_details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    # Stored so a recall can enforce the diode without reading the vector store, and so
    # an audit can answer "what restricted material did this task touch" from one table.
    sensitivity: Mapped[str] = mapped_column(String(20), nullable=False, default="internal")
    content_sha256: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utcnow
    )
