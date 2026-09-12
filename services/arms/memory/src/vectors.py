"""
Episodic memory: per-arm artifact embeddings in Qdrant.

Qdrant has been in the compose stack since Phase 0 and **nothing has ever read or
written it**. This module is the first thing that does, which makes it the moment the
"distributed memory" in every architecture diagram stops being a picture.

## One collection per arm

`octollm_episodic__<arm_id>__<model>`. Two decisions in that name, both load-bearing.

**Per arm**, because episodic memory is *an arm's own experience*. The Coder recalling
what it tried last time is a different question from the Judge recalling what it
rejected, and a single collection would make every recall a filtered scan over
everything the system has ever produced.

**Per embedding model**, because this is the failure that has no symptom.

## The embedding-model trap

A vector store's collection fixes its dimension at creation. Switching from a
384-dimension provider to a 1536-dimension one therefore fails loudly, which is fine --
the error names the problem.

Switching between two *different models of the same dimension* does not fail at all. The
writes succeed, the searches return results, the scores look plausible, and every one of
them is meaningless, because cosine similarity between vectors from two different models
measures nothing. There is no exception, no log line, and no test that catches it unless
something is explicitly checking.

So the model name is part of the collection name, and a collection's dimension is
verified against the live provider before anything is written to it. A model change
becomes a new, empty collection -- which is honest, because the old vectors genuinely
cannot answer questions posed in the new space.

## Dimension is probed, not configured

`LLMProvider` exposes `embedding_model` but not a dimension, and it should not: the
dimension is a property of the model, and a configured one is a second place for the
truth to live. `EpisodicStore.ensure_collection` embeds a probe string and measures the
result. One call at startup, and it cannot disagree with reality.
"""

from __future__ import annotations

import re
from typing import Any

import structlog
from octollm_common.llm.base import LLMProvider
from octollm_common.models.provenance import Artifact, Sensitivity

logger = structlog.get_logger(__name__)

__all__ = [
    "COLLECTION_PREFIX",
    "EpisodicStore",
    "VectorStoreError",
    "collection_name",
]

COLLECTION_PREFIX = "octollm_episodic"

#: Qdrant collection names are path segments. Anything outside this set is replaced so
#: that a provider reporting `text-embedding-3-small` and one reporting
#: `models/embedding-001` both produce a usable, and distinct, name.
_UNSAFE = re.compile(r"[^A-Za-z0-9_]+")

#: Embedded once per collection to measure the model's dimension. The content is
#: irrelevant; only `len()` of the result is used.
_PROBE = "octollm dimension probe"


class VectorStoreError(RuntimeError):
    """The episodic store could not answer."""


def collection_name(arm_id: str, embedding_model: str) -> str:
    """
    The collection holding one arm's episodic memory under one embedding model.

    Both components are sanitised rather than assumed safe: `arm_id` comes from the
    roster and is well-formed, but `embedding_model` is whatever a provider reports,
    and providers report slashes.
    """
    arm = _UNSAFE.sub("_", arm_id).strip("_")
    model = _UNSAFE.sub("_", embedding_model).strip("_")
    return f"{COLLECTION_PREFIX}__{arm}__{model}"


