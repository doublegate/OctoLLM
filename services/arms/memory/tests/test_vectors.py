"""
Tests for episodic memory: per-arm artifact embeddings in Qdrant.

Against a real Qdrant server, not qdrant-client's local mode. Local mode is a separate
implementation of the query language, so a payload filter combined with a vector search
is exactly the thing it might implement differently -- and that combination is where the
data diode is enforced.

Each test gets a unique `arm_id`, so each gets its own collection. That is cheaper than
a global wipe and means two tests cannot see each other's vectors.
"""

from __future__ import annotations

import pytest
from octollm_common.models.provenance import Sensitivity
from src.vectors import VectorStoreError, collection_name

from tests.conftest import make_artifact


async def cleanup(qdrant, name: str) -> None:
    if await qdrant.collection_exists(name):
        await qdrant.delete_collection(name)


# ---------------------------------------------------------------------------
# Collection naming: the embedding-model trap
# ---------------------------------------------------------------------------


def test_the_collection_name_carries_the_embedding_model() -> None:
    """
    The failure this prevents has no symptom.

    Two models of the *same* dimension produce vectors that cannot be compared, and
    swapping one for the other makes every search return plausible, meaningless scores
    with no error anywhere. Putting the model in the name makes that a new, empty
    collection instead.
    """
    a = collection_name("coder", "text-embedding-3-small")
    b = collection_name("coder", "fake-embed-1")
    assert a != b
    assert "coder" in a


def test_provider_reported_model_names_are_sanitised() -> None:
    """Providers report slashes; Qdrant collection names are path segments."""
    name = collection_name("coder", "models/embedding-001")
    assert "/" not in name
    assert name == collection_name("coder", "models/embedding-001"), "must be stable"


def test_two_arms_do_not_share_a_collection() -> None:
    """
    Episodic memory is an arm's own experience.

    One shared collection would make every recall a filtered scan over everything the
    system has ever produced.
    """
    assert collection_name("coder", "m") != collection_name("judge", "m")


# ---------------------------------------------------------------------------
# Indexing
# ---------------------------------------------------------------------------


async def test_indexing_creates_the_collection_sized_to_the_provider(
    episodic, qdrant, arm_id, provider
) -> None:
    """
    The dimension is probed from the live provider, never configured.

    A configured dimension is a second place for the truth to live, and the one that
    goes stale.
    """
    name = episodic.collection_for(arm_id)
    try:
        await episodic.index(make_artifact(created_by=arm_id))

        assert await qdrant.collection_exists(name)
        info = await qdrant.get_collection(name)
        expected = len((await provider.embed(["probe"]))[0])
        assert info.config.params.vectors.size == expected
    finally:
        await cleanup(qdrant, name)


async def test_indexing_the_same_artifact_twice_stores_one_point(episodic, qdrant, arm_id) -> None:
    """
    The point id is the artifact id, so a redelivery overwrites.

    Ring delivery is at-least-once; without this, replaying a stream would multiply
    every artifact in the index and skew every future search.
    """
    name = episodic.collection_for(arm_id)
    try:
        artifact = make_artifact(created_by=arm_id)
        await episodic.index(artifact)
        await episodic.index(artifact)

        count = await qdrant.count(collection_name=name, exact=True)
        assert count.count == 1
    finally:
        await cleanup(qdrant, name)


async def test_a_non_uuid_artifact_id_is_still_stored(episodic, qdrant, arm_id) -> None:
    """
    Qdrant point ids must be a UUID or an unsigned integer.

    Refusing to remember an artifact over the shape of its id would lose data to a
    formatting rule, so a non-UUID id is hashed into the UUID space instead.
    """
    name = episodic.collection_for(arm_id)
    try:
        await episodic.index(make_artifact(created_by=arm_id, artifact_id="not-a-uuid"))
        count = await qdrant.count(collection_name=name, exact=True)
        assert count.count == 1
    finally:
        await cleanup(qdrant, name)


async def test_a_dimension_mismatch_is_refused_rather_than_written(
    episodic, qdrant, arm_id, provider
) -> None:
    """
    The provider changing under a populated collection must be loud.

    Modelled as a **restart**, which is the only way this actually happens: a provider
    upgrades a model in place, keeping its name and changing its dimension, and the
    service comes back up against a collection the previous process created. A fresh
    `EpisodicStore` is therefore built rather than mutating the existing one, whose
    probe result is cached for the life of the process on purpose.

    Writing 8-dimension vectors into a 384-dimension collection would fail at Qdrant
    anyway; the point of checking here is the message, which names the cause instead of
    surfacing a shape error from a client library.
    """
    from src.vectors import EpisodicStore

    name = episodic.collection_for(arm_id)
    try:
        await episodic.index(make_artifact(created_by=arm_id))

        provider.embedding_dimensions = 8
        restarted = EpisodicStore(qdrant, provider)
        with pytest.raises(VectorStoreError, match="dimension"):
            await restarted.ensure_collection(arm_id)
    finally:
        provider.embedding_dimensions = 384
        await cleanup(qdrant, name)


# ---------------------------------------------------------------------------
# Search, and the data diode
# ---------------------------------------------------------------------------


