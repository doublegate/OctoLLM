"""
Pydantic models for OctoLLM SDK.

All request and response models match the OpenAPI 3.0 specifications.
"""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

# ============================================================================
# Core Task Models (Orchestrator)
# ============================================================================


class ResourceBudget(BaseModel):
    """Resource budget constraints for task execution."""

    max_tokens: int = Field(
        default=10000,
        ge=100,
        le=100000,
        description="Maximum LLM tokens to use",
    )
    max_time_seconds: int = Field(
        default=60, ge=5, le=300, description="Maximum execution time in seconds"
    )
    max_cost_dollars: float = Field(
        default=1.0, ge=0.01, le=10.0, description="Maximum cost in USD"
    )


class TaskRequest(BaseModel):
    """Request to submit a new task to the orchestrator."""

    goal: str = Field(
        ...,
        min_length=10,
        max_length=2000,
        description="Natural language description of the task objective",
    )
    constraints: Optional[List[str]] = Field(
        default=None, description="Hard constraints that must be satisfied"
    )
    acceptance_criteria: Optional[List[str]] = Field(
        default=None, description="Success conditions for validation"
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Additional context and metadata"
    )
    budget: Optional[ResourceBudget] = Field(
        default=None, description="Resource budget constraints"
    )


class TaskResponse(BaseModel):
    """Response after submitting a task."""

    task_id: str = Field(
        ..., pattern=r"^task_[a-zA-Z0-9]{16}$", description="Unique task identifier"
    )
    status: Literal["queued", "processing", "completed", "failed", "cancelled"] = Field(
        ..., description="Current task status"
    )
    created_at: datetime = Field(..., description="Task creation timestamp")
    estimated_completion: Optional[datetime] = Field(
        default=None, description="Estimated completion time"
    )


class TaskProgress(BaseModel):
    """Task progress information."""

    current_step: Literal["preprocessing", "planning", "execution", "validation", "synthesis"] = (
        Field(..., description="Current processing step")
    )
    completed_steps: int = Field(..., description="Number of completed steps")
    total_steps: int = Field(..., description="Total number of steps")
    percentage: int = Field(..., ge=0, le=100, description="Progress percentage")


class TaskResult(BaseModel):
    """Task execution result."""

    output: str = Field(..., description="Primary output")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    validation_passed: bool = Field(..., description="Whether output passed validation")


class TaskError(BaseModel):
    """Task error information."""

    type: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[str] = Field(default=None, description="Additional error details")


class TaskMetadata(BaseModel):
    """Task execution metadata."""

    arms_used: List[str] = Field(..., description="Arms used in task execution")
    tokens_used: int = Field(..., description="Total tokens consumed")
    cost_dollars: float = Field(..., description="Total cost in USD")
    duration_seconds: float = Field(..., description="Execution duration")


class TaskStatusResponse(BaseModel):
    """Detailed task status response."""

    task_id: str = Field(..., pattern=r"^task_[a-zA-Z0-9]{16}$")
    status: Literal["queued", "processing", "completed", "failed", "cancelled"]
    progress: Optional[TaskProgress] = None
    result: Optional[TaskResult] = None
    error: Optional[TaskError] = None
    metadata: Optional[TaskMetadata] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None


# ============================================================================
# Arm Capability Models
# ============================================================================


class ArmCapability(BaseModel):
    """Arm registration and capability information."""

    arm_id: str = Field(..., description="Unique arm identifier")
    name: str = Field(..., description="Human-readable arm name")
    description: str = Field(..., description="Arm purpose and capabilities")
    capabilities: List[str] = Field(..., description="List of capabilities")
    cost_tier: int = Field(..., ge=1, le=5, description="Cost tier (1=cheap, 5=expensive)")
    endpoint: str = Field(..., description="Service endpoint URL")
    status: Literal["healthy", "degraded", "unavailable"] = Field(
        ..., description="Current arm status"
    )


# ============================================================================
# Reflex Layer Models
# ============================================================================


class PreprocessRequest(BaseModel):
    """Request to preprocess incoming data."""

    input_text: str = Field(..., min_length=1, max_length=50000, description="Text to preprocess")
    check_cache: bool = Field(
        default=True, description="Whether to check cache for similar requests"
    )
    detect_pii: bool = Field(default=True, description="Whether to detect PII in input")
    detect_injection: bool = Field(
        default=True, description="Whether to detect prompt injection attempts"
    )


