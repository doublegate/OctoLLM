"""
Memory / Curator Arm service client.

Memory owns storage for the whole system: episodic vectors in Qdrant, semantic
provenance in PostgreSQL. It is the Retriever's corpus, which is why it lands first.

Both calls require a **capability token** signed by the orchestrator, with `aud` of
`memory` and a matching `X-Task-Id` header. Memory holds every arm's output, so an open
recall endpoint would be a read of the whole system's work.
"""

from typing import Any

from ..client import BaseClient
from ..models import HealthResponse


class MemoryClient(BaseClient):
    """
    Client for the Memory / Curator Arm (port 8007).

    Two write paths exist; this is the synchronous one. The other is the Neural Ring,
    which Memory consumes without anyone calling it.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8007",
        api_key: str | None = None,
        bearer_token: str | None = None,
        **kwargs: Any,
    ):
        """
        Initialize the Memory client.

        Args:
            base_url: Memory service URL (default: http://localhost:8007)
            api_key: API key for authentication
            bearer_token: The capability token the orchestrator signed
            **kwargs: Additional arguments for BaseClient
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            bearer_token=bearer_token,
            **kwargs,
        )

    async def health(self, timeout: float | None = None) -> HealthResponse:
        """Check service health. Needs no token."""
        response = await self.get("/health", timeout=timeout)
        return HealthResponse(**response)

    async def recall(
        self,
        query: str,
        *,
        task_id: str,
        top_k: int = 10,
        arm_id: str | None = None,
        timeout: float | None = None,
    ) -> dict:
        """
        Search episodic memory.

        Args:
            query: What to search for.
            task_id: Sent as `X-Task-Id` and must match the token's `task_id`.
            top_k: How many hits to return.
            arm_id: Whose memory to search. Defaults to the token's subject, because
                an arm recalling its own experience is the common case.

        Returns:
            A `RecallResponse` with `hits` and `withheld`.

        Note:
            There is deliberately **no clearance argument**. Sensitivity is read from
            the capability token, never from the request -- a caller that states its
            own clearance is an escalation with extra steps. `withheld` tells you how
            many matches your clearance excluded.
        """
        body: dict[str, Any] = {"query": query, "top_k": top_k, "task_id": task_id}
        if arm_id is not None:
            body["arm_id"] = arm_id
        return await self.post(
            "/recall", json=body, headers={"X-Task-Id": task_id}, timeout=timeout
        )

    async def remember(
        self,
        artifact: dict,
        *,
        task_id: str,
        index_episodic: bool = True,
        timeout: float | None = None,
    ) -> dict:
        """
        Commit one artifact to memory.

        Idempotent: a second write of the same `artifact_id` returns 200 with
        `duplicate: true`, not a conflict. Ring delivery is at-least-once, so a
        redelivery is expected rather than exceptional.

        Args:
            artifact: The artifact, including its provenance and `sensitivity`.
            task_id: Sent as `X-Task-Id` and must match the token's `task_id`.
            index_episodic: Embed and index it. False records provenance only.
        """
        return await self.post(
            "/remember",
            json={
                "artifact": artifact,
                "index_episodic": index_episodic,
                "task_id": task_id,
            },
            headers={"X-Task-Id": task_id},
            timeout=timeout,
        )

    async def get_capabilities(self, timeout: float | None = None) -> dict:
        """Get this arm's declaration, including its ring topology. Needs no token."""
        return await self.get("/capabilities", timeout=timeout)
