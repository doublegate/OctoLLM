"""
Pytest configuration and fixtures for Planner Arm tests.
"""

import os

import pytest
from fastapi.testclient import TestClient

from src.config import Settings, reset_settings
from src.main import app
from src.planner import PlannerArm


@pytest.fixture(autouse=True)
def reset_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reset settings singleton and set test API key before each test."""
    monkeypatch.setenv("PLANNER_OPENAI_API_KEY", "sk-test-key-12345")
    reset_settings()
    # Clean up env var after test to avoid pollution
    yield
    if "PLANNER_OPENAI_API_KEY" in os.environ:
        del os.environ["PLANNER_OPENAI_API_KEY"]
    reset_settings()


@pytest.fixture
def test_settings() -> Settings:
    """Create test settings with mock API key."""
    return Settings(
        openai_api_key="sk-test-key-12345",  # nosec B106
        llm_model="gpt-3.5-turbo",
        environment="development",
        debug=True,
        planning_temperature=0.3,
        max_tokens=2000,
        max_plan_steps=7,
        min_plan_steps=3,
    )


@pytest.fixture
def planner(test_settings: Settings) -> PlannerArm:
    """Create PlannerArm instance with test settings."""
    return PlannerArm(test_settings)


@pytest.fixture
def test_client() -> TestClient:
    """Create FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def sample_plan_response() -> dict:
    """Sample plan response from LLM."""
    return {
        "plan": [
            {
                "step": 1,
                "action": "Search for Python sorting algorithms and best practices",
                "required_arm": "retriever",
                "acceptance_criteria": [
                    "Found at least 3 sorting algorithm references",
                    "Identified performance characteristics",
                    "Located code examples",
                ],
                "depends_on": [],
                "estimated_cost_tier": 1,
                "estimated_duration_seconds": 20,
            },
            {
                "step": 2,
                "action": "Generate Python function to sort a list using appropriate algorithm",
                "required_arm": "coder",
                "acceptance_criteria": [
                    "Function accepts list parameter",
                    "Returns sorted list",
                    "Includes type hints and docstring",
                ],
                "depends_on": [1],
                "estimated_cost_tier": 3,
                "estimated_duration_seconds": 45,
            },
            {
                "step": 3,
                "action": "Generate test cases for the sorting function",
                "required_arm": "coder",
                "acceptance_criteria": [
                    "Tests cover normal cases",
                    "Tests cover edge cases (empty list, single item)",
                    "All tests pass",
                ],
                "depends_on": [2],
                "estimated_cost_tier": 2,
                "estimated_duration_seconds": 30,
            },
            {
                "step": 4,
                "action": "Validate function correctness and performance",
                "required_arm": "judge",
                "acceptance_criteria": [
                    "All test cases pass",
                    "Performance is acceptable",
                    "Code follows Python best practices",
                ],
                "depends_on": [3],
                "estimated_cost_tier": 2,
                "estimated_duration_seconds": 25,
            },
        ],
        "rationale": "This plan follows a systematic approach: research algorithms, implement solution, test thoroughly, and validate quality.",
        "confidence": 0.88,
        "complexity_score": 0.5,
        "total_estimated_duration": 120,  # 20+45+30+25
    }


@pytest.fixture
def sample_complex_plan() -> dict:
    """Sample complex plan with multiple dependencies."""
    return {
        "plan": [
            {
                "step": 1,
                "action": "Search for authentication vulnerabilities and best practices",
                "required_arm": "retriever",
                "acceptance_criteria": ["Found security guidelines", "Identified vulnerabilities"],
                "depends_on": [],
                "estimated_cost_tier": 1,
                "estimated_duration_seconds": 20,
            },
            {
                "step": 2,
                "action": "Analyze current authentication code for bugs",
                "required_arm": "coder",
                "acceptance_criteria": ["Root cause identified", "Fix approach proposed"],
                "depends_on": [1],
                "estimated_cost_tier": 4,
                "estimated_duration_seconds": 60,
            },
            {
                "step": 3,
                "action": "Generate code patch to fix authentication bug",
                "required_arm": "coder",
                "acceptance_criteria": ["Patch addresses issue", "No breaking changes"],
                "depends_on": [2],
                "estimated_cost_tier": 4,
                "estimated_duration_seconds": 45,
            },
            {
                "step": 4,
                "action": "Check patch for security vulnerabilities",
                "required_arm": "guardian",
                "acceptance_criteria": ["No PII leakage", "No new vulnerabilities"],
                "depends_on": [3],
                "estimated_cost_tier": 1,
                "estimated_duration_seconds": 15,
            },
            {
                "step": 5,
                "action": "Generate test cases for authentication flow",
                "required_arm": "coder",
                "acceptance_criteria": [
                    "Tests cover attack scenarios",
                    "Tests pass on patched code",
                ],
                "depends_on": [3],
                "estimated_cost_tier": 3,
                "estimated_duration_seconds": 40,
            },
            {
                "step": 6,
                "action": "Run full test suite to verify no regressions",
                "required_arm": "executor",
                "acceptance_criteria": ["All tests pass", "No timeouts"],
                "depends_on": [4, 5],
                "estimated_cost_tier": 2,
                "estimated_duration_seconds": 90,
            },
            {
                "step": 7,
                "action": "Validate fix meets all acceptance criteria",
                "required_arm": "judge",
                "acceptance_criteria": ["All requirements met", "Quality standards achieved"],
                "depends_on": [6],
                "estimated_cost_tier": 2,
                "estimated_duration_seconds": 30,
            },
        ],
        "rationale": "Comprehensive security-focused debugging workflow with parallel testing paths converging at validation.",
        "confidence": 0.82,
        "complexity_score": 0.75,
        "total_estimated_duration": 300,  # Sum of all durations
    }
