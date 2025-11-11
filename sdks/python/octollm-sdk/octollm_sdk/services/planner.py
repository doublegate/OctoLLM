"""
Planner Arm service client.

The Planner specializes in task decomposition and execution planning.
"""

from typing import Optional
from ..client import BaseClient
from ..models import HealthResponse, PlanRequest, PlanResponse


class PlannerClient(BaseClient):
    """
    Client for Planner Arm service (port 8002).

    Specializes in breaking down complex goals into ordered execution steps.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8002",
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Planner client.

        Args:
            base_url: Planner service URL (default: http://localhost:8002)
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

    async def create_plan(
        self,
        request: PlanRequest,
        timeout: Optional[float] = None,
    ) -> PlanResponse:
        """
        Create an execution plan for a task.

        Args:
            request: PlanRequest with goal and constraints
            timeout: Request timeout in seconds

        Returns:
            PlanResponse with ordered execution steps

        Example:
            >>> from octollm_sdk import PlanRequest
            >>> request = PlanRequest(
            ...     goal="Research nginx vulnerabilities and create report",
            ...     constraints=["Use trusted sources only"],
            ...     acceptance_criteria=["Include at least 3 CVEs"]
            ... )
            >>> plan = await client.create_plan(request)
            >>> print(f"Plan has {len(plan.steps)} steps")
            Plan has 5 steps
            >>> for step in plan.steps:
            ...     print(f"- {step.description} (arm: {step.arm_id})")
            - Search vulnerability databases (arm: retriever)
            - Analyze CVE details (arm: coder)
            - Generate report (arm: coder)
        """
        response = await self.post(
            "/plan",
            json=request.model_dump(exclude_none=True),
            timeout=timeout,
        )
        return PlanResponse(**response)

    async def get_capabilities(self, timeout: Optional[float] = None) -> dict:
        """Get planner capabilities."""
        response = await self.get("/capabilities", timeout=timeout)
        return response
