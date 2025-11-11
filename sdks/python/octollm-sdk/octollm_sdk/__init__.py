"""
OctoLLM Python SDK

Official Python client library for the OctoLLM distributed AI architecture.

Basic Usage:
    ```python
    from octollm_sdk import OctoLLMClient

    # Initialize client
    client = OctoLLMClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )

    # Submit a task
    task = await client.orchestrator.create_task(
        goal="Create a Python function to validate emails",
        constraints=["Include type hints", "Add docstring"]
    )

    # Get task status
    result = await client.orchestrator.get_task(task.task_id)
    print(result.result.output)
    ```

Version: 0.3.0
"""

__version__ = "0.3.0"
__author__ = "OctoLLM Core Team"
__license__ = "Apache-2.0"

from .client import OctoLLMClient
from .models import (
    TaskRequest,
    TaskResponse,
    ResourceBudget,
    CodeRequest,
    CodeResponse,
    SearchRequest,
    SearchResponse,
    ValidationRequest,
    ValidationResult,
    SafetyRequest,
    SafetyResult,
)
from .exceptions import (
    OctoLLMError,
    AuthenticationError,
    ValidationError,
    RateLimitError,
    ServiceUnavailableError,
    NotFoundError,
)

__all__ = [
    "OctoLLMClient",
    # Models
    "TaskRequest",
    "TaskResponse",
    "ResourceBudget",
    "CodeRequest",
    "CodeResponse",
    "SearchRequest",
    "SearchResponse",
    "ValidationRequest",
    "ValidationResult",
    "SafetyRequest",
    "SafetyResult",
    # Exceptions
    "OctoLLMError",
    "AuthenticationError",
    "ValidationError",
    "RateLimitError",
    "ServiceUnavailableError",
    "NotFoundError",
]
