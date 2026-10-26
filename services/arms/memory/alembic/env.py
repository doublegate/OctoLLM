"""
Alembic environment for the Memory arm.

`alembic` has been a declared dependency of this repository since Phase 0, and four
separate documents told people to run `alembic upgrade head` against a project that had
no `alembic.ini`, no `env.py` and no `versions/`. Tables came from
`Base.metadata.create_all`. This is the first migration environment that exists.

## Scoped to the `memory` schema, and only that

`include_object` refuses every object outside `memory`, so an autogenerate run here can
never propose dropping the orchestrator's `public.tasks` because it does not know about
it. Without that guard, the first `--autogenerate` against a live database would emit a
migration that deletes another service's data, and it would look entirely reasonable in
review.

`include_schemas=True` is required alongside it: without it Alembic compares only the
default search path and reports every table in `memory` as one to be created, on every
run, forever.

## Sync driver, deliberately

The service uses `postgresql+psycopg://` with an async engine. Migrations use the same
URL with a **sync** engine — psycopg3 supports both, and SQLAlchemy chooses by which
`create_engine` is called. Running DDL synchronously keeps this file free of the
async-migration boilerplate, and migrations are a one-shot process with nothing to
overlap.
"""

from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

import sqlalchemy as sa
from alembic import context
from sqlalchemy import engine_from_config, pool

# The models live one directory up, as a package rooted at the service directory.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.models import MEMORY_SCHEMA, Base  # noqa: E402

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _database_url() -> str:
    """
    The URL to migrate, from the environment.

    Never from `alembic.ini`: a connection string in a tracked file is a credential in
    a tracked file, and `make secrets-scan` would be right to complain.
    """
    url = os.environ.get("MEMORY_DATABASE_URL")
    if not url:
        raise RuntimeError(
            "MEMORY_DATABASE_URL is not set. Migrations need a database to run "
            "against, and there is deliberately no default in alembic.ini."
        )
    return url


def include_object(obj, name, type_, reflected, compare_to):  # noqa: ANN001, ANN201
    """
    Consider only objects in the `memory` schema.

    See the module docstring: without this, an autogenerate run against a live database
    would propose dropping every table another service owns.
    """
    if type_ in {"table", "column", "index", "unique_constraint", "foreign_key_constraint"}:
        schema = getattr(obj, "schema", None)
        if schema is None:
            parent = getattr(obj, "table", None)
            schema = getattr(parent, "schema", None)
        return schema == MEMORY_SCHEMA
    return True


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a connection, for review or for a DBA to apply."""
    context.configure(
        url=_database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
        include_object=include_object,
        version_table_schema=MEMORY_SCHEMA,
    )
    with context.begin_transaction():
        context.execute(f"CREATE SCHEMA IF NOT EXISTS {MEMORY_SCHEMA}")
        context.run_migrations()


def run_migrations_online() -> None:
    """Apply migrations against a live database."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _database_url()
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)

    with connectable.connect() as connection:
        # Bootstrap: the version table lives in `memory` (see `version_table_schema`
        # below), so the schema has to exist before Alembic can record that it has run
        # the migration which creates it. Alembic builds the version table during
        # `configure`, ahead of any migration, so doing this inside 0001 is too late.
        #
        # `IF NOT EXISTS` and committed on its own: this is idempotent and must not be
        # rolled back by a later failure in the migration itself, or the next attempt
        # hits the same ordering problem.
        connection.execute(sa.text(f"CREATE SCHEMA IF NOT EXISTS {MEMORY_SCHEMA}"))
        connection.commit()

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
            include_object=include_object,
            # The version table lives in `memory` too. In `public` it would be a row
            # the orchestrator's role can see and, worse, a second service's alembic
            # would collide with it.
            version_table_schema=MEMORY_SCHEMA,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
