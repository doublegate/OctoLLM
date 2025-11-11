"""
Judge Arm service client.

The Judge specializes in output validation and quality assurance.
"""

from typing import Optional
from ..client import BaseClient
from ..models import HealthResponse, ValidationRequest, ValidationResult


class JudgeClient(BaseClient):
    """
    Client for Judge Arm service (port 8006).

    Validates task outputs against acceptance criteria and quality standards.
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8006",
        api_key: Optional[str] = None,
        bearer_token: Optional[str] = None,
        **kwargs
    ):
        """
        Initialize Judge client.

        Args:
            base_url: Judge service URL (default: http://localhost:8006)
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

    async def validate(
        self,
        request: ValidationRequest,
        timeout: Optional[float] = None,
    ) -> ValidationResult:
        """
        Validate task output.

        Args:
            request: ValidationRequest with output and acceptance criteria
            timeout: Request timeout in seconds

        Returns:
            ValidationResult with validation status and issues

        Example:
            >>> from octollm_sdk import ValidationRequest
            >>> request = ValidationRequest(
            ...     output="def validate_email(email):\\n    return '@' in email",
            ...     acceptance_criteria=[
            ...         "Function includes type hints",
            ...         "Function includes docstring",
            ...         "Function handles edge cases"
            ...     ],
            ...     output_type="python_code"
            ... )
            >>> result = await client.validate(request)
            >>> print(f"Valid: {result.valid}")
            Valid: False
            >>> print(f"Failed criteria: {result.failed_criteria}")
            Failed criteria: ['Function includes type hints', 'Function includes docstring']
            >>> for issue in result.issues:
            ...     print(f"- [{issue.severity}] {issue.message}")
            - [high] Missing type hints for parameters and return value
            - [medium] Missing docstring explaining function purpose
        """
        response = await self.post(
            "/validate",
            json=request.model_dump(exclude_none=True),
            timeout=timeout,
        )
        return ValidationResult(**response)

    async def get_capabilities(self, timeout: Optional[float] = None) -> dict:
        """Get judge capabilities."""
        response = await self.get("/capabilities", timeout=timeout)
        return response
