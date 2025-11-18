"""
Tests for core planning logic.
"""

import json

import pytest
from openai import APIError, RateLimitError
from pytest_mock import MockerFixture

from src.config import Settings
from src.models import PlanResponse
from src.planner import (
    InvalidDependencyError,
    LLMError,
    PlannerArm,
    PlanningError,
)

# ==============================================================================
# PlannerArm Initialization Tests
# ==============================================================================


def test_planner_initialization(test_settings: Settings) -> None:
    """Test PlannerArm initializes correctly."""
    planner = PlannerArm(test_settings)

    assert planner.model == "gpt-3.5-turbo"
    assert planner.temperature == 0.3
    assert planner.max_tokens == 2000


# ==============================================================================
# Plan Generation Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_generate_plan_success(
    planner: PlannerArm, sample_plan_response: dict, mocker: MockerFixture
) -> None:
    """Test successful plan generation."""
    # Mock LLM call
    mock_response = mocker.Mock()
    mock_response.choices = [mocker.Mock()]
    mock_response.choices[0].message.content = json.dumps(sample_plan_response)
    mock_response.model = "gpt-3.5-turbo"
    mock_response.usage.total_tokens = 500

    mocker.patch.object(
        planner.client.chat.completions,
        "create",
        return_value=mock_response,
    )

    # Generate plan
    plan = await planner.generate_plan(
        goal="Write a function to sort a list",
        constraints=["Use Python", "Include tests"],
        context={},
    )

    # Verify
    assert isinstance(plan, PlanResponse)
    assert len(plan.plan) == 4
    assert plan.confidence == 0.88
    assert plan.total_estimated_duration == 120


@pytest.mark.asyncio
async def test_generate_plan_complex(
    planner: PlannerArm, sample_complex_plan: dict, mocker: MockerFixture
) -> None:
    """Test complex plan with multiple dependencies."""
    mock_response = mocker.Mock()
    mock_response.choices = [mocker.Mock()]
    mock_response.choices[0].message.content = json.dumps(sample_complex_plan)
    mock_response.model = "gpt-3.5-turbo"
    mock_response.usage.total_tokens = 800

    mocker.patch.object(
        planner.client.chat.completions,
        "create",
        return_value=mock_response,
    )

    plan = await planner.generate_plan(
        goal="Fix authentication bug",
        constraints=["Maintain backward compatibility"],
        context={"language": "Python"},
    )

    assert len(plan.plan) == 7
    assert plan.complexity_score == 0.75

    # Check parallel dependencies
    step_6 = plan.plan[5]  # 0-indexed, so step 6
    assert 4 in step_6.depends_on
    assert 5 in step_6.depends_on


@pytest.mark.asyncio
async def test_generate_plan_too_few_steps(planner: PlannerArm, mocker: MockerFixture) -> None:
    """Test plan with fewer than minimum steps."""
    short_plan = {
        "plan": [
            {
                "step": 1,
                "action": "Do task",
                "required_arm": "coder",
                "acceptance_criteria": ["Done"],
                "depends_on": [],
                "estimated_cost_tier": 2,
                "estimated_duration_seconds": 30,
            }
        ],
        "rationale": "Too short",
        "confidence": 0.5,
        "complexity_score": 0.2,
    }

    mock_response = mocker.Mock()
    mock_response.choices = [mocker.Mock()]
    mock_response.choices[0].message.content = json.dumps(short_plan)
    mock_response.model = "gpt-3.5-turbo"
    mock_response.usage = None

    mocker.patch.object(
        planner.client.chat.completions,
        "create",
        return_value=mock_response,
    )

    with pytest.raises(PlanningError, match="minimum is 3"):
        await planner.generate_plan("Simple task", [], {})