class PreprocessResponse(BaseModel):
    """Preprocessing result."""

    cache_hit: bool = Field(..., description="Whether cache hit occurred")
    cached_result: Optional[Dict[str, Any]] = Field(
        default=None, description="Cached result if cache hit"
    )
    pii_detected: bool = Field(..., description="Whether PII was detected")
    pii_types: List[str] = Field(default_factory=list, description="Types of PII detected")
    injection_detected: bool = Field(..., description="Whether prompt injection was detected")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Risk score (0=safe, 1=high risk)")
    sanitized_input: str = Field(..., description="Sanitized input text")
    should_proceed: bool = Field(..., description="Whether request should proceed to orchestrator")


class CacheStats(BaseModel):
    """Cache statistics."""

    total_entries: int = Field(..., description="Total cache entries")
    hit_rate: float = Field(..., ge=0.0, le=1.0, description="Cache hit rate")
    memory_usage_mb: float = Field(..., description="Memory usage in MB")
    eviction_count: int = Field(..., description="Number of evictions")


# ============================================================================
# Planner Arm Models
# ============================================================================


class PlanStep(BaseModel):
    """A single step in an execution plan."""

    step_id: str = Field(..., description="Unique step identifier")
    description: str = Field(..., description="Step description")
    arm_id: str = Field(..., description="Target arm for execution")
    dependencies: List[str] = Field(default_factory=list, description="IDs of prerequisite steps")
    input_mapping: Dict[str, str] = Field(
        default_factory=dict, description="Input parameter mappings"
    )
    expected_output: Optional[str] = Field(
        default=None, description="Description of expected output"
    )


class PlanRequest(BaseModel):
    """Request to create an execution plan."""

    goal: str = Field(..., min_length=10, max_length=2000, description="Task goal to plan for")
    constraints: Optional[List[str]] = Field(default=None, description="Task constraints")
    acceptance_criteria: Optional[List[str]] = Field(default=None, description="Success criteria")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class PlanResponse(BaseModel):
    """Execution plan result."""

    plan_id: str = Field(..., description="Unique plan identifier")
    steps: List[PlanStep] = Field(..., description="Ordered execution steps")
    estimated_duration_seconds: int = Field(..., description="Estimated execution duration")
    estimated_cost_dollars: float = Field(..., description="Estimated cost")
    complexity_score: float = Field(
        ..., ge=0.0, le=1.0, description="Plan complexity (0=simple, 1=complex)"
    )
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in plan success")


# ============================================================================
# Executor Arm Models
# ============================================================================


class ExecutionRequest(BaseModel):
    """Request to execute a command or script."""

    command: str = Field(..., description="Command to execute")
    command_type: Literal["shell", "python", "http", "tool"] = Field(
        ..., description="Type of command"
    )
    args: Optional[List[str]] = Field(default=None, description="Command arguments")
    env: Optional[Dict[str, str]] = Field(default=None, description="Environment variables")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Execution timeout")
    allow_network: bool = Field(default=False, description="Whether to allow network access")


class ExecutionResult(BaseModel):
    """Command execution result."""

    success: bool = Field(..., description="Whether execution succeeded")
    exit_code: int = Field(..., description="Process exit code")
    stdout: str = Field(..., description="Standard output")
    stderr: str = Field(..., description="Standard error")
    duration_seconds: float = Field(..., description="Execution duration")
    sandbox_info: Dict[str, Any] = Field(..., description="Sandbox container information")


# ============================================================================
# Retriever Arm Models
# ============================================================================


class SearchRequest(BaseModel):
    """Request to search knowledge base."""

    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    method: Literal["vector", "keyword", "hybrid"] = Field(
        default="hybrid", description="Search method"
    )
    max_results: int = Field(default=10, ge=1, le=100, description="Maximum results")
    min_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum relevance score")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Additional filters")


class SearchResult(BaseModel):
    """A single search result."""

    result_id: str = Field(..., description="Result identifier")
    content: str = Field(..., description="Result content")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    source: str = Field(..., description="Source identifier")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SearchResponse(BaseModel):
    """Search results."""

    results: List[SearchResult] = Field(..., description="Search results")
    query: str = Field(..., description="Original query")
    method_used: Literal["vector", "keyword", "hybrid"] = Field(
        ..., description="Search method used"
    )
    total_results: int = Field(..., description="Total matching results")
    synthesis: Optional[str] = Field(default=None, description="Synthesized summary of results")
    citations: List[str] = Field(default_factory=list, description="Source citations")


# ============================================================================
# Coder Arm Models
# ============================================================================


