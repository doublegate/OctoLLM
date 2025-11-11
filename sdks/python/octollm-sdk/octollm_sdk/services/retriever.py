"""
Retriever Arm service client.

The Retriever specializes in knowledge base search and document retrieval.
"""

from typing import Optional
from ..client import BaseClient
from ..models import HealthResponse, SearchRequest, SearchResponse


class RetrieverClient(BaseClient):
    """
    Client for Retriever Arm service (port 8004).

    Performs semantic and keyword search across knowledge bases.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8004",
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Retriever client.

        Args:
            base_url: Retriever service URL (default: http://localhost:8004)
            api_key: API key for authentication
            bearer_token: JWT bearer token for authentication
            **kwargs: Additional arguments for BaseClient
        """
        super().__init__(
            base_url=base_url,
            api_key=api_key,
            bearer_token=bearer_token,
            **kwargs,
        )

    async def health(self, timeout: Optional[float] = None) -> HealthResponse:
        """Check service health."""
        response = await self.get("/health", timeout=timeout)
        return HealthResponse(**response)

    async def search(
        self,
        request: SearchRequest,
        timeout: Optional[float] = None,
    ) -> SearchResponse:
        """
        Search the knowledge base.

        Args:
            request: SearchRequest with query and search parameters
            timeout: Request timeout in seconds

        Returns:
            SearchResponse with relevant results

        Example:
            >>> from octollm_sdk import SearchRequest
            >>> request = SearchRequest(
            ...     query="nginx security vulnerabilities",
            ...     method="hybrid",
            ...     max_results=5
            ... )
            >>> results = await client.search(request)
            >>> print(f"Found {results.total_results} results")
            Found 42 results
            >>> for result in results.results:
            ...     print(f"- {result.content[:100]}... (score: {result.score:.2f})")
        """
        response = await self.post(
            "/search",
            json=request.model_dump(exclude_none=True),
            timeout=timeout,
        )
        return SearchResponse(**response)

    async def get_capabilities(self, timeout: Optional[float] = None) -> dict:
        """Get retriever capabilities."""
        response = await self.get("/capabilities", timeout=timeout)
        return response
