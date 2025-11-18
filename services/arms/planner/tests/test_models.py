"""
Tests for Pydantic data models.
"""

import pytest
from pydantic import ValidationError

from src.models import (
    CapabilitiesResponse,
    HealthResponse,
    PlanRequest,
    PlanResponse,
    ReadinessResponse,
    SubTask,
)

# ==============================================================================
# SubTask Tests
# ==============================================================================


def test_subtask_valid() -> None:
    """Test creating a valid SubTask."""
    subtask = SubTask(
        step=1,
        action="Search for information about Python",
        required_arm="retriever",
        acceptance_criteria=["Found at least 3 resources", "Resources are relevant"],
        depends_on=[],
        estimated_cost_tier=1,
        estimated_duration_seconds=20,
    )

    assert subtask.step == 1
    assert subtask.required_arm == "retriever"
    assert len(subtask.acceptance_criteria) == 2
    assert subtask.depends_on == []


def test_subtask_invalid_arm() -> None:
    """Test SubTask with invalid arm name."""
    with pytest.raises(ValidationError, match="required_arm must be one of"):
        SubTask(
            step=1,
            action="Do something",
            required_arm="invalid_arm",
            acceptance_criteria=["Done"],
        )


def test_subtask_invalid_cost_tier() -> None:
    """Test SubTask with invalid cost tier."""
    with pytest.raises(ValidationError):
        SubTask(
            step=1,
            action="Do something",
            required_arm="coder",
            acceptance_criteria=["Done"],
            estimated_cost_tier=6,  # Too high
        )

    with pytest.raises(ValidationError):
        SubTask(
            step=1,
            action="Do something",
            required_arm="coder",
            acceptance_criteria=["Done"],
            estimated_cost_tier=0,  # Too low
        )


def test_subtask_empty_acceptance_criteria() -> None:
    """Test SubTask with empty acceptance criteria."""
    with pytest.raises(ValidationError, match="acceptance_criteria must not be empty"):
        SubTask(
            step=1,
            action="Do something",
            required_arm="coder",
            acceptance_criteria=[],
        )


def test_subtask_whitespace_acceptance_criteria() -> None:
    """Test SubTask with whitespace-only acceptance criteria."""
    with pytest.raises(ValidationError, match="must contain non-empty strings"):
        SubTask(
            step=1,
            action="Do something",
            required_arm="coder",
            acceptance_criteria=["Valid", "  ", "Also valid"],
        )


# ==============================================================================
# PlanResponse Tests
# ==============================================================================


def test_plan_response_valid(sample_plan_response: dict) -> None:
    """Test creating a valid PlanResponse."""
    plan = PlanResponse(**sample_plan_response)

    assert len(plan.plan) == 4
    assert plan.confidence == 0.88
    assert plan.complexity_score == 0.5
    assert plan.total_estimated_duration == 120  # 20+45+30+25


def test_plan_response_empty_plan() -> None:
    """Test PlanResponse with empty plan list."""
    with pytest.raises(ValidationError, match="Plan must contain at least one subtask"):
        PlanResponse(
            plan=[],
            rationale="No plan",
            confidence=0.5,
            total_estimated_duration=0,
            complexity_score=0.0,
        )


def test_plan_response_non_sequential_steps() -> None:
    """Test PlanResponse with non-sequential step numbers."""
    with pytest.raises(ValidationError, match="Step numbers must be sequential"):
        PlanResponse(
            plan=[
                SubTask(
                    step=1,
                    action="Do A",
                    required_arm="coder",
                    acceptance_criteria=["Done"],
                ),
                SubTask(
                    step=3,  # Skipped step 2
                    action="Do B",
                    required_arm="coder",
                    acceptance_criteria=["Done"],
                ),
            ],
            rationale="Bad plan",
            confidence=0.5,
            total_estimated_duration=60,
            complexity_score=0.5,
        )


def test_plan_response_invalid_dependency_nonexistent() -> None:
    """Test PlanResponse with dependency on non-existent step."""
    with pytest.raises(ValidationError, match="depends on non-existent step"):
        PlanResponse(
            plan=[
                SubTask(
                    step=1,
                    action="Do A",
                    required_arm="coder",
                    acceptance_criteria=["Done"],
                    depends_on=[],
                ),
                SubTask(
                    step=2,
                    action="Do B",
                    required_arm="coder",
                    acceptance_criteria=["Done"],
                    depends_on=[3],  # Step 3 doesn't exist
                ),
            ],
            rationale="Bad dependencies",
            confidence=0.5,
            total_estimated_duration=60,
            complexity_score=0.5,
        )


