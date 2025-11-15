"""
Tests for Orchestrator models.

Validates Pydantic models, SQLAlchemy ORM models, and enum behavior.
"""

from datetime import UTC, datetime
from uuid import UUID, uuid4

import pytest
from pydantic import ValidationError

from app.models import (
    HealthResponse,
    Priority,
    ReadinessResponse,
    ResourceBudget,
    Task,
    TaskContract,
    TaskRequest,
    TaskResponse,
    TaskResult,
    TaskStatus,
    TaskSubmitResponse,
)

# ==============================================================================
# Enum Tests
# ==============================================================================


def test_task_status_enum_values():
    """Test TaskStatus enum has expected values."""
    assert TaskStatus.PENDING.value == "pending"
    assert TaskStatus.PROCESSING.value == "processing"
    assert TaskStatus.COMPLETED.value == "completed"
    assert TaskStatus.FAILED.value == "failed"
    assert TaskStatus.CANCELLED.value == "cancelled"


def test_priority_enum_values():
    """Test Priority enum has expected values."""
    assert Priority.LOW.value == "low"
    assert Priority.MEDIUM.value == "medium"
    assert Priority.HIGH.value == "high"
    assert Priority.CRITICAL.value == "critical"


def test_task_status_enum_iteration():
    """Test TaskStatus enum can be iterated."""
    statuses = list(TaskStatus)
    assert len(statuses) == 5
    assert TaskStatus.PENDING in statuses


def test_priority_enum_iteration():
    """Test Priority enum can be iterated."""
    priorities = list(Priority)
    assert len(priorities) == 4
    assert Priority.MEDIUM in priorities


# ==============================================================================
# ResourceBudget Tests
# ==============================================================================


def test_resource_budget_defaults():
    """Test ResourceBudget default values."""
    budget = ResourceBudget()
    assert budget.max_tokens == 10000
    assert budget.max_time_seconds == 300
    assert budget.max_cost_usd == 1.0


def test_resource_budget_valid_values():
    """Test ResourceBudget accepts valid values."""
    budget = ResourceBudget(
        max_tokens=5000,
        max_time_seconds=600,
        max_cost_usd=2.5,
    )
    assert budget.max_tokens == 5000
    assert budget.max_time_seconds == 600
    assert budget.max_cost_usd == 2.5


def test_resource_budget_rejects_negative_tokens():
    """Test ResourceBudget rejects negative max_tokens."""
    with pytest.raises(ValidationError) as exc_info:
        ResourceBudget(max_tokens=-100)

    assert "max_tokens" in str(exc_info.value)


def test_resource_budget_rejects_zero_tokens():
    """Test ResourceBudget rejects zero max_tokens."""
    with pytest.raises(ValidationError) as exc_info:
        ResourceBudget(max_tokens=0)

    assert "max_tokens" in str(exc_info.value)


def test_resource_budget_rejects_negative_time():
    """Test ResourceBudget rejects negative max_time_seconds."""
    with pytest.raises(ValidationError) as exc_info:
        ResourceBudget(max_time_seconds=-10)

    assert "max_time_seconds" in str(exc_info.value)


def test_resource_budget_rejects_negative_cost():
    """Test ResourceBudget rejects negative max_cost_usd."""
    with pytest.raises(ValidationError) as exc_info:
        ResourceBudget(max_cost_usd=-5.0)

    assert "max_cost_usd" in str(exc_info.value)


def test_resource_budget_rejects_excessive_tokens():
    """Test ResourceBudget rejects tokens above maximum."""
    with pytest.raises(ValidationError) as exc_info:
        ResourceBudget(max_tokens=200000)

    assert "max_tokens" in str(exc_info.value)


def test_resource_budget_rejects_excessive_time():
    """Test ResourceBudget rejects time above maximum."""
    with pytest.raises(ValidationError) as exc_info:
        ResourceBudget(max_time_seconds=7200)

    assert "max_time_seconds" in str(exc_info.value)


def test_resource_budget_rejects_excessive_cost():
    """Test ResourceBudget rejects cost above maximum."""
    with pytest.raises(ValidationError) as exc_info:
        ResourceBudget(max_cost_usd=150.0)

    assert "max_cost_usd" in str(exc_info.value)


# ==============================================================================
# TaskContract Tests
# ==============================================================================


def test_task_contract_minimal():
    """Test TaskContract with minimal required fields."""
    contract = TaskContract(goal="Test task goal")

    assert contract.goal == "Test task goal"
    assert isinstance(UUID(contract.task_id), UUID)
    assert contract.constraints == {}
    assert contract.context is None
    assert contract.acceptance_criteria == []
    assert isinstance(contract.budget, ResourceBudget)
    assert contract.priority == Priority.MEDIUM
    assert contract.parent_task_id is None
    assert contract.assigned_arm is None
    assert contract.metadata == {}


