"""
Pydantic models for OctoLLM SDK.

All request and response models match the OpenAPI 3.0 specifications.
"""

from datetime import datetime
from typing import Any, Literal

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
    constraints: list[str] | None = Field(
        default=None, description="Hard constraints that must be satisfied"
    )
    acceptance_criteria: list[str] | None = Field(
        default=None, description="Success conditions for validation"
    )
    context: dict[str, Any] | None = Field(
        default=None, description="Additional context and metadata"
    )
    budget: ResourceBudget | None = Field(default=None, description="Resource budget constraints")


class TaskResponse(BaseModel):
    """Response after submitting a task."""

    task_id: str = Field(
        ..., pattern=r"^task_[a-zA-Z0-9]{16}$", description="Unique task identifier"
    )
    status: Literal["queued", "processing", "completed", "failed", "cancelled"] = Field(
        ..., description="Current task status"
    )
    created_at: datetime = Field(..., description="Task creation timestamp")
    estimated_completion: datetime | None = Field(
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
    details: str | None = Field(default=None, description="Additional error details")


class TaskMetadata(BaseModel):
    """Task execution metadata."""

    arms_used: list[str] = Field(..., description="Arms used in task execution")
    tokens_used: int = Field(..., description="Total tokens consumed")
    cost_dollars: float = Field(..., description="Total cost in USD")
    duration_seconds: float = Field(..., description="Execution duration")


class TaskStatusResponse(BaseModel):
    """Detailed task status response."""

    task_id: str = Field(..., pattern=r"^task_[a-zA-Z0-9]{16}$")
    status: Literal["queued", "processing", "completed", "failed", "cancelled"]
    progress: TaskProgress | None = None
    result: TaskResult | None = None
    error: TaskError | None = None
    metadata: TaskMetadata | None = None
    created_at: datetime
    updated_at: datetime | None = None
    completed_at: datetime | None = None
    failed_at: datetime | None = None


# ============================================================================
# Arm Capability Models
# ============================================================================


class ArmCapability(BaseModel):
    """
    Arm registration and capability information, as `GET /arms` returns it.

    Three shapes of this existed and disagreed: this model carried a `status` and no
    schemas, the TypeScript SDK carried `input_schema`/`output_schema` and no status,
    and no endpoint served either. This is the frozen shape -- the union of what is
    actually knowable -- and it is what the orchestrator's registry returns.
    """

    arm_id: str = Field(..., description="Unique arm identifier")
    name: str = Field(..., description="Human-readable arm name")
    description: str = Field(..., description="Arm purpose and capabilities")
    capabilities: list[str] = Field(default_factory=list, description="Routing tags")
    cost_tier: int = Field(..., ge=1, le=5, description="Cost tier (1=cheap, 5=expensive)")

    # `endpoint` is the PATH on the arm; `base_url` is where the arm listens. This
    # field was documented as "Service endpoint URL" while every arm returns a path --
    # two meanings under one name is how a client builds `http://hosthttp://host/plan`.
    endpoint: str = Field(..., description="Path on the arm, e.g. '/plan'")
    base_url: str = Field(..., description="Where the arm listens")
    port: int = Field(..., ge=1, le=65535, description="Container port")

    input_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema of the request, generated from the contract"
    )
    output_schema: dict[str, Any] = Field(
        default_factory=dict, description="JSON Schema of the response"
    )

    implemented: bool = Field(..., description="Whether the endpoint does anything yet")
    implemented_in_stage: int = Field(..., description="Which v1.0.0 stage builds it")

    publishes: list[str] = Field(default_factory=list, description="Ring artifact types produced")
    subscribes: list[str] = Field(default_factory=list, description="Ring artifact types consumed")
    peers: list[str] = Field(default_factory=list, description="Arms this one may call directly")

    status: Literal["healthy", "degraded", "unavailable"] = Field(
        "unavailable", description="Result of the orchestrator's last probe"
    )
    last_probed_at: datetime | None = Field(None, description="None if never probed")