def test_plan_response_invalid_dependency_forward() -> None:
    """Test PlanResponse with forward dependency."""
    with pytest.raises(ValidationError, match="cannot depend on later or same step"):
        PlanResponse(
            plan=[
                SubTask(
                    step=1,
                    action="Do A",
                    required_arm="coder",
                    acceptance_criteria=["Done"],
                    depends_on=[2],  # Forward dependency
                ),
                SubTask(
                    step=2,
                    action="Do B",
                    required_arm="coder",
                    acceptance_criteria=["Done"],
                    depends_on=[],
                ),
            ],
            rationale="Forward dependencies",
            confidence=0.5,
            total_estimated_duration=60,
            complexity_score=0.5,
        )


def test_plan_response_self_dependency() -> None:
    """Test PlanResponse with self-dependency."""
    with pytest.raises(ValidationError, match="cannot depend on later or same step"):
        PlanResponse(
            plan=[
                SubTask(
                    step=1,
                    action="Do A",
                    required_arm="coder",
                    acceptance_criteria=["Done"],
                    depends_on=[1],  # Self-dependency
                ),
            ],
            rationale="Self dependency",
            confidence=0.5,
            total_estimated_duration=30,
            complexity_score=0.5,
        )


def test_plan_response_confidence_bounds() -> None:
    """Test PlanResponse confidence validation."""
    # Valid bounds
    plan_data = {
        "plan": [
            SubTask(
                step=1,
                action="Do something",
                required_arm="coder",
                acceptance_criteria=["Done"],
            )
        ],
        "rationale": "Test",
        "total_estimated_duration": 30,
        "complexity_score": 0.5,
    }

    PlanResponse(**{**plan_data, "confidence": 0.0})
    PlanResponse(**{**plan_data, "confidence": 1.0})

    # Invalid bounds
    with pytest.raises(ValidationError):
        PlanResponse(**{**plan_data, "confidence": -0.1})
    with pytest.raises(ValidationError):
        PlanResponse(**{**plan_data, "confidence": 1.1})


# ==============================================================================
# PlanRequest Tests
# ==============================================================================


def test_plan_request_valid() -> None:
    """Test creating a valid PlanRequest."""
    request = PlanRequest(
        goal="Write a Python function to sort a list",
        constraints=["Use Python 3.11+", "Include type hints"],
        context={"experience_level": "intermediate"},
    )

    assert request.goal == "Write a Python function to sort a list"
    assert len(request.constraints) == 2
    assert request.context["experience_level"] == "intermediate"
    assert request.request_id  # Auto-generated UUID


def test_plan_request_minimal() -> None:
    """Test PlanRequest with minimal fields."""
    request = PlanRequest(goal="Simple task")

    assert request.goal == "Simple task"
    assert request.constraints == []
    assert request.context == {}
    assert request.request_id


def test_plan_request_empty_goal() -> None:
    """Test PlanRequest with empty goal."""
    with pytest.raises(ValidationError, match="Goal must be a non-empty string"):
        PlanRequest(goal="")


def test_plan_request_whitespace_goal() -> None:
    """Test PlanRequest with whitespace-only goal."""
    with pytest.raises(ValidationError, match="Goal must be a non-empty string"):
        PlanRequest(goal="   ")


def test_plan_request_goal_trimming() -> None:
    """Test that goal is trimmed."""
    request = PlanRequest(goal="  Task with spaces  ")
    assert request.goal == "Task with spaces"


# ==============================================================================
# Other Model Tests
# ==============================================================================


def test_health_response() -> None:
    """Test HealthResponse model."""
    response = HealthResponse(
        status="healthy",
        version="0.1.0",
        model="gpt-3.5-turbo",
        timestamp="2024-01-01T00:00:00Z",
    )

    assert response.status == "healthy"
    assert response.model == "gpt-3.5-turbo"


def test_readiness_response() -> None:
    """Test ReadinessResponse model."""
    response = ReadinessResponse(
        ready=True,
        checks={"planner": True, "api_key": True},
    )

    assert response.ready is True
    assert response.checks["planner"] is True


def test_capabilities_response() -> None:
    """Test CapabilitiesResponse model."""
    response = CapabilitiesResponse(
        arm_id="planner",
        capabilities=["planning", "decomposition"],
        cost_tier=2,
        average_latency_ms=1500,
        success_rate=0.92,
    )

    assert response.arm_id == "planner"
    assert len(response.capabilities) == 2
    assert response.cost_tier == 2