def test_task_contract_full():
    """Test TaskContract with all fields populated."""
    task_id = str(uuid4())
    parent_id = str(uuid4())

    contract = TaskContract(
        task_id=task_id,
        goal="Full task specification",
        constraints={"max_retries": 3, "timeout": 60},
        context="Additional context for task",
        acceptance_criteria=["Criterion 1", "Criterion 2"],
        budget=ResourceBudget(max_tokens=5000, max_time_seconds=120, max_cost_usd=0.5),
        priority=Priority.HIGH,
        parent_task_id=parent_id,
        assigned_arm="planner",
        metadata={"source": "test", "version": "1.0"},
    )

    assert contract.task_id == task_id
    assert contract.goal == "Full task specification"
    assert contract.constraints == {"max_retries": 3, "timeout": 60}
    assert contract.context == "Additional context for task"
    assert len(contract.acceptance_criteria) == 2
    assert contract.budget.max_tokens == 5000
    assert contract.priority == Priority.HIGH
    assert contract.parent_task_id == parent_id
    assert contract.assigned_arm == "planner"
    assert contract.metadata["source"] == "test"


def test_task_contract_rejects_empty_goal():
    """Test TaskContract rejects empty goal."""
    with pytest.raises(ValidationError) as exc_info:
        TaskContract(goal="")

    assert "goal" in str(exc_info.value).lower()


def test_task_contract_rejects_whitespace_only_goal():
    """Test TaskContract rejects whitespace-only goal."""
    with pytest.raises(ValidationError) as exc_info:
        TaskContract(goal="   \n\t  ")

    assert "goal" in str(exc_info.value).lower() or "whitespace" in str(exc_info.value).lower()


def test_task_contract_rejects_too_long_goal():
    """Test TaskContract rejects goal exceeding max length."""
    long_goal = "x" * 10001

    with pytest.raises(ValidationError) as exc_info:
        TaskContract(goal=long_goal)

    assert "goal" in str(exc_info.value).lower()


def test_task_contract_rejects_too_long_context():
    """Test TaskContract rejects context exceeding max length."""
    long_context = "x" * 50001

    with pytest.raises(ValidationError) as exc_info:
        TaskContract(goal="Valid goal", context=long_context)

    assert "context" in str(exc_info.value).lower()


def test_task_contract_generates_unique_ids():
    """Test TaskContract generates unique task IDs."""
    contract1 = TaskContract(goal="Task 1")
    contract2 = TaskContract(goal="Task 2")

    assert contract1.task_id != contract2.task_id
    assert isinstance(UUID(contract1.task_id), UUID)
    assert isinstance(UUID(contract2.task_id), UUID)


# ==============================================================================
# TaskRequest/TaskResponse Tests
# ==============================================================================


def test_task_request_minimal():
    """Test TaskRequest with minimal fields."""
    request = TaskRequest(goal="Test goal")

    assert request.goal == "Test goal"
    assert request.constraints is None
    assert request.context is None
    assert request.acceptance_criteria is None
    assert request.budget is None
    assert request.priority == Priority.MEDIUM
    assert request.metadata is None


def test_task_request_full():
    """Test TaskRequest with all fields."""
    request = TaskRequest(
        goal="Full request",
        constraints={"timeout": 30},
        context="Request context",
        acceptance_criteria=["Criterion 1"],
        budget=ResourceBudget(max_tokens=2000),
        priority=Priority.CRITICAL,
        metadata={"source": "api"},
    )

    assert request.goal == "Full request"
    assert request.constraints == {"timeout": 30}
    assert request.context == "Request context"
    assert len(request.acceptance_criteria) == 1
    assert request.budget.max_tokens == 2000
    assert request.priority == Priority.CRITICAL
    assert request.metadata["source"] == "api"


def test_task_response_structure():
    """Test TaskResponse structure and fields."""
    now = datetime.now(UTC)
    task_id = str(uuid4())

    response = TaskResponse(
        task_id=task_id,
        status=TaskStatus.COMPLETED,
        goal="Test goal",
        result={"output": "success"},
        error=None,
        created_at=now,
        updated_at=now,
        processing_time_ms=1500,
    )

    assert response.task_id == task_id
    assert response.status == TaskStatus.COMPLETED
    assert response.goal == "Test goal"
    assert response.result == {"output": "success"}
    assert response.error is None
    assert response.processing_time_ms == 1500


def test_task_submit_response_structure():
    """Test TaskSubmitResponse structure."""
    task_id = str(uuid4())

    response = TaskSubmitResponse(
        task_id=task_id,
        status=TaskStatus.PENDING,
        message="Task submitted",
    )

    assert response.task_id == task_id
    assert response.status == TaskStatus.PENDING
    assert response.message == "Task submitted"


# ==============================================================================
# Health/Readiness Response Tests
# ==============================================================================


def test_health_response_defaults():
    """Test HealthResponse with default values."""
    response = HealthResponse(status="healthy")

    assert response.status == "healthy"
    assert isinstance(response.timestamp, datetime)
    assert response.version == "0.1.0"


def test_health_response_custom_version():
    """Test HealthResponse with custom version."""
    response = HealthResponse(status="healthy", version="1.0.0")

    assert response.version == "1.0.0"