class EpisodicStore:
    """
    Artifact embeddings, one collection per (arm, embedding model).

    Args:
        client: An `AsyncQdrantClient`, or anything with the same surface. Injected so
            a test can use `AsyncQdrantClient(":memory:")` -- qdrant-client's own local
            implementation, not a hand-written double that would agree with whatever
            this module assumes.
        provider: Supplies `embed()` and `embedding_model`. `FakeProvider` by default
            everywhere, which is what lets the whole stack run with no API keys.
    """

    def __init__(self, client: Any, provider: LLMProvider) -> None:
        self._client = client
        self._provider = provider
        self._dimensions: dict[str, int] = {}

    @property
    def embedding_model(self) -> str:
        return self._provider.embedding_model

    def collection_for(self, arm_id: str) -> str:
        return collection_name(arm_id, self._provider.embedding_model)

    async def ensure_collection(self, arm_id: str) -> str:
        """
        Create the collection if absent, and verify its dimension if present.

        Returns the collection name.

        Raises:
            VectorStoreError: an existing collection's dimension does not match what
                the live provider produces. That means the provider changed under a
                populated collection, and continuing would write vectors that cannot
                be compared with the ones already there.
        """
        from qdrant_client import models as qmodels

        name = self.collection_for(arm_id)
        dimension = await self._probe_dimensions()

        if await self._client.collection_exists(name):
            existing = await self._existing_dimension(name)
            if existing is not None and existing != dimension:
                raise VectorStoreError(
                    f"Collection {name} holds {existing}-dimension vectors but the "
                    f"configured provider produces {dimension}. The embedding model "
                    "changed under a populated collection; recall across the two "
                    "would be meaningless. Re-index, or configure the original model."
                )
            return name

        await self._client.create_collection(
            collection_name=name,
            vectors_config=qmodels.VectorParams(size=dimension, distance=qmodels.Distance.COSINE),
        )
        logger.info(
            "episodic_collection_created",
            collection=name,
            arm_id=arm_id,
            dimensions=dimension,
            embedding_model=self._provider.embedding_model,
        )
        return name

    async def _probe_dimensions(self) -> int:
        model = self._provider.embedding_model
        cached = self._dimensions.get(model)
        if cached is not None:
            return cached
        vectors = await self._provider.embed([_PROBE])
        if not vectors or not vectors[0]:
            raise VectorStoreError(
                f"Provider {model!r} returned an empty embedding for a probe string. "
                "A vector store cannot be sized against a provider that embeds nothing."
            )
        self._dimensions[model] = len(vectors[0])
        return self._dimensions[model]

    async def _existing_dimension(self, name: str) -> int | None:
        try:
            info = await self._client.get_collection(name)
        except Exception as exc:  # noqa: BLE001 - any failure means "cannot verify"
            logger.warning("episodic_collection_probe_failed", collection=name, error=str(exc))
            return None
        params = getattr(getattr(info, "config", None), "params", None)
        vectors = getattr(params, "vectors", None)
        size = getattr(vectors, "size", None)
        return int(size) if isinstance(size, int) else None

    async def index(self, artifact: Artifact) -> str:
        """
        Embed and store one artifact in its producer's collection.

        The point id is the artifact id, so a redelivery overwrites rather than
        duplicating -- ring delivery is at-least-once and this is what makes indexing
        idempotent at the vector store as well as at the database.

        Returns the collection name written to.
        """
        from qdrant_client import models as qmodels

        arm_id = artifact.provenance.created_by
        name = await self.ensure_collection(arm_id)
        vector = (await self._provider.embed([artifact.content]))[0]

        await self._client.upsert(
            collection_name=name,
            points=[
                qmodels.PointStruct(
                    id=_point_id(artifact.artifact_id),
                    vector=vector,
                    payload={
                        "artifact_id": artifact.artifact_id,
                        "artifact_type": artifact.artifact_type,
                        "content": artifact.content,
                        "created_by": arm_id,
                        "task_id": artifact.provenance.task_id,
                        "sensitivity": str(artifact.provenance.sensitivity),
                        "created_at": artifact.provenance.created_at.isoformat(),
                        "content_sha256": artifact.content_sha256,
                    },
                )
            ],
        )
        return name

    async def search(
        self,
        *,
        arm_id: str,
        query: str,
        limit: int,
        clearance: Sensitivity,
        task_id: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        """
        Similarity search, with the data diode applied **in the query**.

        Returns `(payloads, withheld)` where `withheld` counts matches suppressed by
        clearance.

        The clearance filter is a Qdrant filter rather than a post-filter in Python.
        That matters for a reason beyond efficiency: a post-filter over `limit` results
        silently returns fewer than asked for whenever restricted material ranks highly,
        so the caller sees a sparse index rather than a clearance boundary. Filtering in
        the query means `limit` is honoured among the documents the caller may see.

        `withheld` is then measured by a second, unfiltered count -- which is the only
        way to report that something exists without revealing what.
        """
        from qdrant_client import models as qmodels

        name = self.collection_for(arm_id)
        if not await self._client.collection_exists(name):
            # Not an error: an arm that has never produced anything has no collection,
            # and "nothing remembered" is the correct answer to that.
            return [], 0

        vector = (await self._provider.embed([query]))[0]
        permitted = [s.value for s in Sensitivity if _permits(s, clearance)]

        must: list[Any] = [
            qmodels.FieldCondition(key="sensitivity", match=qmodels.MatchAny(any=permitted))
        ]
        if task_id:
            must.append(
                qmodels.FieldCondition(key="task_id", match=qmodels.MatchValue(value=task_id))
            )

        response = await self._client.query_points(
            collection_name=name,
            query=vector,
            query_filter=qmodels.Filter(must=must),
            limit=limit,
            with_payload=True,
        )
        points = list(getattr(response, "points", []) or [])
        payloads = [{**(p.payload or {}), "score": _clamp(p.score)} for p in points]

        withheld = await self._count_withheld(name, permitted, task_id)
        return payloads, withheld

    async def _count_withheld(self, name: str, permitted: list[str], task_id: str | None) -> int:
        """How many stored points the caller's clearance excludes."""
        from qdrant_client import models as qmodels

        must_not: list[Any] = [
            qmodels.FieldCondition(key="sensitivity", match=qmodels.MatchAny(any=permitted))
        ]
        must: list[Any] = []
        if task_id:
            must.append(
                qmodels.FieldCondition(key="task_id", match=qmodels.MatchValue(value=task_id))
            )
        try:
            result = await self._client.count(
                collection_name=name,
                count_filter=qmodels.Filter(must=must, must_not=must_not),
                exact=True,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("episodic_withheld_count_failed", collection=name, error=str(exc))
            return 0
        return int(getattr(result, "count", 0))


def _permits(artifact: Sensitivity, clearance: Sensitivity) -> bool:
    from octollm_common.models.provenance import may_flow_to

    return may_flow_to(artifact, clearance)


def _clamp(score: float | None) -> float:
    """
    Cosine similarity is [-1, 1]; the contract's `score` is [0, 1].

    Clamped rather than rescaled: a negative cosine means "unrelated, and pointing the
    other way", which is not usefully different from "unrelated" to a caller ranking
    results. Rescaling would make an unrelated document score 0.5.
    """
    if score is None:
        return 0.0
    return max(0.0, min(1.0, float(score)))


def _point_id(artifact_id: str) -> str | int:
    """
    Qdrant point ids must be a UUID or an unsigned integer.

    Artifact ids are UUIDs everywhere in this system, so they pass through. Anything
    else is hashed into the UUID space rather than rejected, because refusing to
    remember an artifact over the shape of its id would lose data to a formatting rule.
    """
    import uuid

    try:
        return str(uuid.UUID(artifact_id))
    except ValueError, AttributeError, TypeError:
        return str(uuid.uuid5(uuid.NAMESPACE_URL, f"octollm:artifact:{artifact_id}"))
