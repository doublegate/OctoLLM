"""
Tests for Pydantic models.
"""

import pytest
from datetime import datetime
from octollm_sdk.models import (
    TaskRequest,
    ResourceBudget,
    TaskResponse,
    CodeRequest,
    SearchRequest,
    ValidationRequest,
    SafetyRequest,
)


def test_task_request_minimal():
    """Test TaskRequest with minimal required fields."""
    task = TaskRequest(goal="Test goal for task request validation")
    assert task.goal == "Test goal for task request validation"
    assert task.constraints is None
    assert task.acceptance_criteria is None
    assert task.context is None
    assert task.budget is None


def test_task_request_full():
    """Test TaskRequest with all fields."""
    budget = ResourceBudget(max_tokens=5000, max_time_seconds=30, max_cost_dollars=0.50)
    task = TaskRequest(
        goal="Create Python email validator",
        constraints=["Include type hints", "Add docstring"],
        acceptance_criteria=["Validates RFC 5322"],
        context={"language": "python"},
        budget=budget,
    )
    assert task.goal == "Create Python email validator"
    assert len(task.constraints) == 2
    assert len(task.acceptance_criteria) == 1
    assert task.context["language"] == "python"
    assert task.budget.max_tokens == 5000


def test_resource_budget_defaults():
    """Test ResourceBudget default values."""
    budget = ResourceBudget()
    assert budget.max_tokens == 10000
    assert budget.max_time_seconds == 60
    assert budget.max_cost_dollars == 1.0


def test_resource_budget_validation():
    """Test ResourceBudget field validation."""
    # Valid ranges
    budget = ResourceBudget(max_tokens=100, max_time_seconds=5, max_cost_dollars=0.01)
    assert budget.max_tokens == 100

    # Invalid: below minimum
    with pytest.raises(ValueError):
        ResourceBudget(max_tokens=50)  # Below 100 minimum


def test_task_response_status_enum():
    """Test TaskResponse status enum validation."""
    response = TaskResponse(
        task_id="task_abc123xyz789",
        status="processing",
        created_at=datetime.now(),
    )
    assert response.status == "processing"

    # Invalid status should be rejected
    with pytest.raises(ValueError):
        TaskResponse(
            task_id="task_abc123xyz789",
            status="invalid_status",
            created_at=datetime.now(),
        )


def test_code_request_operations():
    """Test CodeRequest operation types."""
    operations = ["generate", "debug", "refactor", "explain"]
    for op in operations:
        request = CodeRequest(operation=op, prompt="Test prompt", language="python")
        assert request.operation == op


def test_search_request_methods():
    """Test SearchRequest search method types."""
    methods = ["vector", "keyword", "hybrid"]
    for method in methods:
        request = SearchRequest(query="test query", method=method)
        assert request.method == method


def test_validation_request_minimal():
    """Test ValidationRequest with minimal fields."""
    request = ValidationRequest(output="test output")
    assert request.output == "test output"
    assert request.acceptance_criteria is None


def test_safety_request_check_types():
    """Test SafetyRequest check types."""
    request = SafetyRequest(
        content="test content", check_types=["pii", "injection"], sanitize=True
    )
    assert len(request.check_types) == 2
    assert request.sanitize is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
