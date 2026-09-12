"""
The Memory / Curator arm's behaviour, separated from its wiring.

`main.py` builds the app; this holds what the app does, so both can be tested without
standing up the other.

## Two stores, one write

`remember` writes provenance to Postgres and, when the artifact is worth a vector, an
embedding to Qdrant. The Postgres write is authoritative and happens first: if the
vector write then fails, memory has lost the ability to *find* the artifact but not the
record that it existed. The reverse order would lose the audit trail while leaving a
searchable copy, which is the worse half to lose.

Neither write is wrapped in a distributed transaction, because there is no such thing
across Postgres and Qdrant, and pretending otherwise with compensating deletes would
produce a system that is wrong in more interesting ways. Instead both writes are
**idempotent**, so the recovery for a partial write is to deliver the artifact again --
which the ring does by itself.

## The diode is enforced on read, from the token

An artifact's `sensitivity` is set by its producer and stored verbatim. A recall returns
only what the caller's clearance permits, and that clearance comes from the capability
token's scope -- never from the request, which has no field for it. `withheld` reports
how many matches were suppressed, because silently returning fewer results makes a
clearance boundary look like an empty index.
"""

from __future__ import annotations

from typing import Any

import structlog
from octollm_common.models.contracts import (
    MemoryHit,
    MemoryScope,
    RecallRequest,
    RecallResponse,
    RememberRequest,
    RememberResponse,
    UsageReport,
)
from octollm_common.models.provenance import Artifact, Sensitivity

from .store import SemanticStore
from .vectors import EpisodicStore, VectorStoreError

logger = structlog.get_logger(__name__)

__all__ = ["MemoryService"]

ARM_ID = "memory"


class MemoryService:
    """Reads and writes the two halves of memory."""

    def __init__(self, *, semantic: SemanticStore, episodic: EpisodicStore) -> None:
        self._semantic = semantic
        self._episodic = episodic

    async def remember(self, request: RememberRequest, *, request_id: str) -> RememberResponse:
        """
        Commit one artifact. Idempotent, because ring delivery is at-least-once.

        `episodic_written` is reported honestly: an artifact whose vector write failed
        is recorded as `False` rather than raising, so the audit record survives and
        the caller learns the artifact is remembered but not yet findable.
        """
        artifact = request.artifact
        created = await self._semantic.remember(artifact)

        episodic = False
        if request.index_episodic and artifact.content:
            try:
                await self._episodic.index(artifact)
                episodic = True
            except VectorStoreError:
                # A dimension mismatch is a configuration error and must be loud.
                raise
            except Exception as exc:  # noqa: BLE001 - the record still stands
                logger.warning(
                    "episodic_index_failed",
                    artifact_id=artifact.artifact_id,
                    error=str(exc),
                )

        return RememberResponse(
            arm_id=ARM_ID,
            request_id=request_id,
            usage=UsageReport(provider="none", model="none"),
            # Memory reports what it did, not how sure it is: the write either
            # happened or did not, and a probability here would be theatre.
            confidence=1.0,
            artifact_id=artifact.artifact_id,
            episodic_written=episodic,
            semantic_written=True,
            duplicate=not created,
        )

    async def recall(
        self,
        request: RecallRequest,
        *,
        request_id: str,
        caller: str,
        clearance: Sensitivity,
    ) -> RecallResponse:
        """
        Search episodic memory, applying the caller's clearance.

        Args:
            caller: The arm that presented the token, used as the default store to
                search. An arm recalling its own experience is the common case, and
                making it the default means the usual request names no arm at all.
            clearance: Read from the token. See `octollm_common.security.clearance_from`.
        """
        target = request.arm_id or caller
        payloads, withheld = await self._episodic.search(
            arm_id=target,
            query=request.query,
            limit=request.top_k,
            clearance=clearance,
            task_id=request.task_id,
        )

        hits = [_hit(payload) for payload in payloads]
        logger.info(
            "memory_recall",
            caller=caller,
            target=target,
            hits=len(hits),
            withheld=withheld,
            clearance=str(clearance),
        )
        return RecallResponse(
            arm_id=ARM_ID,
            request_id=request_id,
            usage=UsageReport(provider="none", model="none"),
            # The mean hit score: a recall over an empty index is not a confident
            # answer, and reporting 1.0 for "I found nothing" would mislead a caller
            # deciding whether to trust it.
            confidence=(sum(h.score for h in hits) / len(hits)) if hits else 0.0,
            hits=hits,
            scope=MemoryScope.EPISODIC,
            withheld=withheld,
        )

    async def health(self) -> dict[str, Any]:
        """
        Readiness detail: both stores, reported separately.

        An arm that says `ready` while its database is unreachable is the same failure
        as a green check over a suite that never ran.
        """
        checks: dict[str, Any] = {}
        try:
            checks["artifacts"] = await self._semantic.count()
            checks["postgres"] = True
        except Exception as exc:  # noqa: BLE001
            checks["postgres"] = False
            checks["postgres_error"] = str(exc)
        try:
            checks["embedding_model"] = self._episodic.embedding_model
            checks["qdrant"] = True
        except Exception as exc:  # noqa: BLE001
            checks["qdrant"] = False
            checks["qdrant_error"] = str(exc)
        return checks


def _hit(payload: dict[str, Any]) -> MemoryHit:
    from datetime import UTC, datetime

    raw_created = payload.get("created_at")
    created_at = datetime.fromisoformat(str(raw_created)) if raw_created else datetime.now(UTC)
    return MemoryHit(
        artifact_id=str(payload.get("artifact_id", "")),
        artifact_type=str(payload.get("artifact_type", "")),
        content=str(payload.get("content", "")),
        score=float(payload.get("score", 0.0) or 0.0),
        created_by=str(payload.get("created_by", "")),
        task_id=str(payload.get("task_id", "")),
        sensitivity=Sensitivity(str(payload.get("sensitivity", "internal"))),
        created_at=created_at,
    )


def artifact_from(request: RememberRequest) -> Artifact:
    """The artifact a remember request carries. Named for readability at call sites."""
    return request.artifact