@pytest.mark.asyncio
async def test_generate_plan_too_many_steps(planner: PlannerArm, mocker: MockerFixture) -> None:
    """Test plan with more than maximum steps."""
    long_plan = {
        "plan": [
            {
                "step": i,
                "action": f"Step {i}",
                "required_arm": "coder",
                "acceptance_criteria": ["Done"],
                "depends_on": [i - 1] if i > 1 else [],
                "estimated_cost_tier": 2,
                "estimated_duration_seconds": 30,
            }
            for i in range(1, 11)  # 10 steps
        ],
        "rationale": "Too long",
        "confidence": 0.5,
        "complexity_score": 0.8,
    }

    mock_response = mocker.Mock()
    mock_response.choices = [mocker.Mock()]
    mock_response.choices[0].message.content = json.dumps(long_plan)
    mock_response.model = "gpt-3.5-turbo"
    mock_response.usage = None

    mocker.patch.object(
        planner.client.chat.completions,
        "create",
        return_value=mock_response,
    )

    with pytest.raises(PlanningError, match="maximum is 7"):
        await planner.generate_plan("Complex task", [], {})


# ==============================================================================
# Error Handling Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_generate_plan_invalid_json(planner: PlannerArm, mocker: MockerFixture) -> None:
    """Test handling of invalid JSON from LLM."""
    mock_response = mocker.Mock()
    mock_response.choices = [mocker.Mock()]
    mock_response.choices[0].message.content = "This is not JSON {{"
    mock_response.model = "gpt-3.5-turbo"
    mock_response.usage = None

    mocker.patch.object(
        planner.client.chat.completions,
        "create",
        return_value=mock_response,
    )

    with pytest.raises(PlanningError, match="Failed to parse LLM response as JSON"):
        await planner.generate_plan("Test goal", [], {})


@pytest.mark.asyncio
async def test_generate_plan_missing_fields(planner: PlannerArm, mocker: MockerFixture) -> None:
    """Test handling of response missing required fields."""
    incomplete_response = {
        "plan": [
            {
                "step": 1,
                "action": "Do something",
                "required_arm": "coder",
                "acceptance_criteria": ["Done"],
                "depends_on": [],
                "estimated_cost_tier": 2,
                "estimated_duration_seconds": 30,
            }
        ]
        # Missing rationale, confidence
    }

    mock_response = mocker.Mock()
    mock_response.choices = [mocker.Mock()]
    mock_response.choices[0].message.content = json.dumps(incomplete_response)
    mock_response.model = "gpt-3.5-turbo"
    mock_response.usage = None

    mocker.patch.object(
        planner.client.chat.completions,
        "create",
        return_value=mock_response,
    )

    with pytest.raises(PlanningError):
        await planner.generate_plan("Test goal", [], {})


@pytest.mark.asyncio
async def test_generate_plan_llm_rate_limit(planner: PlannerArm, mocker: MockerFixture) -> None:
    """Test LLM rate limit error with retry."""
    call_count = 0

    async def mock_create(*args: any, **kwargs: any) -> any:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise RateLimitError("Rate limit exceeded", response=mocker.Mock(), body=None)
        # Success on 3rd attempt
        mock_resp = mocker.Mock()
        mock_resp.choices = [mocker.Mock()]
        mock_resp.choices[0].message.content = json.dumps(
            {
                "plan": [
                    {
                        "step": 1,
                        "action": "Do A",
                        "required_arm": "coder",
                        "acceptance_criteria": ["Done"],
                        "depends_on": [],
                        "estimated_cost_tier": 2,
                        "estimated_duration_seconds": 30,
                    },
                    {
                        "step": 2,
                        "action": "Do B",
                        "required_arm": "judge",
                        "acceptance_criteria": ["Validated"],
                        "depends_on": [1],
                        "estimated_cost_tier": 2,
                        "estimated_duration_seconds": 20,
                    },
                    {
                        "step": 3,
                        "action": "Do C",
                        "required_arm": "executor",
                        "acceptance_criteria": ["Executed"],
                        "depends_on": [2],
                        "estimated_cost_tier": 1,
                        "estimated_duration_seconds": 15,
                    },
                ],
                "rationale": "Retry succeeded",
                "confidence": 0.8,
                "complexity_score": 0.4,
            }
        )
        mock_resp.model = "gpt-3.5-turbo"
        mock_resp.usage.total_tokens = 300
        return mock_resp

    mocker.patch.object(
        planner.client.chat.completions,
        "create",
        side_effect=mock_create,
    )

    plan = await planner.generate_plan("Test goal", [], {})
    assert len(plan.plan) == 3
    assert call_count == 3  # Retried twice


