"""Tests for the ring's provenance envelope."""

from __future__ import annotations

import hashlib

import pytest
from octollm_common.models.provenance import (
    Artifact,
    InputSource,
    ModelInfo,
    Provenance,
    Sensitivity,
    Transformation,
    ValidationStatus,
    may_flow_to,
)


def provenance(**overrides: object) -> Provenance:
    base: dict[str, object] = {"created_by": "coder", "task_id": "task-1"}
    return Provenance(**{**base, **overrides})  # type: ignore[arg-type]


def test_content_hash_is_computed_not_accepted() -> None:
    """
    A producer-supplied hash proves nothing, so any supplied value is overwritten.

    This is the whole reason the hash exists: an artifact whose integrity field is
    filled in by the thing whose integrity is in question is decoration.
    """
    artifact = Artifact(
        artifact_id="a1",
        artifact_type="code",
        content="def hello(): ...",
        provenance=provenance(),
        content_sha256="0" * 64,
    )
    assert artifact.content_sha256 == hashlib.sha256(b"def hello(): ...").hexdigest()


def test_identical_content_hashes_identically() -> None:
    """At-least-once delivery makes this the handler's duplicate check."""
    first = Artifact(artifact_id="a1", artifact_type="code", content="x", provenance=provenance())
    second = Artifact(artifact_id="a2", artifact_type="code", content="x", provenance=provenance())
    assert first.content_sha256 == second.content_sha256


def test_json_round_trip_preserves_the_envelope() -> None:
    """
    The ring carries these as JSON, so this is the actual wire format.

    Serialising with one shape and parsing with another is precisely the defect that
    kept 39 reflex-client tests green over a client that could not read a real response.
    """
    original = Artifact(
        artifact_id="a1",
        artifact_type="verdict",
        content="looks fine",
        provenance=provenance(
            created_by="judge",
            parent_task_id="task-0",
            input_sources=[InputSource(source_id="d1", source_type="memory", relevance_score=0.9)],
            transformations=[Transformation(step=1, operation="score", tool="judge_v1")],
            validation_status=ValidationStatus(
                validated=True, validator="judge", confidence=0.95, checks_passed=["syntax"]
            ),
            model_info=ModelInfo(model_name="fake", provider="fake", tokens_used=12),
            trace_id="trace-abc",
            engagement_id="eng-1",
            sensitivity=Sensitivity.CONFIDENTIAL,
            promoted_from="a0",
        ),
    )
    restored = Artifact.from_json(original.to_json())
    assert restored == original
    assert restored.provenance.sensitivity is Sensitivity.CONFIDENTIAL
    assert restored.provenance.trace_id == "trace-abc"


def test_an_unlabelled_artifact_defaults_to_internal_not_public() -> None:
    """
    The default must be the safer of the two.

    An artifact nobody labelled is an artifact nobody thought about, and defaulting it
    to the most freely flowing level is how confidential content reaches an egress
    gate that waves it through.
    """
    assert provenance().sensitivity is Sensitivity.INTERNAL


@pytest.mark.parametrize(
    ("artifact", "clearance", "allowed"),
    [
        (Sensitivity.PUBLIC, Sensitivity.PUBLIC, True),
        (Sensitivity.PUBLIC, Sensitivity.RESTRICTED, True),
        (Sensitivity.INTERNAL, Sensitivity.PUBLIC, False),
        (Sensitivity.RESTRICTED, Sensitivity.CONFIDENTIAL, False),
        (Sensitivity.RESTRICTED, Sensitivity.RESTRICTED, True),
        (Sensitivity.CONFIDENTIAL, Sensitivity.RESTRICTED, True),
    ],
)
def test_the_diode_only_flows_upward(
    artifact: Sensitivity, clearance: Sensitivity, allowed: bool
) -> None:
    assert may_flow_to(artifact, clearance) is allowed


def test_every_sensitivity_level_is_ordered() -> None:
    """
    Adding an enum member without placing it in the order must fail here.

    `may_flow_to` indexes into an explicit tuple; a member missing from it raises
    ValueError at the first comparison, which in production would be an egress check
    that crashes rather than one that decides.
    """
    for level in Sensitivity:
        assert may_flow_to(level, Sensitivity.RESTRICTED) is True


def test_promotion_records_lineage_and_inherits_sensitivity() -> None:
    """
    Promotion changes where something is stored, never how far it may travel.

    A promoted copy that reset to the default would launder a restricted artifact into
    an internal one on its way into global memory.
    """
    episodic = Artifact(
        artifact_id="ep-1",
        artifact_type="finding",
        content="secret",
        provenance=provenance(created_by="red-team", sensitivity=Sensitivity.RESTRICTED),
    )
    promoted = episodic.promote(artifact_id="sem-1", created_by="memory")

    assert promoted.provenance.promoted_from == "ep-1"
    assert promoted.provenance.created_by == "memory"
    assert promoted.provenance.sensitivity is Sensitivity.RESTRICTED
    assert promoted.content_sha256 == episodic.content_sha256


def test_provenance_requires_a_producer_and_a_task() -> None:
    """An artifact that cannot say who made it or why is not auditable."""
    with pytest.raises(ValueError):
        Provenance(created_by="", task_id="task-1")
    with pytest.raises(ValueError):
        Provenance(created_by="coder", task_id="")


def test_unknown_fields_are_rejected() -> None:
    """
    `extra="forbid"` throughout: a typo'd field name must not vanish silently.

    A `sensitivty` that is accepted and ignored is an artifact that believes it is
    labelled and is not.
    """
    with pytest.raises(ValueError):
        Provenance(created_by="coder", task_id="t", sensitivty="restricted")  # type: ignore[call-arg]