async def test_searching_an_arm_that_has_remembered_nothing_is_empty_not_an_error(
    episodic, arm_id
) -> None:
    """ "Nothing remembered" is the correct answer, not a missing-collection failure."""
    hits, withheld = await episodic.search(
        arm_id=arm_id, query="anything", limit=5, clearance=Sensitivity.INTERNAL
    )
    assert hits == []
    assert withheld == 0


async def test_recall_returns_what_was_stored_with_its_provenance(episodic, qdrant, arm_id) -> None:
    name = episodic.collection_for(arm_id)
    try:
        artifact = make_artifact(created_by=arm_id, content="the quick brown fox", task_id="task-9")
        await episodic.index(artifact)

        hits, _ = await episodic.search(
            arm_id=arm_id, query="fox", limit=5, clearance=Sensitivity.INTERNAL
        )

        assert len(hits) == 1
        assert hits[0]["artifact_id"] == artifact.artifact_id
        assert hits[0]["content"] == "the quick brown fox"
        assert hits[0]["created_by"] == arm_id
        assert hits[0]["task_id"] == "task-9"
        assert 0.0 <= hits[0]["score"] <= 1.0
    finally:
        await cleanup(qdrant, name)


async def test_the_diode_withholds_material_above_the_callers_clearance(
    episodic, qdrant, arm_id
) -> None:
    """
    **The property this module exists to hold.**

    An `internal` caller must not receive `restricted` material, and must be told that
    something was withheld -- silently returning fewer results makes a clearance
    boundary look like an empty index.
    """
    name = episodic.collection_for(arm_id)
    try:
        await episodic.index(
            make_artifact(created_by=arm_id, content="public notes", sensitivity="public")
        )
        await episodic.index(
            make_artifact(created_by=arm_id, content="internal notes", sensitivity="internal")
        )
        await episodic.index(
            make_artifact(
                created_by=arm_id, content="the key rotation runbook", sensitivity="restricted"
            )
        )

        hits, withheld = await episodic.search(
            arm_id=arm_id, query="notes", limit=10, clearance=Sensitivity.INTERNAL
        )

        levels = {h["sensitivity"] for h in hits}
        assert "restricted" not in levels
        assert "confidential" not in levels
        assert levels <= {"public", "internal"}
        assert withheld == 1
    finally:
        await cleanup(qdrant, name)


async def test_a_cleared_caller_sees_everything(episodic, qdrant, arm_id) -> None:
    """The diode bounds flow; it does not withhold from someone entitled to see."""
    name = episodic.collection_for(arm_id)
    try:
        for level in ("public", "internal", "confidential", "restricted"):
            await episodic.index(
                make_artifact(created_by=arm_id, content=f"{level} notes", sensitivity=level)
            )

        hits, withheld = await episodic.search(
            arm_id=arm_id, query="notes", limit=10, clearance=Sensitivity.RESTRICTED
        )

        assert len(hits) == 4
        assert withheld == 0
    finally:
        await cleanup(qdrant, name)


async def test_the_limit_is_honoured_among_documents_the_caller_may_see(
    episodic, qdrant, arm_id
) -> None:
    """
    Filtering happens in the query, not after it.

    A post-filter over `limit` results returns fewer than asked for whenever restricted
    material ranks highly, so a caller sees a sparse index rather than a boundary.
    """
    name = episodic.collection_for(arm_id)
    try:
        for i in range(5):
            await episodic.index(
                make_artifact(
                    created_by=arm_id, content=f"restricted {i}", sensitivity="restricted"
                )
            )
        for i in range(3):
            await episodic.index(
                make_artifact(created_by=arm_id, content=f"internal {i}", sensitivity="internal")
            )

        hits, withheld = await episodic.search(
            arm_id=arm_id, query="notes", limit=3, clearance=Sensitivity.INTERNAL
        )

        assert len(hits) == 3, "the limit was consumed by documents the caller cannot see"
        assert all(h["sensitivity"] == "internal" for h in hits)
        assert withheld == 5
    finally:
        await cleanup(qdrant, name)


async def test_recall_can_be_narrowed_to_one_task(episodic, qdrant, arm_id) -> None:
    name = episodic.collection_for(arm_id)
    try:
        await episodic.index(make_artifact(created_by=arm_id, content="a", task_id="task-a"))
        await episodic.index(make_artifact(created_by=arm_id, content="b", task_id="task-b"))

        hits, _ = await episodic.search(
            arm_id=arm_id,
            query="anything",
            limit=10,
            clearance=Sensitivity.INTERNAL,
            task_id="task-a",
        )

        assert len(hits) == 1
        assert hits[0]["task_id"] == "task-a"
    finally:
        await cleanup(qdrant, name)


async def test_identical_content_embeds_identically(episodic, qdrant, arm_id, provider) -> None:
    """
    `FakeProvider.embed()` is hash-derived, so the same text always gives one vector.

    That is what makes this suite deterministic. It is also the limit of what the fake
    can do: two *different* texts get unrelated vectors, so ranking is meaningful only
    against a real embedding provider. Asserted here so the property is recorded rather
    than assumed of a search that appears to work.
    """
    first = (await provider.embed(["identical text"]))[0]
    second = (await provider.embed(["identical text"]))[0]
    assert first == second
