"""
OctoLLM Python SDK

Official Python client library for the OctoLLM distributed AI architecture.

Basic Usage:
    ```python
    from octollm_sdk import OrchestratorClient, TaskRequest, ResourceBudget

    # Initialize client
    client = OrchestratorClient(
        base_url="http://localhost:8000",
        api_key="your-api-key"
    )

    # Submit a task
    task = TaskRequest(
        goal="Create a Python function to validate emails",
        constraints=["Include type hints", "Add docstring"],
        budget=ResourceBudget(max_tokens=5000)
    )
    response = await client.submit_task(task)

    # Get task status
    result = await client.get_task(response.task_id)
    print(result.result.output if result.result else "Still processing...")
    ```

Version: 0.4.0
"""

__version__ = "0.5.0"
__author__ = "OctoLLM Core Team"
__license__ = "Apache-2.0"

# Configuration
from .config import OctoLLMConfig

# Exceptions
from .exceptions import (
    APIError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    OctoLLMError,
    RateLimitError,
    ServiceUnavailableError,
    TimeoutError,
    ValidationError,
)

# Models
from .models import (  # Core task models; Reflex models; Planner models; Executor models; Retriever models; Coder models; Judge models; Safety models; Common models
    ArmCapability,
    CacheStats,
    CodeRequest,
    CodeResponse,
    ErrorResponse,
    ExecutionRequest,
    ExecutionResult,
    HealthResponse,
    PlanRequest,
    PlanResponse,
    PlanStep,
    PreprocessRequest,
    PreprocessResponse,
    ResourceBudget,
    SafetyIssue,
    SafetyRequest,
    SafetyResult,
    SearchRequest,
    SearchResponse,
    SearchResult,
    TaskRequest,
    TaskResponse,
    TaskStatusResponse,
    ValidationIssue,
    ValidationRequest,
    ValidationResult,
)

# Service clients
from .services import (
    CoderClient,
    ExecutorClient,
    JudgeClient,
    OrchestratorClient,
    PlannerClient,
    ReflexClient,
    RetrieverClient,
    SafetyGuardianClient,
)

__all__ = [
    "APIError",
    "ArmCapability",
    "AuthenticationError",
    "AuthorizationError",
    "CacheStats",
    "CodeRequest",
    "CodeResponse",
    "CoderClient",
    "ErrorResponse",
    "ExecutionRequest",
    "ExecutionResult",
    "ExecutorClient",
    "HealthResponse",
    "JudgeClient",
    "NotFoundError",
    "OctoLLMConfig",
    "OctoLLMError",
    "OrchestratorClient",
    "PlanRequest",
    "PlanResponse",
    "PlanStep",
    "PlannerClient",
    "PreprocessRequest",
    "PreprocessResponse",
    "RateLimitError",
    "ReflexClient",
    "ResourceBudget",
    "RetrieverClient",
    "SafetyGuardianClient",
    "SafetyIssue",
    "SafetyRequest",
    "SafetyResult",
    "SearchRequest",
    "SearchResponse",
    "SearchResult",
    "ServiceUnavailableError",
    "TaskRequest",
    "TaskResponse",
    "TaskStatusResponse",
    "TimeoutError",
    "ValidationError",
    "ValidationIssue",
    "ValidationRequest",
    "ValidationResult",
]
