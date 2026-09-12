"""Global semantic memory: the knowledge graph and the provenance log.

Revision ID: 0001_global_semantic_memory
Revises:
Create Date: 2026-09-12

Transcribed from `docs/implementation/memory-systems.md`, which has carried a complete,
implementable schema since before any of this was built. Four tables and their indexes,
in a dedicated `memory` schema.

Three things here are not in that document, each for a stated reason:

- **`CREATE SCHEMA memory`.** The document writes the tables into the default schema.
  Separating them means a database role scoped to `memory` cannot read the
  orchestrator's `public.tasks` however thoroughly the Memory arm is compromised — and
  Memory is the arm that ingests content every other arm produced, so it is the one
  most exposed to material it did not write.

- **`action_log.artifact_id`, unique.** The document's `action_log` has no artifact
  identity and therefore no way to be idempotent. Ring delivery is at-least-once, so
  the same artifact arriving twice is normal operation; without this constraint the
  second delivery silently doubles the record and every count built on it is wrong.
  This is the same defect as `store_task_result`, which INSERTed unconditionally into a
  table with a unique `task_id` and turned a resumed graph into a permanently stuck
  task.

- **`action_log.sensitivity` and `content_sha256`.** The data diode is only enforceable
  if the label is stored. Keeping it here as well as in the vector payload lets an
  audit answer "what restricted material did this task touch" from one table, without
  a vector search.

Timestamps are `TIMESTAMPTZ`, not the document's naive `TIMESTAMP`. A provenance record
whose time has no zone is a provenance record that cannot be ordered against another
host's.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_global_semantic_memory"
down_revision = None
branch_labels = None
depends_on = None

SCHEMA = "memory"


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    op.create_table(
        "entities",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "properties",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_entities_type", "entities", ["entity_type"], schema=SCHEMA)
    # The document's two GIN indexes. Created with `create_index` rather than raw SQL
    # so that this and the ORM's `__table_args__` are the same construct, which is what
    # lets `make migrate-check` compare them instead of reporting them missing forever.
    op.create_index(
        "idx_entities_name",
        "entities",
        [sa.text("to_tsvector('english', name)")],
        schema=SCHEMA,
        postgresql_using="gin",
    )
    op.create_index(
        "idx_entities_properties",
        "entities",
        ["properties"],
        schema=SCHEMA,
        postgresql_using="gin",
    )

    op.create_table(
        "relationships",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("from_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("to_entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("relationship_type", sa.String(50), nullable=False),
        sa.Column(
            "properties",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.ForeignKeyConstraint(["from_entity_id"], [f"{SCHEMA}.entities.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["to_entity_id"], [f"{SCHEMA}.entities.id"], ondelete="CASCADE"),
        schema=SCHEMA,
    )
    op.create_index("idx_relationships_from", "relationships", ["from_entity_id"], schema=SCHEMA)
    op.create_index("idx_relationships_to", "relationships", ["to_entity_id"], schema=SCHEMA)
    op.create_index("idx_relationships_type", "relationships", ["relationship_type"], schema=SCHEMA)

    op.create_table(
        "task_history",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("task_id", sa.String(255), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column(
            "plan",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "results",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("cost_tokens", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        schema=SCHEMA,
    )
    op.create_index("idx_task_history_task_id", "task_history", ["task_id"], schema=SCHEMA)
    op.create_index(
        "idx_task_history_created_at",
        "task_history",
        [sa.text("created_at DESC")],
        schema=SCHEMA,
    )

    op.create_table(
        "action_log",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("artifact_id", sa.String(255), nullable=False),
        sa.Column("task_id", sa.String(255), nullable=False),
        sa.Column("arm_id", sa.String(50), nullable=False),
        sa.Column("action_type", sa.String(50), nullable=False),
        sa.Column(
            "action_details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "result",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "sensitivity", sa.String(20), nullable=False, server_default=sa.text("'internal'")
        ),
        sa.Column("content_sha256", sa.String(64), nullable=False, server_default=sa.text("''")),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
        ),
        sa.UniqueConstraint("artifact_id", name="uq_action_log_artifact_id"),
        schema=SCHEMA,
    )
    op.create_index("idx_action_log_task_id", "action_log", ["task_id"], schema=SCHEMA)
    op.create_index("idx_action_log_arm_id", "action_log", ["arm_id"], schema=SCHEMA)
    op.create_index(
        "idx_action_log_timestamp", "action_log", [sa.text("timestamp DESC")], schema=SCHEMA
    )


def downgrade() -> None:
    """
    Drop the tables, and the schema with them.

    A downgrade here destroys every remembered artifact. That is what a downgrade of
    the migration that created the store means, and writing it as a no-op to seem safe
    would be worse: it would leave a database that reports itself at revision base
    while still holding the tables.
    """
    op.drop_table("action_log", schema=SCHEMA)
    op.drop_table("task_history", schema=SCHEMA)
    op.drop_table("relationships", schema=SCHEMA)
    op.drop_table("entities", schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA} CASCADE")