@pytest.mark.asyncio
async def test_generate_plan_llm_api_error(planner: PlannerArm, mocker: MockerFixture) -> None:
    """Test LLM API error after retries."""
    mocker.patch.object(
        planner.client.chat.completions,
        "create",
        side_effect=APIError("API Error", request=mocker.Mock(), body=None),
    )

    with pytest.raises(LLMError):
        await planner.generate_plan("Test goal", [], {})


# ==============================================================================
# Dependency Validation Tests
# ==============================================================================


def test_validate_dependencies_valid(planner: PlannerArm) -> None:
    """Test valid dependencies pass validation."""
    steps = [
        {"step": 1, "depends_on": []},
        {"step": 2, "depends_on": [1]},
        {"step": 3, "depends_on": [1, 2]},
    ]

    # Should not raise
    planner._validate_dependencies(steps)


def test_validate_dependencies_forward_reference(planner: PlannerArm) -> None:
    """Test forward dependency is caught."""
    steps = [
        {"step": 1, "depends_on": [2]},  # Forward ref
        {"step": 2, "depends_on": []},
    ]

    with pytest.raises(InvalidDependencyError, match="cannot depend on later or same step"):
        planner._validate_dependencies(steps)


def test_validate_dependencies_self_reference(planner: PlannerArm) -> None:
    """Test self-dependency is caught."""
    steps = [{"step": 1, "depends_on": [1]}]

    with pytest.raises(InvalidDependencyError, match="cannot depend on later or same step"):
        planner._validate_dependencies(steps)


def test_validate_dependencies_nonexistent(planner: PlannerArm) -> None:
    """Test dependency on non-existent step is caught."""
    steps = [
        {"step": 1, "depends_on": []},
        {"step": 2, "depends_on": [3]},  # Step 3 doesn't exist
    ]

    with pytest.raises(InvalidDependencyError, match="depends on non-existent step"):
        planner._validate_dependencies(steps)


# ==============================================================================
# Complexity Calculation Tests
# ==============================================================================


def test_calculate_complexity_simple(planner: PlannerArm) -> None:
    """Test complexity calculation for simple plan."""
    steps = [
        {"step": 1, "depends_on": [], "estimated_cost_tier": 1},
        {"step": 2, "depends_on": [1], "estimated_cost_tier": 1},
        {"step": 3, "depends_on": [2], "estimated_cost_tier": 1},
    ]

    complexity = planner._calculate_complexity(steps)
    assert 0.0 <= complexity <= 0.5  # Simple plan


def test_calculate_complexity_complex(planner: PlannerArm) -> None:
    """Test complexity calculation for complex plan."""
    steps = [
        {"step": i, "depends_on": list(range(max(1, i - 2), i)), "estimated_cost_tier": 4}
        for i in range(1, 11)
    ]

    complexity = planner._calculate_complexity(steps)
    assert 0.7 <= complexity <= 1.0  # Complex plan


def test_calculate_complexity_empty(planner: PlannerArm) -> None:
    """Test complexity calculation for empty plan."""
    complexity = planner._calculate_complexity([])
    assert complexity == 0.0


# ==============================================================================
# Parse LLM Response Tests
# ==============================================================================


def test_parse_llm_response_valid(planner: PlannerArm, sample_plan_response: dict) -> None:
    """Test parsing valid LLM response."""
    content = json.dumps(sample_plan_response)
    data = planner._parse_llm_response(content)

    assert "plan" in data
    assert "rationale" in data
    assert "confidence" in data
    assert "complexity_score" in data


def test_parse_llm_response_adds_default_complexity(planner: PlannerArm) -> None:
    """Test that missing complexity_score is calculated."""
    response = {
        "plan": [
            {
                "step": 1,
                "action": "Do something",
                "required_arm": "coder",
                "acceptance_criteria": ["Done"],
                "depends_on": [],
                "estimated_cost_tier": 2,
                "estimated_duration_seconds": 30,
            }
        ],
        "rationale": "Test",
        "confidence": 0.8,
        # Missing complexity_score
    }

    content = json.dumps(response)
    data = planner._parse_llm_response(content)

    assert "complexity_score" in data
    assert isinstance(data["complexity_score"], float)
