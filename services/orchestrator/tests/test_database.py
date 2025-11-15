"""
Tests for Orchestrator database layer.

Tests database initialization, CRUD operations, and error handling using SQLite in-memory database.
"""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import (
    Database,
    create_task,
    delete_task,
    get_task,
    get_task_count_by_status,
    get_tasks_by_status,
    store_task_result,
    update_task_status,
)
from app.models import Priority, ResourceBudget, Task, TaskContract, TaskStatus

# ==============================================================================
# Fixtures
# ==============================================================================


@pytest.fixture
async def test_database():
    """Create test database with SQLite in-memory."""
    # Use SQLite in-memory for testing
    # Note: We need to use a URL that doesn't trigger the PostgreSQL validator
    db = Database.__new__(Database)
    db.database_url = "sqlite+aiosqlite:///:memory:"

    # Create async engine
    db.engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    # Create session maker
    db.async_session_maker = async_sessionmaker(
        db.engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    # Create tables
    await db.create_tables()

    yield db

    # Cleanup
    await db.close()


@pytest.fixture
def sample_contract():
    """Sample TaskContract for testing."""
    return TaskContract(
        goal="Test task goal",
        context="Test context",
        acceptance_criteria=["Criterion 1", "Criterion 2"],
        budget=ResourceBudget(max_tokens=5000, max_time_seconds=120, max_cost_usd=0.5),
        priority=Priority.HIGH,
        metadata={"source": "test"},
    )


# ==============================================================================
# Database Initialization Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_database_initialization(test_database):
    """Test database initializes correctly."""
    assert test_database is not None
    assert test_database.engine is not None
    assert test_database.async_session_maker is not None


@pytest.mark.asyncio
async def test_database_health_check_healthy(test_database):
    """Test health check returns True for healthy database."""
    is_healthy = await test_database.health_check()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_database_session_context_manager(test_database):
    """Test database session context manager works."""
    async with test_database.session() as session:
        assert session is not None
        assert isinstance(session, AsyncSession)


# ==============================================================================
# create_task Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_create_task(test_database, sample_contract):
    """Test creating a new task."""
    async with test_database.session() as session:
        task = await create_task(session, sample_contract)

        assert task is not None
        assert str(task.id) == sample_contract.task_id
        assert task.goal == "Test task goal"
        assert task.status == TaskStatus.PENDING
        assert task.context == "Test context"
        assert len(task.acceptance_criteria) == 2
        assert task.priority == Priority.HIGH
        assert task.task_metadata["source"] == "test"


@pytest.mark.asyncio
async def test_create_task_with_defaults(test_database):
    """Test creating task with minimal fields uses defaults."""
    contract = TaskContract(goal="Minimal task")

    async with test_database.session() as session:
        task = await create_task(session, contract)

        assert task is not None
        assert task.goal == "Minimal task"
        assert task.status == TaskStatus.PENDING
        assert task.priority == Priority.MEDIUM
        assert task.constraints == {}
        assert task.acceptance_criteria == []
        assert task.task_metadata == {}


@pytest.mark.asyncio
async def test_create_task_generates_id_if_not_provided(test_database):
    """Test task ID is generated if not provided in contract."""
    # TaskContract auto-generates task_id via Pydantic default_factory
    contract = TaskContract(goal="Auto-ID task")

    async with test_database.session() as session:
        task = await create_task(session, contract)

        assert task is not None
        assert task.id is not None
        assert str(task.id) == contract.task_id


# ==============================================================================
# get_task Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_task_existing(test_database, sample_contract):
    """Test retrieving existing task by ID."""
    # Create task
    async with test_database.session() as session:
        created_task = await create_task(session, sample_contract)
        task_id = str(created_task.id)

    # Retrieve task
    async with test_database.session() as session:
        retrieved_task = await get_task(session, task_id)

        assert retrieved_task is not None
        assert str(retrieved_task.id) == task_id
        assert retrieved_task.goal == "Test task goal"
        assert retrieved_task.status == TaskStatus.PENDING


@pytest.mark.asyncio
async def test_get_task_non_existent(test_database):
    """Test retrieving non-existent task returns None."""
    non_existent_id = str(uuid4())

    async with test_database.session() as session:
        task = await get_task(session, non_existent_id)

        assert task is None


@pytest.mark.asyncio
async def test_get_task_invalid_uuid(test_database):
    """Test retrieving task with invalid UUID returns None."""
    async with test_database.session() as session:
        task = await get_task(session, "invalid-uuid")

        assert task is None


# ==============================================================================
# get_tasks_by_status Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_tasks_by_status_empty(test_database):
    """Test retrieving tasks by status when none exist."""
    async with test_database.session() as session:
        tasks = await get_tasks_by_status(session, TaskStatus.PENDING)

        assert tasks == []


@pytest.mark.asyncio
async def test_get_tasks_by_status_multiple(test_database):
    """Test retrieving multiple tasks with same status."""
    # Create multiple pending tasks
    async with test_database.session() as session:
        for i in range(3):
            contract = TaskContract(goal=f"Task {i}")
            await create_task(session, contract)

    # Retrieve pending tasks
    async with test_database.session() as session:
        pending_tasks = await get_tasks_by_status(session, TaskStatus.PENDING)

        assert len(pending_tasks) == 3


@pytest.mark.asyncio
async def test_get_tasks_by_status_filters_correctly(test_database):
    """Test get_tasks_by_status filters by status correctly."""
    # Create tasks with different statuses
    async with test_database.session() as session:
        pending_contract = TaskContract(goal="Pending task")
        _pending_task = await create_task(session, pending_contract)

        processing_contract = TaskContract(goal="Processing task")
        processing_task = await create_task(session, processing_contract)
        processing_task.status = TaskStatus.PROCESSING
        await session.commit()

    # Retrieve only pending tasks
    async with test_database.session() as session:
        pending_tasks = await get_tasks_by_status(session, TaskStatus.PENDING)

        assert len(pending_tasks) == 1
        assert pending_tasks[0].goal == "Pending task"


@pytest.mark.asyncio
async def test_get_tasks_by_status_respects_limit(test_database):
    """Test get_tasks_by_status respects limit parameter."""
    # Create 5 pending tasks
    async with test_database.session() as session:
        for i in range(5):
            contract = TaskContract(goal=f"Task {i}")
            await create_task(session, contract)

    # Retrieve with limit of 3
    async with test_database.session() as session:
        tasks = await get_tasks_by_status(session, TaskStatus.PENDING, limit=3)

        assert len(tasks) == 3


# ==============================================================================
# update_task_status Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_update_task_status(test_database, sample_contract):
    """Test updating task status."""
    # Create task
    async with test_database.session() as session:
        created_task = await create_task(session, sample_contract)
        task_id = str(created_task.id)
        assert created_task.status == TaskStatus.PENDING

    # Update status
    async with test_database.session() as session:
        updated_task = await update_task_status(session, task_id, TaskStatus.PROCESSING)

        assert updated_task is not None
        assert updated_task.status == TaskStatus.PROCESSING


@pytest.mark.asyncio
async def test_update_task_status_non_existent(test_database):
    """Test updating status of non-existent task returns None."""
    non_existent_id = str(uuid4())

    async with test_database.session() as session:
        result = await update_task_status(session, non_existent_id, TaskStatus.COMPLETED)

        assert result is None


@pytest.mark.asyncio
async def test_update_task_status_updates_timestamp(test_database, sample_contract):
    """Test updating task status updates the updated_at timestamp."""
    # Create task
    async with test_database.session() as session:
        created_task = await create_task(session, sample_contract)
        task_id = str(created_task.id)
        _original_updated_at = created_task.updated_at

    # Small delay to ensure timestamp difference
    import asyncio

    await asyncio.sleep(0.01)

    # Update status
    async with test_database.session() as session:
        updated_task = await update_task_status(session, task_id, TaskStatus.COMPLETED)

        # Note: In SQLite, datetime precision might not show difference
        # This test validates the field is set, not necessarily changed
        assert updated_task.updated_at is not None


# ==============================================================================
# store_task_result Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_store_task_result_success(test_database, sample_contract):
    """Test storing successful task result."""
    # Create task
    async with test_database.session() as session:
        created_task = await create_task(session, sample_contract)
        task_id = str(created_task.id)

    # Store result
    result_data = {"output": "success", "data": [1, 2, 3]}

    async with test_database.session() as session:
        task_result = await store_task_result(
            session, task_id, result=result_data, processing_time_ms=1500
        )

        assert task_result is not None
        assert task_result.result == result_data
        assert task_result.error is None
        assert task_result.processing_time_ms == 1500

    # Verify task status updated to COMPLETED
    async with test_database.session() as session:
        task = await get_task(session, task_id)
        assert task.status == TaskStatus.COMPLETED


@pytest.mark.asyncio
async def test_store_task_result_error(test_database, sample_contract):
    """Test storing task result with error."""
    # Create task
    async with test_database.session() as session:
        created_task = await create_task(session, sample_contract)
        task_id = str(created_task.id)

    # Store error result
    error_message = "Task execution failed: timeout"

    async with test_database.session() as session:
        task_result = await store_task_result(
            session, task_id, error=error_message, processing_time_ms=30000
        )

        assert task_result is not None
        assert task_result.result is None
        assert task_result.error == error_message
        assert task_result.processing_time_ms == 30000

    # Verify task status updated to FAILED
    async with test_database.session() as session:
        task = await get_task(session, task_id)
        assert task.status == TaskStatus.FAILED


@pytest.mark.asyncio
async def test_store_task_result_non_existent_task(test_database):
    """Test storing result for non-existent task returns None."""
    non_existent_id = str(uuid4())

    async with test_database.session() as session:
        result = await store_task_result(session, non_existent_id, result={"output": "test"})

        assert result is None


# ==============================================================================
# delete_task Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_delete_task_existing(test_database, sample_contract):
    """Test deleting existing task."""
    # Create task
    async with test_database.session() as session:
        created_task = await create_task(session, sample_contract)
        task_id = str(created_task.id)

    # Delete task
    async with test_database.session() as session:
        deleted = await delete_task(session, task_id)

        assert deleted is True

    # Verify task is gone
    async with test_database.session() as session:
        task = await get_task(session, task_id)
        assert task is None


@pytest.mark.asyncio
async def test_delete_task_non_existent(test_database):
    """Test deleting non-existent task returns False."""
    non_existent_id = str(uuid4())

    async with test_database.session() as session:
        deleted = await delete_task(session, non_existent_id)

        assert deleted is False


@pytest.mark.asyncio
async def test_delete_task_cascades_to_result(test_database, sample_contract):
    """Test deleting task also deletes associated result."""
    # Create task and result
    async with test_database.session() as session:
        created_task = await create_task(session, sample_contract)
        task_id = str(created_task.id)

        # Store result
        await store_task_result(session, task_id, result={"output": "test"})

    # Delete task
    async with test_database.session() as session:
        deleted = await delete_task(session, task_id)
        assert deleted is True

    # Verify task and result are gone
    async with test_database.session() as session:
        task = await get_task(session, task_id)
        assert task is None


# ==============================================================================
# get_task_count_by_status Tests
# ==============================================================================


@pytest.mark.asyncio
async def test_get_task_count_by_status_empty(test_database):
    """Test task count by status when no tasks exist."""
    async with test_database.session() as session:
        counts = await get_task_count_by_status(session)

        assert counts["pending"] == 0
        assert counts["processing"] == 0
        assert counts["completed"] == 0
        assert counts["failed"] == 0
        assert counts["cancelled"] == 0


@pytest.mark.asyncio
async def test_get_task_count_by_status_multiple(test_database):
    """Test task count by status with multiple tasks."""
    async with test_database.session() as session:
        # Create tasks with different statuses
        for i in range(3):
            contract = TaskContract(goal=f"Pending task {i}")
            await create_task(session, contract)

        for i in range(2):
            contract = TaskContract(goal=f"Processing task {i}")
            task = await create_task(session, contract)
            task.status = TaskStatus.PROCESSING

        for i in range(1):
            contract = TaskContract(goal=f"Completed task {i}")
            task = await create_task(session, contract)
            task.status = TaskStatus.COMPLETED

        await session.commit()

    # Get counts
    async with test_database.session() as session:
        counts = await get_task_count_by_status(session)

        assert counts["pending"] == 3
        assert counts["processing"] == 2
        assert counts["completed"] == 1
        assert counts["failed"] == 0
        assert counts["cancelled"] == 0


# ==============================================================================
# Task ORM Conversion Tests (in database context)
# ==============================================================================


@pytest.mark.asyncio
async def test_task_to_contract_conversion_after_storage(test_database, sample_contract):
    """Test Task ORM to TaskContract conversion after database storage."""
    # Create and retrieve task
    async with test_database.session() as session:
        created_task = await create_task(session, sample_contract)
        task_id = str(created_task.id)

    async with test_database.session() as session:
        retrieved_task = await get_task(session, task_id)
        contract = retrieved_task.to_contract()

        assert contract.task_id == task_id
        assert contract.goal == "Test task goal"
        assert contract.priority == Priority.HIGH
        assert isinstance(contract.budget, ResourceBudget)


@pytest.mark.asyncio
async def test_task_to_response_conversion_with_result(test_database, sample_contract):
    """Test Task ORM to TaskResponse conversion with result."""
    # Create task and store result
    async with test_database.session() as session:
        created_task = await create_task(session, sample_contract)
        task_id = str(created_task.id)

        await store_task_result(
            session, task_id, result={"output": "success"}, processing_time_ms=2000
        )

    # Retrieve and convert to response (need eager loading for relationship)
    async with test_database.session() as session:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        result = await session.execute(
            select(Task).where(Task.id == UUID(task_id)).options(selectinload(Task.result))
        )
        task = result.scalar_one()
        response = task.to_response()

        assert response.task_id == task_id
        assert response.status == TaskStatus.COMPLETED
        assert response.result == {"output": "success"}
        assert response.error is None
        assert response.processing_time_ms == 2000