def test_readiness_response_ready():
    """Test ReadinessResponse when ready."""
    response = ReadinessResponse(
        ready=True,
        checks={"database": True, "reflex_layer": True},
    )

    assert response.ready is True
    assert response.checks["database"] is True
    assert response.checks["reflex_layer"] is True
    assert isinstance(response.timestamp, datetime)


def test_readiness_response_not_ready():
    """Test ReadinessResponse when not ready."""
    response = ReadinessResponse(
        ready=False,
        checks={"database": True, "reflex_layer": False},
    )

    assert response.ready is False
    assert response.checks["database"] is True
    assert response.checks["reflex_layer"] is False


# ==============================================================================
# SQLAlchemy ORM Model Tests
# ==============================================================================


def test_task_orm_to_contract_conversion():
    """Test Task ORM model converts to TaskContract."""
    task_id = uuid4()

    task = Task(
        id=task_id,
        goal="ORM test goal",
        status=TaskStatus.PENDING,
        constraints={"timeout": 60},
        context="ORM context",
        acceptance_criteria=["Criterion 1"],
        budget={"max_tokens": 5000, "max_time_seconds": 300, "max_cost_usd": 1.0},
        priority=Priority.HIGH,
        assigned_arm="planner",
        task_metadata={"source": "test"},
    )

    contract = task.to_contract()

    assert contract.task_id == str(task_id)
    assert contract.goal == "ORM test goal"
    # Note: TaskContract doesn't have a status field, only Task ORM does
    assert contract.constraints == {"timeout": 60}
    assert contract.context == "ORM context"
    assert len(contract.acceptance_criteria) == 1
    assert isinstance(contract.budget, ResourceBudget)
    assert contract.budget.max_tokens == 5000
    assert contract.priority == Priority.HIGH
    assert contract.assigned_arm == "planner"
    assert contract.metadata["source"] == "test"


def test_task_orm_to_response_conversion_without_result():
    """Test Task ORM converts to TaskResponse without result."""
    task_id = uuid4()
    now = datetime.now(UTC)

    task = Task(
        id=task_id,
        goal="Response test",
        status=TaskStatus.PROCESSING,
        budget={"max_tokens": 5000, "max_time_seconds": 300, "max_cost_usd": 1.0},
        created_at=now,
        updated_at=now,
    )

    response = task.to_response()

    assert response.task_id == str(task_id)
    assert response.status == TaskStatus.PROCESSING
    assert response.goal == "Response test"
    assert response.result is None
    assert response.error is None
    assert response.processing_time_ms is None


def test_task_orm_default_values():
    """Test Task ORM model default values.

    Note: This test verifies that explicit defaults are applied,
    but SQLAlchemy defaults (like UUID, timestamps) only apply after session.add().
    """
    task = Task(
        goal="Default test",
        budget={"max_tokens": 5000, "max_time_seconds": 300, "max_cost_usd": 1.0},
        # Explicitly set required defaults that normally come from Column defaults
        status=TaskStatus.PENDING,
        priority=Priority.MEDIUM,
        constraints={},
        acceptance_criteria=[],
        task_metadata={},
    )

    # Verify explicitly set values
    assert task.status == TaskStatus.PENDING
    assert task.priority == Priority.MEDIUM
    assert task.constraints == {}
    assert task.acceptance_criteria == []
    assert task.task_metadata == {}
    assert task.context is None
    assert task.parent_task_id is None
    assert task.assigned_arm is None


def test_task_result_orm_structure():
    """Test TaskResult ORM model structure."""
    task_id = uuid4()

    result = TaskResult(
        task_id=task_id,
        result={"output": "success", "data": [1, 2, 3]},
        error=None,
        processing_time_ms=2500,
    )

    assert result.task_id == task_id
    assert result.result == {"output": "success", "data": [1, 2, 3]}
    assert result.error is None
    assert result.processing_time_ms == 2500
    # Note: SQLAlchemy defaults like UUIDs are only generated after session.add()
    # assert isinstance(result.id, UUID)
    # assert isinstance(result.created_at, datetime)


def test_task_result_orm_with_error():
    """Test TaskResult ORM model with error."""
    task_id = uuid4()

    result = TaskResult(
        task_id=task_id,
        result=None,
        error="Task execution failed: timeout",
        processing_time_ms=30000,
    )

    assert result.task_id == task_id
    assert result.result is None
    assert result.error == "Task execution failed: timeout"
    assert result.processing_time_ms == 30000


def test_task_orm_with_parent_task():
    """Test Task ORM with parent task relationship."""
    parent_id = uuid4()

    task = Task(
        goal="Child task",
        budget={"max_tokens": 5000, "max_time_seconds": 300, "max_cost_usd": 1.0},
        parent_task_id=parent_id,
        priority=Priority.MEDIUM,  # Add explicit priority since it's required by Pydantic validation
    )

    assert task.parent_task_id == parent_id

    contract = task.to_contract()
    assert contract.parent_task_id == str(parent_id)