class CodeRequest(BaseModel):
    """Request for code generation, debugging, or refactoring."""

    operation: Literal["generate", "debug", "refactor", "explain"] = Field(
        ..., description="Code operation type"
    )
    prompt: str = Field(..., min_length=10, max_length=5000, description="Code generation prompt")
    language: str = Field(..., description="Programming language")
    existing_code: Optional[str] = Field(
        default=None, description="Existing code (for debug/refactor)"
    )
    style_guide: Optional[str] = Field(default=None, description="Code style guidelines")
    include_tests: bool = Field(default=False, description="Whether to generate tests")
    include_docstrings: bool = Field(default=True, description="Whether to include docstrings")


class CodeResponse(BaseModel):
    """Code generation result."""

    success: bool = Field(..., description="Whether operation succeeded")
    code: str = Field(..., description="Generated/modified code")
    explanation: str = Field(..., description="Explanation of code/changes")
    language: str = Field(..., description="Programming language")
    tests: Optional[str] = Field(default=None, description="Generated tests")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in code quality")
    warnings: List[str] = Field(default_factory=list, description="Warnings or caveats")


# ============================================================================
# Judge Arm Models
# ============================================================================


class ValidationIssue(BaseModel):
    """A single validation issue."""

    severity: Literal["critical", "high", "medium", "low"] = Field(
        ..., description="Issue severity"
    )
    category: str = Field(..., description="Issue category")
    message: str = Field(..., description="Issue description")
    location: Optional[str] = Field(default=None, description="Location in output")
    suggestion: Optional[str] = Field(default=None, description="Suggested fix")


class ValidationRequest(BaseModel):
    """Request to validate task output."""

    output: str = Field(..., description="Output to validate")
    acceptance_criteria: Optional[List[str]] = Field(
        default=None, description="Criteria to check against"
    )
    output_type: Optional[str] = Field(default=None, description="Expected output type")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Validation context")


class ValidationResult(BaseModel):
    """Validation result."""

    valid: bool = Field(..., description="Whether output is valid")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in validation")
    issues: List[ValidationIssue] = Field(
        default_factory=list, description="Validation issues found"
    )
    passed_criteria: List[str] = Field(default_factory=list, description="Criteria that passed")
    failed_criteria: List[str] = Field(default_factory=list, description="Criteria that failed")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


# ============================================================================
# Safety Guardian Arm Models
# ============================================================================


class SafetyIssue(BaseModel):
    """A detected safety issue."""

    issue_type: Literal["pii", "injection", "harmful_content", "policy_violation"] = Field(
        ..., description="Type of safety issue"
    )
    severity: Literal["critical", "high", "medium", "low"] = Field(
        ..., description="Issue severity"
    )
    description: str = Field(..., description="Issue description")
    location: Optional[str] = Field(default=None, description="Location in text")
    detected_value: Optional[str] = Field(
        default=None, description="Detected sensitive value (redacted)"
    )


class SafetyRequest(BaseModel):
    """Request for safety check."""

    content: str = Field(..., description="Content to check")
    check_types: List[Literal["pii", "injection", "harmful_content", "policy_violation"]] = Field(
        default=["pii", "injection", "harmful_content"],
        description="Types of checks to perform",
    )
    sanitize: bool = Field(default=True, description="Whether to sanitize detected issues")


class SafetyResult(BaseModel):
    """Safety check result."""

    safe: bool = Field(..., description="Whether content is safe")
    issues: List[SafetyIssue] = Field(default_factory=list, description="Detected safety issues")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Overall risk score")
    sanitized_content: Optional[str] = Field(
        default=None, description="Sanitized version of content"
    )
    should_proceed: bool = Field(..., description="Whether processing should proceed")


# ============================================================================
# Common Response Models
# ============================================================================


class HealthResponse(BaseModel):
    """Service health status."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime_seconds: int = Field(..., description="Service uptime in seconds")
    components: Optional[Dict[str, str]] = Field(
        default=None, description="Component health status"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    retry_after: Optional[int] = Field(
        default=None, description="Retry after seconds (for rate limits)"
    )
    request_id: Optional[str] = Field(default=None, description="Request ID for debugging")


class ProvenanceMetadata(BaseModel):
    """Provenance tracking metadata."""

    arm_id: str = Field(..., description="Arm that produced output")
    timestamp: datetime = Field(..., description="Output generation timestamp")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    command_hash: Optional[str] = Field(
        default=None, description="Hash of executed command (for reproducibility)"
    )
    model_name: Optional[str] = Field(default=None, description="LLM model name (if applicable)")
    model_version: Optional[str] = Field(default=None, description="LLM model version")
