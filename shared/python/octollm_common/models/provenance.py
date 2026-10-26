"""
The provenance envelope every ring artifact carries.

`docs/architecture/data-flow.md` specifies this shape and imposes three constraints on
direct arm-to-arm communication: register intent with the orchestrator, include
provenance in all messages, respect capability boundaries. This module is the second
one, and it is transcribed from that document rather than redesigned -- the fields
`created_by`, `created_at`, `task_id`, `parent_task_id`, `input_sources`,
`transformations`, `validation_status` and `model_info` are the doc's, verbatim.

Four fields are added, each for a reason the original could not have had:

- **`trace_id`** stitches an artifact to its OpenTelemetry span. Without it, a ring
  message is the one hop in the system with no place in a trace, which is exactly the
  hop hardest to reason about because no single service saw both ends of it.
- **`engagement_id`** binds an artifact to a signed Red Team engagement (Stage 11).
  An audit that cannot answer "which authorization produced this packet" is not an
  audit, and retrofitting the field later would leave every earlier artifact unable
  to answer.
- **`sensitivity`** is what makes the "data diode" in the design enforceable rather
  than aspirational. The docs describe restricted data that must not flow outward;
  until something labels an artifact, no component can act on that.
- **`promoted_from`** records memory lineage: when the Memory arm (Stage 6) promotes
  an episodic artifact into global semantic memory, the promoted copy points back at
  what it came from. Promotion without lineage is how a wrong fact becomes permanent
  and unattributable.

## Content hashing

`content_sha256` is computed, not supplied. An artifact whose hash is a field the
producer fills in is an artifact whose hash proves nothing.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = [
    "Artifact",
    "InputSource",
    "ModelInfo",
    "Provenance",
    "Sensitivity",
    "Transformation",
    "ValidationStatus",
    "may_flow_to",
]


class Sensitivity(StrEnum):
    """
    How far an artifact is permitted to travel.

    Ordered, and the order is load-bearing: `may_flow_to` compares them. Adding a level
    means inserting it in `_ORDER` too, which is deliberately a separate list so that
    adding an enum member without thinking about ordering fails a test rather than
    silently sorting alphabetically.
    """

    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


#: Increasing restriction. See `Sensitivity`.
_ORDER: tuple[Sensitivity, ...] = (
    Sensitivity.PUBLIC,
    Sensitivity.INTERNAL,
    Sensitivity.CONFIDENTIAL,
    Sensitivity.RESTRICTED,
)


def may_flow_to(artifact: Sensitivity, destination_clearance: Sensitivity) -> bool:
    """
    Whether an artifact may cross into a destination of the given clearance.

    The diode direction: data flows *up* to a destination cleared for at least its own
    sensitivity, never down. A `restricted` artifact may not reach a `public` sink; a
    `public` artifact may reach any.

    This is a pure predicate on purpose. The enforcement point is the Safety Guardian's
    egress gate (Stage 8), and a predicate that several components can apply
    identically is better than three components each deciding what "restricted" means.
    """
    return _ORDER.index(artifact) <= _ORDER.index(destination_clearance)


class InputSource(BaseModel):
    """Something that fed into producing this artifact."""

    model_config = ConfigDict(extra="forbid")

    source_id: str
    source_type: str = Field(..., description="e.g. 'documentation', 'memory', 'tool_output'")
    relevance_score: float | None = Field(None, ge=0.0, le=1.0)


class Transformation(BaseModel):
    """One step in how the artifact came to be."""

    model_config = ConfigDict(extra="forbid")

    step: int = Field(..., ge=1)
    operation: str = Field(..., min_length=1, description="e.g. 'template_fill'")
    tool: str = Field("", description="What performed it")


class ValidationStatus(BaseModel):
    """What the Judge, or any validator, concluded."""

    model_config = ConfigDict(extra="forbid")

    validated: bool = False
    validator: str = Field("", description="arm_id of the validator, empty if none")
    confidence: float | None = Field(None, ge=0.0, le=1.0)
    checks_passed: list[str] = Field(default_factory=list)


class ModelInfo(BaseModel):
    """
    Which model produced this, and under what settings.

    `prompt_hash` rather than the prompt: reproducibility without putting task content
    -- which may be exactly the confidential part -- into an audit record that is
    retained longer and read more widely than the task itself.
    """

    model_config = ConfigDict(extra="forbid")

    model_name: str = Field("", description="Empty when no model was involved")
    provider: str = Field("")
    prompt_hash: str = Field("", description="sha256:... of the rendered prompt")
    temperature: float | None = Field(None, ge=0.0, le=2.0)
    tokens_used: int = Field(0, ge=0)


class Provenance(BaseModel):
    """Complete lineage for one artifact."""

    model_config = ConfigDict(extra="forbid")

    created_by: str = Field(..., min_length=1, description="arm_id of the producer")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    task_id: str = Field(..., min_length=1)
    parent_task_id: str | None = None

    input_sources: list[InputSource] = Field(default_factory=list)
    transformations: list[Transformation] = Field(default_factory=list)
    validation_status: ValidationStatus = Field(default_factory=ValidationStatus)
    model_info: ModelInfo = Field(default_factory=ModelInfo)

    # --- added beyond data-flow.md; see the module docstring for why each ----------
    trace_id: str | None = Field(None, description="OpenTelemetry trace id, for stitching")
    engagement_id: str | None = Field(
        None, description="Signed Red Team engagement this artifact was produced under"
    )
    sensitivity: Sensitivity = Field(
        Sensitivity.INTERNAL,
        description="Default INTERNAL, never PUBLIC: an unlabelled artifact must not "
        "be the most freely flowing one.",
    )
    promoted_from: str | None = Field(
        None, description="artifact_id this was promoted from, for memory lineage"
    )


class Artifact(BaseModel):
    """
    One unit of work product on the ring.

    `artifact_type` is the routing key: it selects the stream, and an arm may only
    publish types it declares in `ArmSpec.publishes`.
    """

    model_config = ConfigDict(extra="forbid")

    artifact_id: str = Field(..., min_length=1)
    artifact_type: str = Field(..., min_length=1, description="e.g. 'code', 'verdict'")
    content: str = Field("")
    provenance: Provenance
    content_sha256: str = Field(
        "", description="Computed from `content`; any supplied value is overwritten"
    )

    @model_validator(mode="after")
    def _hash_content(self) -> Artifact:
        # Recomputed unconditionally rather than filled in when absent. A producer that
        # supplies a hash is either duplicating this line or lying, and there is no way
        # from here to tell which.
        digest = hashlib.sha256(self.content.encode("utf-8")).hexdigest()
        if self.content_sha256 != digest:
            object.__setattr__(self, "content_sha256", digest)
        return self

    def to_json(self) -> str:
        return self.model_dump_json()

    @classmethod
    def from_json(cls, raw: str | bytes) -> Artifact:
        return cls.model_validate_json(raw)

    def promote(self, *, artifact_id: str, created_by: str, **overrides: Any) -> Artifact:
        """
        Derive a promoted copy that points back at this one.

        Used by the Memory arm when an episodic artifact earns a place in global
        semantic memory. Sensitivity is inherited rather than reset: promotion changes
        where something is stored, never how far it may travel.
        """
        provenance = self.provenance.model_copy(
            update={
                "created_by": created_by,
                "created_at": datetime.now(UTC),
                "promoted_from": self.artifact_id,
                **overrides,
            }
        )
        return Artifact(
            artifact_id=artifact_id,
            artifact_type=self.artifact_type,
            content=self.content,
            provenance=provenance,
        )
