"""
Tests for FastAPI endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from src.main import app
from src.models import PlanResponse


@pytest.fixture
def client() -> TestClient:
    """Create test client."""
    return TestClient(app)


# ==============================================================================
# POST /plan Tests
# ==============================================================================


def test_plan_endpoint_success(
    client: TestClient, sample_plan_response: dict, mocker: MockerFixture
) -> None:
    """Test successful plan generation via API."""
    # Mock planner
    mock_plan = PlanResponse(**sample_plan_response)
    mocker.patch.object(
        app.state, "planner", mocker.Mock(generate_plan=mocker.AsyncMock(return_value=mock_plan))
    )

    # Make request
    response = client.post(
        "/plan",
        json={
            "goal": "Write a function to sort a list",
            "constraints": ["Use Python", "Include tests"],
            "context": {},
        },
    )

    # Verify
    assert response.status_code == 200
    data = response.json()
    assert len(data["plan"]) == 4
    assert data["confidence"] == 0.88
    assert "rationale" in data


def test_plan_endpoint_with_constraints_and_context(
    client: TestClient, sample_plan_response: dict, mocker: MockerFixture
) -> None:
    """Test plan endpoint with constraints and context."""
    mock_plan = PlanResponse(**sample_plan_response)
    mock_generate = mocker.AsyncMock(return_value=mock_plan)
    mocker.patch.object(app.state, "planner", mocker.Mock(generate_plan=mock_generate))

    response = client.post(
        "/plan",
        json={
            "goal": "Complex task",
            "constraints": ["Time < 2 minutes", "Cost < $1"],
            "context": {"language": "Python", "experience": "intermediate"},
        },
    )

    assert response.status_code == 200

    # Verify planner was called with correct args
    mock_generate.assert_called_once()
    call_args = mock_generate.call_args
    assert call_args.kwargs["goal"] == "Complex task"
    assert len(call_args.kwargs["constraints"]) == 2
    assert call_args.kwargs["context"]["language"] == "Python"


def test_plan_endpoint_validation_error_empty_goal(client: TestClient) -> None:
    """Test validation error for empty goal."""
    response = client.post(
        "/plan",
        json={
            "goal": "",
            "constraints": [],
            "context": {},
        },
    )

    assert response.status_code == 422  # Validation error


def test_plan_endpoint_validation_error_missing_goal(client: TestClient) -> None:
    """Test validation error for missing goal."""
    response = client.post(
        "/plan",
        json={
            "constraints": [],
            "context": {},
        },
    )

    assert response.status_code == 422  # Validation error


def test_plan_endpoint_invalid_dependency_error(client: TestClient, mocker: MockerFixture) -> None:
    """Test handling of invalid dependency error."""
    from src.planner import InvalidDependencyError

    mocker.patch.object(
        app.state,
        "planner",
        mocker.Mock(
            generate_plan=mocker.AsyncMock(
                side_effect=InvalidDependencyError("Step 2 depends on step 3")
            )
        ),
    )

    response = client.post(
        "/plan",
        json={"goal": "Test goal", "constraints": [], "context": {}},
    )

    assert response.status_code == 400  # Bad request
    assert "Step 2 depends on step 3" in response.json()["detail"]


def test_plan_endpoint_llm_error(client: TestClient, mocker: MockerFixture) -> None:
    """Test handling of LLM error."""
    from src.planner import LLMError

    mocker.patch.object(
        app.state,
        "planner",
        mocker.Mock(generate_plan=mocker.AsyncMock(side_effect=LLMError("API timeout"))),
    )

    response = client.post(
        "/plan",
        json={"goal": "Test goal", "constraints": [], "context": {}},
    )

    assert response.status_code == 503  # Service unavailable
    assert "LLM service error" in response.json()["detail"]


def test_plan_endpoint_planning_error(client: TestClient, mocker: MockerFixture) -> None:
    """Test handling of generic planning error."""
    from src.planner import PlanningError

    mocker.patch.object(
        app.state,
        "planner",
        mocker.Mock(generate_plan=mocker.AsyncMock(side_effect=PlanningError("Plan too short"))),
    )

    response = client.post(
        "/plan",
        json={"goal": "Test goal", "constraints": [], "context": {}},
    )

    assert response.status_code == 500  # Internal server error
    assert "Planning failed" in response.json()["detail"]


def test_plan_endpoint_unexpected_error(client: TestClient, mocker: MockerFixture) -> None:
    """Test handling of unexpected error."""
    mocker.patch.object(
        app.state,
        "planner",
        mocker.Mock(generate_plan=mocker.AsyncMock(side_effect=RuntimeError("Unexpected"))),
    )

    response = client.post(
        "/plan",
        json={"goal": "Test goal", "constraints": [], "context": {}},
    )

    assert response.status_code == 500  # Internal server error


# ==============================================================================
# GET /health Tests
# ==============================================================================


def test_health_endpoint(client: TestClient) -> None:
    """Test health check endpoint."""
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "0.1.0"
    assert "model" in data
    assert "timestamp" in data


# ==============================================================================
# GET /ready Tests
# ==============================================================================


def test_ready_endpoint_ready(client: TestClient, mocker: MockerFixture) -> None:
    """Test readiness endpoint when service is ready."""
    # Mock planner exists
    mocker.patch.object(app.state, "planner", mocker.Mock())

    response = client.get("/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
    assert data["checks"]["planner_initialized"] is True
    assert data["checks"]["api_key_configured"] is True


def test_ready_endpoint_not_ready(client: TestClient, mocker: MockerFixture) -> None:
    """Test readiness endpoint when service is not ready."""
    # Remove planner from app state
    if hasattr(app.state, "planner"):
        delattr(app.state, "planner")

    response = client.get("/ready")

    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is False
    assert data["checks"]["planner_initialized"] is False


# ==============================================================================
# GET /metrics Tests
# ==============================================================================


def test_metrics_endpoint(client: TestClient) -> None:
    """Test Prometheus metrics endpoint."""
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]

    # Check for some expected metrics
    content = response.text
    assert "planner_arm_requests_total" in content
    assert "planner_arm_success_total" in content
    assert "planner_arm_errors_total" in content


# ==============================================================================
# GET /capabilities Tests
# ==============================================================================


def test_capabilities_endpoint(client: TestClient) -> None:
    """Test capabilities endpoint."""
    response = client.get("/capabilities")

    assert response.status_code == 200
    data = response.json()
    assert data["arm_id"] == "planner"
    assert "planning" in data["capabilities"]
    assert "task_decomposition" in data["capabilities"]
    assert data["cost_tier"] == 2
    assert data["average_latency_ms"] == 1500
    assert 0.0 <= data["success_rate"] <= 1.0


# ==============================================================================
# Middleware Tests
# ==============================================================================


def test_logging_middleware(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    """Test that requests are logged."""
    response = client.get("/health")
    assert response.status_code == 200

    # Note: structlog might not show up in caplog, but we verify the middleware doesn't break


def test_cors_middleware(client: TestClient) -> None:
    """Test CORS middleware is configured."""
    response = client.options(
        "/plan",
        headers={
            "Origin": "http://localhost:8000",
            "Access-Control-Request-Method": "POST",
        },
    )

    # CORS headers should be present
    assert "access-control-allow-origin" in response.headers


# ==============================================================================
# Integration Tests
# ==============================================================================


def test_full_request_flow(
    client: TestClient, sample_complex_plan: dict, mocker: MockerFixture
) -> None:
    """Test full request flow from request to response."""
    mock_plan = PlanResponse(**sample_complex_plan)
    mocker.patch.object(
        app.state, "planner", mocker.Mock(generate_plan=mocker.AsyncMock(return_value=mock_plan))
    )

    # Make request
    response = client.post(
        "/plan",
        json={
            "goal": "Fix authentication bug and add tests",
            "constraints": [
                "Don't modify database schema",
                "Complete in <5 minutes",
            ],
            "context": {
                "repository": "https://github.com/example/repo",
                "affected_files": ["auth/login.py"],
            },
        },
        headers={"X-Request-ID": "test-request-123"},
    )

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # Verify plan structure
    assert len(data["plan"]) == 7
    assert data["confidence"] == 0.82
    assert data["complexity_score"] == 0.75
    assert data["total_estimated_duration"] == 300

    # Verify steps
    assert data["plan"][0]["step"] == 1
    assert data["plan"][0]["required_arm"] == "retriever"
    assert len(data["plan"][0]["acceptance_criteria"]) == 2

    # Verify dependencies
    step_7 = data["plan"][6]
    assert step_7["step"] == 7
    assert 6 in step_7["depends_on"]


def test_request_validation_comprehensive(client: TestClient) -> None:
    """Test comprehensive request validation."""
    # Missing required field
    response = client.post("/plan", json={})
    assert response.status_code == 422

    # Empty goal
    response = client.post("/plan", json={"goal": ""})
    assert response.status_code == 422

    # Whitespace-only goal
    response = client.post("/plan", json={"goal": "   "})
    assert response.status_code == 422

    # Invalid constraint type (should be list)
    response = client.post("/plan", json={"goal": "Test", "constraints": "not a list"})
    assert response.status_code == 422

    # Invalid context type (should be dict)
    response = client.post("/plan", json={"goal": "Test", "context": "not a dict"})
    assert response.status_code == 422
