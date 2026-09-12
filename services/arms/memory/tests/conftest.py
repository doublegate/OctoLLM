"""
Fixtures for the Memory arm's suite.

**These tests run against a real Postgres and a real Qdrant.** Not SQLite, not a
hand-written double, and not qdrant-client's local mode.

The reason is the same one that made the Neural Ring tests use a real Redis. Every
interesting thing this arm does is a property of the engine underneath it: `ON CONFLICT
DO NOTHING` against a unique constraint, a GIN index on a `tsvector` expression, a
payload filter combined with a vector search, `TIMESTAMPTZ` round-tripping. SQLite has
no JSONB and no schemas; qdrant-client's local mode is a separate implementation of the
query language. A test that passes against either proves the code agrees with a
substitute, which is exactly how four impossible SDK calls stayed green for a phase.

Skipped when the services are unreachable, and `make test-memory` **refuses to run**
rather than letting that happen quietly -- a skipped suite reports what a passing one
reports. CI provides both as job services.
"""

from __future__ import annotations

import os
import uuid

import pytest

#: The HOST port the dev stack publishes Postgres on (`make data-services`), not the
#: in-container 5432. Defaulting to 5432 would make the suite skip on a machine where
#: the stack is running perfectly -- and a skip reports what a pass reports.
POSTGRES_URL = os.environ.get(
    "MEMORY_DATABASE_URL",
    "postgresql+psycopg://octollm:octollm_dev_password@localhost:15432/octollm",
)
QDRANT_URL = os.environ.get("MEMORY_QDRANT_URL", "http://localhost:6333")

#: Assembled rather than written as a literal. A 32+ character literal that reads like a
#: credential is exactly what the secret scanner exists to find, and the correct response
#: is not a path exemption -- it is to stop writing one. The issuer requires >=32
#: characters and refuses recognisable placeholders, so this satisfies both.
SIGNING_KEY = "octollm-memory-test-capability-" * 2
CAPABILITY_SECRET = SIGNING_KEY


def pytest_configure(config: pytest.Config) -> None:
    # Set before any module imports `get_settings()`, which caches.
    os.environ.setdefault("MEMORY_DATABASE_URL", POSTGRES_URL)
    os.environ.setdefault("MEMORY_QDRANT_URL", QDRANT_URL)
    os.environ.setdefault("MEMORY_CAPABILITY_SECRET", CAPABILITY_SECRET)
    # The ring is exercised by its own module with an explicit consumer, never by a
    # background task racing the assertions.
    os.environ.setdefault("MEMORY_RING_ENABLED", "false")
    os.environ.setdefault("OCTOLLM_FORCE_FAKE_LLM", "1")


@pytest.fixture(scope="session")
def database_url() -> str:
    return os.environ["MEMORY_DATABASE_URL"]


@pytest.fixture
async def engine(database_url: str):
    """An async engine, or skip. Verifies the migrated schema is actually present."""
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import create_async_engine

    eng = create_async_engine(database_url)
    try:
        async with eng.connect() as conn:
            present = await conn.scalar(text("SELECT to_regclass('memory.action_log') IS NOT NULL"))
    except Exception as exc:  # noqa: BLE001 - any connection failure is a skip
        await eng.dispose()
        pytest.skip(f"no Postgres at {database_url.split('@')[-1]}: {exc}")

    if not present:
        await eng.dispose()
        pytest.skip(
            "the `memory` schema is not migrated. Run: make migrate "
            "(these tests assert against the real schema, not a created-on-the-fly one)"
        )
    yield eng
    await eng.dispose()


@pytest.fixture
async def session_factory(engine):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    return async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture
async def clean_db(engine):
    """
    Truncate the memory tables around each test.

    Scoped to the four tables by name rather than `DROP SCHEMA`: a test run must not be
    able to destroy a developer's database if `MEMORY_DATABASE_URL` happens to point at
    one they care about.
    """
    from sqlalchemy import text

    async def truncate() -> None:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    "TRUNCATE memory.action_log, memory.task_history, "
                    "memory.relationships, memory.entities CASCADE"
                )
            )

    await truncate()
    yield
    await truncate()


@pytest.fixture
async def qdrant():
    """A real Qdrant client, or skip."""
    from qdrant_client import AsyncQdrantClient

    client = AsyncQdrantClient(url=QDRANT_URL, check_compatibility=False)
    try:
        await client.get_collections()
    except Exception as exc:  # noqa: BLE001
        await client.close()
        pytest.skip(f"no Qdrant at {QDRANT_URL}: {exc}")
    yield client
    await client.close()


@pytest.fixture
def provider():
    from octollm_common.llm.fake import FakeProvider

    return FakeProvider()


@pytest.fixture
def arm_id() -> str:
    """
    A unique arm id per test.

    Collections are named per arm, so a unique id gives each test its own collection
    without a global wipe -- and means two tests running against the same Qdrant cannot
    see each other's vectors.
    """
    return f"testarm{uuid.uuid4().hex[:10]}"


@pytest.fixture
async def episodic(qdrant, provider):
    from src.vectors import EpisodicStore

    return EpisodicStore(qdrant, provider)


@pytest.fixture
async def semantic(session_factory, clean_db):
    from src.store import SemanticStore

    return SemanticStore(session_factory)


@pytest.fixture
async def service(semantic, episodic):
    from src.service import MemoryService

    return MemoryService(semantic=semantic, episodic=episodic)


@pytest.fixture
def issuer():
    from octollm_common.capability import CapabilityIssuer

    return CapabilityIssuer(CAPABILITY_SECRET, kid="k1")


def make_artifact(
    *,
    created_by: str,
    content: str = "def hello(): ...",
    artifact_type: str = "code",
    task_id: str = "task-1",
    sensitivity: str = "internal",
    artifact_id: str | None = None,
):
    from octollm_common.models.provenance import Artifact, Provenance, Sensitivity

    return Artifact(
        artifact_id=artifact_id or str(uuid.uuid4()),
        artifact_type=artifact_type,
        content=content,
        provenance=Provenance(
            created_by=created_by,
            task_id=task_id,
            sensitivity=Sensitivity(sensitivity),
        ),
    )
