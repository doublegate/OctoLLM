"""
Tests for the shared contract models.

These models are the seam that makes drift structurally impossible: the arms import
them as their FastAPI models and the orchestrator imports the same classes as its
client models. What is asserted here is mostly that the seam is *strict* -- a lenient
model accepts the drift it exists to prevent.
"""

from __future__ import annotations

import pytest
from octollm_common.models.contracts import (
    ArmRequest,
    ArmResponse,
    CheckRequest,
    CodeRequest,
    ExecuteRequest,
    PlanRequest,
    PlanResponse,
    PlanStep,
    SearchRequest,
    UsageReport,
    ValidateRequest,
    ValidateResponse,
    Verdict,
)
from pydantic import ValidationError


def _response_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "arm_id": "planner",
        "request_id": "req-1",
        "usage": UsageReport(provider="fake", model="fake-1"),
        "confidence": 0.5,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Strictness -- the property the seam depends on
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "model, payload",
    [
        (PlanRequest, {"goal": "g", "goals": ["g"]}),
        (SearchRequest, {"query": "q", "topK": 5}),
        (CodeRequest, {"instruction": "i", "lang": "python"}),
        (ValidateRequest, {"content": "c", "schema": {}}),
        (CheckRequest, {"content": "c", "dir": "egress"}),
        (ExecuteRequest, {"argv": ["ls"], "cmd": "ls"}),
    ],
)
def test_an_unknown_field_is_rejected_rather_than_ignored(model: type, payload: dict):
    """
    `extra="forbid"` everywhere.

    A model that silently drops `topK` accepts a caller that will never work and
    reports success. This is exactly how the reflex client and the reflex layer came
    to disagree on four fields at once while 39 tests stayed green.
    """
    with pytest.raises(ValidationError, match="extra_forbidden|Extra inputs"):
        model(**payload)


def test_confidence_must_be_a_probability():
    with pytest.raises(ValidationError):
        PlanResponse(**_response_kwargs(confidence=1.5))


def test_an_empty_goal_is_rejected():
    """A planner asked to decompose nothing should fail at the boundary, not inside."""
    with pytest.raises(ValidationError):
        PlanRequest(goal="")


def test_execute_requires_at_least_one_argv_element():
    with pytest.raises(ValidationError):
        ExecuteRequest(argv=[])


# ---------------------------------------------------------------------------
# The common envelope
# ---------------------------------------------------------------------------


def test_every_response_carries_usage_even_with_no_model_call():
    """
    `usage` is required, not optional. Once arms call each other over the Neural Ring,
    an arm's own response is the only place its peer's spend can be reported -- the
    orchestrator never sees that call. An optional field here would make the ledger
    silently incomplete rather than loudly wrong.
    """
    response = PlanResponse(**_response_kwargs())

    assert response.usage.input_tokens == 0
    assert response.usage.peer_calls == 0
    assert response.produced_at.tzinfo is not None, "timestamps are timezone-aware"


def test_usage_report_rejects_negative_counts():
    with pytest.raises(ValidationError):
        UsageReport(provider="fake", model="fake-1", input_tokens=-1)


def test_the_base_request_fields_are_all_optional():
    """An arm called directly, outside a task, is a legitimate case -- notably in tests."""
    request = ArmRequest()

    assert request.task_id is None
    assert request.budget_tokens is None


def test_a_budget_of_zero_is_rejected():
    """A zero budget is almost always an uninitialised variable, not an intent."""
    with pytest.raises(ValidationError):
        ArmRequest(budget_tokens=0)


def test_arm_response_requires_the_full_envelope():
    with pytest.raises(ValidationError):
        ArmResponse(arm_id="planner", request_id="r")  # no usage, no confidence


# ---------------------------------------------------------------------------
# Wire format
# ---------------------------------------------------------------------------


def test_the_verdict_enum_serialises_to_snake_case_strings():
    """
    The contract says snake_case on the wire, enum values included. `StrEnum` means
    the serialised form and the Python value are the same string, so there is no
    mapping table to get wrong.
    """
    response = ValidateResponse(**_response_kwargs(verdict=Verdict.NEEDS_REVISION, score=0.4))

    assert response.model_dump(mode="json")["verdict"] == "needs_revision"


def test_a_plan_round_trips_through_json_unchanged():
    """
    The arms serialise these and the orchestrator deserialises them. A field that
    survives construction but not a round trip is drift with extra steps.
    """
    original = PlanResponse(
        **_response_kwargs(
            steps=[
                PlanStep(step_id="s1", arm_id="retriever", instruction="find the config"),
                PlanStep(step_id="s2", arm_id="coder", instruction="patch it", depends_on=["s1"]),
            ],
            rationale="two steps",
        )
    )

    assert PlanResponse.model_validate_json(original.model_dump_json()) == original


def test_dependencies_default_to_none_rather_than_an_implied_chain():
    """
    An empty `depends_on` means "ready now". Defaulting to the previous step would
    serialise a sequential plan the planner never asked for.
    """
    assert PlanStep(step_id="s1", arm_id="coder", instruction="i").depends_on == []


# ---------------------------------------------------------------------------
# Deliberate omissions, pinned so they are not re-added by accident
# ---------------------------------------------------------------------------


def test_the_judge_has_no_facts_check():
    """
    Deferred to v1.1 deliberately: verifying a factual claim means fetching a
    task-supplied URL from inside an arm, which is an SSRF primitive. It is routed
    through the retriever instead. This test is the reminder.
    """
    with pytest.raises(ValidationError):
        ValidateRequest(content="c", check="facts")


def test_the_safety_guardian_only_accepts_egress():
    """
    The two gates are split by traffic direction. Ingress belongs to the reflex layer,
    which is <10ms, cached, and already working; a second ingress path here would mean
    a second regex corpus drifting from the first.
    """
    with pytest.raises(ValidationError):
        CheckRequest(content="c", direction="ingress")


def test_execute_has_no_network_by_default():
    assert ExecuteRequest(argv=["ls"]).network is False