class RegisterArmRequest(BaseModel):
    """
    What `POST /arms/register` accepts.

    Registration **updates** an arm already in the roster; it cannot introduce one.
    Every field but `arm_id` is optional, and an omitted field is left alone rather
    than cleared -- the difference between PATCH and PUT semantics is not academic
    when the cleared field is what routing matches on.

    `port`, `endpoint` and `cost_tier` are absent on purpose: they are roster facts,
    and an arm able to restate them could redirect its own traffic.
    """

    arm_id: str = Field(..., min_length=1, description="Must already be in the roster")
    base_url: str | None = Field(None, description="Override where this arm listens")
    capabilities: list[str] | None = Field(None, description="Replaces the routing tags")
    implemented: bool | None = Field(None, description="Whether the endpoint works yet")
    publishes: list[str] | None = Field(None, description="Ring artifact types produced")
    subscribes: list[str] | None = Field(None, description="Ring artifact types consumed")
    peers: list[str] | None = Field(None, description="Declared ring edges; advisory")


class RegisterArmResponse(BaseModel):
    """Result of a registration."""

    status: Literal["updated"] = Field(
        "updated", description="Always 'updated': registration cannot introduce an arm"
    )
    arm: ArmCapability = Field(..., description="The arm as the registry now holds it")


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
    cached_result: dict[str, Any] | None = Field(
        default=None, description="Cached result if cache hit"
    )
    pii_detected: bool = Field(..., description="Whether PII was detected")
    pii_types: list[str] = Field(default_factory=list, description="Types of PII detected")
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
    dependencies: list[str] = Field(default_factory=list, description="IDs of prerequisite steps")
    input_mapping: dict[str, str] = Field(
        default_factory=dict, description="Input parameter mappings"
    )
    expected_output: str | None = Field(default=None, description="Description of expected output")


class PlanRequest(BaseModel):
    """Request to create an execution plan."""

    goal: str = Field(..., min_length=10, max_length=2000, description="Task goal to plan for")
    constraints: list[str] | None = Field(default=None, description="Task constraints")
    acceptance_criteria: list[str] | None = Field(default=None, description="Success criteria")
    context: dict[str, Any] | None = Field(default=None, description="Additional context")


class PlanResponse(BaseModel):
    """Execution plan result."""

    plan_id: str = Field(..., description="Unique plan identifier")
    steps: list[PlanStep] = Field(..., description="Ordered execution steps")
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
    args: list[str] | None = Field(default=None, description="Command arguments")
    env: dict[str, str] | None = Field(default=None, description="Environment variables")
    timeout_seconds: int = Field(default=30, ge=1, le=300, description="Execution timeout")
    allow_network: bool = Field(default=False, description="Whether to allow network access")


class ExecutionResult(BaseModel):
    """Command execution result."""

    success: bool = Field(..., description="Whether execution succeeded")
    exit_code: int = Field(..., description="Process exit code")
    stdout: str = Field(..., description="Standard output")
    stderr: str = Field(..., description="Standard error")
    duration_seconds: float = Field(..., description="Execution duration")
    sandbox_info: dict[str, Any] = Field(..., description="Sandbox container information")


class SandboxResources(BaseModel):
    """Resource usage of a running sandbox."""

    cpu_percent: float = Field(..., description="CPU usage as a percentage")
    memory_mb: float = Field(..., description="Resident memory in megabytes")


class SandboxStatusResponse(BaseModel):
    """
    State of one execution sandbox.

    Not served yet: the hardened sandbox arrives in Stage 9. The TypeScript SDK has
    carried this shape since Phase 0 and the Python SDK had no equivalent, which is
    the asymmetry `scripts/ci/check_sdk_parity.py` exists to catch.
    """

    sandbox_id: str = Field(..., description="Sandbox identifier")
    status: Literal["running", "completed", "terminated"] = Field(..., description="Current state")
    created_at: datetime = Field(..., description="When the sandbox was created")
    resources: SandboxResources | None = Field(None, description="Usage, while running")


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
    filters: dict[str, Any] | None = Field(default=None, description="Additional filters")


