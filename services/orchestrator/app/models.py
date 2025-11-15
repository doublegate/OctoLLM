"""
Data models for Orchestrator service.

This module contains Pydantic models for API requests/responses and SQLAlchemy ORM models
for database persistence.
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# ==============================================================================
# Enums
# ==============================================================================


class TaskStatus(str, Enum):
    """Status of a task in the orchestration pipeline."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Priority(str, Enum):
    """Task priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ==============================================================================
# Pydantic Models (API Layer)
# ==============================================================================


class ResourceBudget(BaseModel):
    """Resource constraints for task execution."""

    max_tokens: int = Field(default=10000, ge=1, le=100000, description="Maximum LLM tokens")
    max_time_seconds: int = Field(default=300, ge=1, le=3600, description="Maximum time")
    max_cost_usd: float = Field(default=1.0, ge=0.0, le=100.0, description="Maximum cost")


class TaskContract(BaseModel):
    """
    Formal specification for a task.

    This is the core data structure passed between Orchestrator and Arms,
    based on the TaskContract from ref-docs/OctoLLM-Architecture-Implementation.md.
    """

    task_id: str = Field(
        default_factory=lambda: str(uuid4()),
        description="Unique task identifier",
    )
    goal: str = Field(..., min_length=1, max_length=10000, description="Natural language goal")
    constraints: dict[str, Any] = Field(
        default_factory=dict,
        description="Hard constraints (time, cost, safety)",
    )
    context: str | None = Field(
        None,
        max_length=50000,
        description="Relevant background information",
    )
    acceptance_criteria: list[str] = Field(
        default_factory=list,
        description="Conditions for successful completion",
    )
    budget: ResourceBudget = Field(
        default_factory=ResourceBudget,
        description="Resource limits",
    )
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")
    parent_task_id: str | None = Field(
        None,
        description="Parent task if this is a subtask",
    )
    assigned_arm: str | None = Field(
        None,
        description="Target arm identifier",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    @field_validator("goal")
    @classmethod
    def validate_goal_not_empty(cls, v: str) -> str:
        """Ensure goal is not just whitespace."""
        if not v.strip():
            raise ValueError("Goal cannot be empty or whitespace only")
        return v


class TaskRequest(BaseModel):
    """Request to submit a new task."""

    goal: str = Field(..., min_length=1, max_length=10000, description="Task goal")
    constraints: dict[str, Any] | None = Field(None, description="Constraints")
    context: str | None = Field(None, max_length=50000, description="Context")
    acceptance_criteria: list[str] | None = Field(None, description="Success criteria")
    budget: ResourceBudget | None = Field(None, description="Resource budget")
    priority: Priority | None = Field(Priority.MEDIUM, description="Priority")
    metadata: dict[str, Any] | None = Field(None, description="Metadata")


class TaskResponse(BaseModel):
    """Response for task status/result query."""

    task_id: str = Field(..., description="Task identifier")
    status: TaskStatus = Field(..., description="Current status")
    goal: str = Field(..., description="Task goal")
    result: dict[str, Any] | None = Field(None, description="Task result if completed")
    error: str | None = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Task creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    processing_time_ms: int | None = Field(None, description="Total processing time")


class TaskSubmitResponse(BaseModel):
    """Response for task submission."""

    task_id: str = Field(..., description="Assigned task identifier")
    status: TaskStatus = Field(..., description="Initial status")
    message: str = Field(..., description="Confirmation message")


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = Field(..., description="Health status")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Check timestamp",
    )
    version: str = Field(default="0.1.0", description="Service version")


class ReadinessResponse(BaseModel):
    """Readiness check response."""

    ready: bool = Field(..., description="Service ready status")
    checks: dict[str, bool] = Field(..., description="Individual component checks")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="Check timestamp",
    )


# ==============================================================================
# SQLAlchemy Models (Database Layer)
# ==============================================================================


class Task(Base):  # type: ignore[valid-type,misc]
    """
    Task database model.

    Stores task metadata and status in PostgreSQL.
    """

    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    goal = Column(Text, nullable=False)
    status = Column(
        SQLEnum(TaskStatus, native_enum=False),
        nullable=False,
        default=TaskStatus.PENDING,
        index=True,
    )
    constraints = Column(JSON, nullable=False, default=dict)
    context = Column(Text, nullable=True)
    acceptance_criteria = Column(JSON, nullable=False, default=list)
    budget = Column(JSON, nullable=False)
    priority = Column(SQLEnum(Priority, native_enum=False), nullable=False, default=Priority.MEDIUM)
    parent_task_id = Column(UUID(as_uuid=True), nullable=True)
    assigned_arm = Column(String(100), nullable=True)
    task_metadata = Column(JSON, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        index=True,
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationship to task results
    result = relationship(
        "TaskResult", back_populates="task", uselist=False, cascade="all, delete-orphan"
    )

    def to_contract(self) -> TaskContract:
        """Convert database model to TaskContract."""
        return TaskContract(
            task_id=str(self.id),
            goal=self.goal,
            constraints=self.constraints or {},
            context=self.context,
            acceptance_criteria=self.acceptance_criteria or [],
            budget=ResourceBudget(**self.budget) if isinstance(self.budget, dict) else self.budget,
            priority=self.priority,
            parent_task_id=str(self.parent_task_id) if self.parent_task_id else None,
            assigned_arm=self.assigned_arm,
            metadata=self.task_metadata or {},
        )

    def to_response(self) -> TaskResponse:
        """Convert database model to TaskResponse."""
        return TaskResponse(
            task_id=str(self.id),
            status=self.status,
            goal=self.goal,
            result=self.result.result if self.result else None,
            error=self.result.error if self.result else None,
            created_at=self.created_at,
            updated_at=self.updated_at,
            processing_time_ms=self.result.processing_time_ms if self.result else None,
        )


class TaskResult(Base):  # type: ignore[valid-type,misc]
    """
    Task result database model.

    Stores task execution results and errors.
    """

    __tablename__ = "task_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    task_id = Column(
        UUID(as_uuid=True), ForeignKey("tasks.id"), nullable=False, unique=True, index=True
    )
    result = Column(JSON, nullable=True)
    error = Column(Text, nullable=True)
    processing_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC))

    # Relationship to task
    task = relationship("Task", back_populates="result")