class SearchResult(BaseModel):
    """A single search result."""

    result_id: str = Field(..., description="Result identifier")
    content: str = Field(..., description="Result content")
    score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    source: str = Field(..., description="Source identifier")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class SearchResponse(BaseModel):
    """Search results."""

    results: list[SearchResult] = Field(..., description="Search results")
    query: str = Field(..., description="Original query")
    method_used: Literal["vector", "keyword", "hybrid"] = Field(
        ..., description="Search method used"
    )
    total_results: int = Field(..., description="Total matching results")
    synthesis: str | None = Field(default=None, description="Synthesized summary of results")
    citations: list[str] = Field(default_factory=list, description="Source citations")


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
    existing_code: str | None = Field(
        default=None, description="Existing code (for debug/refactor)"
    )
    style_guide: str | None = Field(default=None, description="Code style guidelines")
    include_tests: bool = Field(default=False, description="Whether to generate tests")
    include_docstrings: bool = Field(default=True, description="Whether to include docstrings")


class CodeResponse(BaseModel):
    """Code generation result."""

    success: bool = Field(..., description="Whether operation succeeded")
    code: str = Field(..., description="Generated/modified code")
    explanation: str = Field(..., description="Explanation of code/changes")
    language: str = Field(..., description="Programming language")
    tests: str | None = Field(default=None, description="Generated tests")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in code quality")
    warnings: list[str] = Field(default_factory=list, description="Warnings or caveats")


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
    location: str | None = Field(default=None, description="Location in output")
    suggestion: str | None = Field(default=None, description="Suggested fix")


class ValidationRequest(BaseModel):
    """Request to validate task output."""

    output: str = Field(..., description="Output to validate")
    acceptance_criteria: list[str] | None = Field(
        default=None, description="Criteria to check against"
    )
    output_type: str | None = Field(default=None, description="Expected output type")
    context: dict[str, Any] | None = Field(default=None, description="Validation context")


class ValidationResult(BaseModel):
    """Validation result."""

    valid: bool = Field(..., description="Whether output is valid")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in validation")
    issues: list[ValidationIssue] = Field(
        default_factory=list, description="Validation issues found"
    )
    passed_criteria: list[str] = Field(default_factory=list, description="Criteria that passed")
    failed_criteria: list[str] = Field(default_factory=list, description="Criteria that failed")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall quality score")
    suggestions: list[str] = Field(default_factory=list, description="Improvement suggestions")


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
    location: str | None = Field(default=None, description="Location in text")
    detected_value: str | None = Field(
        default=None, description="Detected sensitive value (redacted)"
    )


class SafetyRequest(BaseModel):
    """Request for safety check."""

    content: str = Field(..., description="Content to check")
    check_types: list[Literal["pii", "injection", "harmful_content", "policy_violation"]] = Field(
        default=["pii", "injection", "harmful_content"],
        description="Types of checks to perform",
    )
    sanitize: bool = Field(default=True, description="Whether to sanitize detected issues")


class SafetyResult(BaseModel):
    """Safety check result."""

    safe: bool = Field(..., description="Whether content is safe")
    issues: list[SafetyIssue] = Field(default_factory=list, description="Detected safety issues")
    risk_score: float = Field(..., ge=0.0, le=1.0, description="Overall risk score")
    sanitized_content: str | None = Field(default=None, description="Sanitized version of content")
    should_proceed: bool = Field(..., description="Whether processing should proceed")


# ============================================================================
# Common Response Models
# ============================================================================


class HealthResponse(BaseModel):
    """Service health status."""

    status: Literal["healthy", "degraded", "unhealthy"] = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime_seconds: int = Field(..., description="Service uptime in seconds")
    components: dict[str, str] | None = Field(default=None, description="Component health status")


class ErrorResponse(BaseModel):
    """Standard error response."""

    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(default=None, description="Additional error details")
    retry_after: int | None = Field(
        default=None, description="Retry after seconds (for rate limits)"
    )
    request_id: str | None = Field(default=None, description="Request ID for debugging")


class ProvenanceMetadata(BaseModel):
    """Provenance tracking metadata."""

    arm_id: str = Field(..., description="Arm that produced output")
    timestamp: datetime = Field(..., description="Output generation timestamp")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    command_hash: str | None = Field(
        default=None, description="Hash of executed command (for reproducibility)"
    )
    model_name: str | None = Field(default=None, description="LLM model name (if applicable)")
    model_version: str | None = Field(default=None, description="LLM model version")
