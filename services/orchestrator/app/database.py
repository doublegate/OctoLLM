"""
Database layer for Orchestrator service.

Provides PostgreSQL connection pooling, session management, and CRUD operations for tasks.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import QueuePool

from app.config import get_settings
from app.models import Base, Task, TaskContract, TaskResult, TaskStatus

logger = structlog.get_logger(__name__)


class Database:
    """
    Database connection manager.

    Handles connection pooling, session management, and database initialization.
    """

    def __init__(self, database_url: str | None = None):
        """
        Initialize database connection.

        Args:
            database_url: PostgreSQL connection URL (defaults to settings)
        """
        settings = get_settings()
        self.database_url = database_url or settings.database_url

        # Convert postgresql:// to postgresql+psycopg:// for async
        if self.database_url.startswith("postgresql://"):
            async_url = self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        else:
            async_url = self.database_url

        # Create async engine with connection pooling
        self.engine = create_async_engine(
            async_url,
            poolclass=QueuePool,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            pool_timeout=settings.database_pool_timeout,
            pool_pre_ping=True,  # Verify connections before using
            echo=settings.debug,  # Log SQL queries in debug mode
        )

        # Create session factory
        self.async_session_maker = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(
            "database.initialized",
            url=self.database_url.split("@")[-1],  # Hide credentials
            pool_size=settings.database_pool_size,
        )

    async def create_tables(self) -> None:
        """Create all database tables."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("database.tables_created")

    async def drop_tables(self) -> None:
        """Drop all database tables (use with caution!)."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
        logger.warning("database.tables_dropped")

    async def close(self) -> None:
        """Close database connections."""
        await self.engine.dispose()
        logger.info("database.closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Get database session context manager.

        Usage:
            async with db.session() as session:
                task = await create_task(session, contract)
        """
        async with self.async_session_maker() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            True if database is accessible, False otherwise
        """
        try:
            async with self.session() as session:
                await session.execute(select(1))
            return True
        except Exception as e:
            logger.error("database.health_check_failed", error=str(e))
            return False


# Global database instance
_db: Database | None = None


def get_database() -> Database:
    """
    Get database singleton.

    Returns:
        Database instance
    """
    global _db
    if _db is None:
        _db = Database()
    return _db


async def reset_database() -> None:
    """Reset database singleton and close connections (useful for testing)."""
    global _db
    if _db is not None:
        await _db.close()
        _db = None


# ==============================================================================
# CRUD Operations
# ==============================================================================


async def create_task(session: AsyncSession, contract: TaskContract) -> Task:
    """
    Create a new task in the database.

    Args:
        session: Database session
        contract: Task contract

    Returns:
        Created task model
    """
    task = Task(
        id=UUID(contract.task_id) if contract.task_id else None,
        goal=contract.goal,
        status=TaskStatus.PENDING,
        constraints=contract.constraints,
        context=contract.context,
        acceptance_criteria=contract.acceptance_criteria,
        budget=contract.budget.model_dump(),
        priority=contract.priority,
        parent_task_id=UUID(contract.parent_task_id) if contract.parent_task_id else None,
        assigned_arm=contract.assigned_arm,
        task_metadata=contract.metadata,
    )

    session.add(task)
    await session.commit()
    await session.refresh(task)

    logger.info(
        "database.task_created",
        task_id=str(task.id),
        goal=task.goal[:50],
        status=task.status.value,
    )

    return task


async def get_task(session: AsyncSession, task_id: str) -> Task | None:
    """
    Get task by ID.

    Args:
        session: Database session
        task_id: Task identifier

    Returns:
        Task model if found, None otherwise
    """
    try:
        task_uuid = UUID(task_id)
    except ValueError:
        logger.warning("database.invalid_task_id", task_id=task_id)
        return None

    result = await session.execute(select(Task).where(Task.id == task_uuid))
    task: Task | None = result.scalar_one_or_none()

    if task:
        logger.debug("database.task_retrieved", task_id=task_id, status=task.status.value)
    else:
        logger.debug("database.task_not_found", task_id=task_id)

    return task


async def get_tasks_by_status(
    session: AsyncSession, status: TaskStatus, limit: int = 100
) -> list[Task]:
    """
    Get tasks by status.

    Args:
        session: Database session
        status: Task status to filter by
        limit: Maximum number of tasks to return

    Returns:
        List of task models
    """
    result = await session.execute(
        select(Task).where(Task.status == status).order_by(Task.created_at.desc()).limit(limit)
    )
    tasks = result.scalars().all()

    logger.debug("database.tasks_retrieved_by_status", status=status.value, count=len(tasks))

    return list(tasks)


async def update_task_status(
    session: AsyncSession, task_id: str, status: TaskStatus
) -> Task | None:
    """
    Update task status.

    Args:
        session: Database session
        task_id: Task identifier
        status: New status

    Returns:
        Updated task model if found, None otherwise
    """
    task = await get_task(session, task_id)
    if task is None:
        return None

    task.status = status
    task.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(task)

    logger.info(
        "database.task_status_updated",
        task_id=task_id,
        old_status=task.status.value,
        new_status=status.value,
    )

    return task


async def store_task_result(
    session: AsyncSession,
    task_id: str,
    result: dict | None = None,
    error: str | None = None,
    processing_time_ms: int | None = None,
) -> TaskResult | None:
    """
    Store task result.

    Args:
        session: Database session
        task_id: Task identifier
        result: Task result data
        error: Error message if task failed
        processing_time_ms: Processing time in milliseconds

    Returns:
        Created TaskResult model if task exists, None otherwise
    """
    task = await get_task(session, task_id)
    if task is None:
        logger.warning("database.task_not_found_for_result", task_id=task_id)
        return None

    # Create or update result
    task_result = TaskResult(
        task_id=UUID(task_id),
        result=result,
        error=error,
        processing_time_ms=processing_time_ms,
    )

    session.add(task_result)

    # Update task status based on result
    if error:
        task.status = TaskStatus.FAILED
    elif result:
        task.status = TaskStatus.COMPLETED
    task.updated_at = datetime.now(UTC)

    await session.commit()
    await session.refresh(task_result)

    logger.info(
        "database.task_result_stored",
        task_id=task_id,
        has_result=result is not None,
        has_error=error is not None,
        processing_time_ms=processing_time_ms,
    )

    return task_result


async def delete_task(session: AsyncSession, task_id: str) -> bool:
    """
    Delete task by ID.

    Args:
        session: Database session
        task_id: Task identifier

    Returns:
        True if task was deleted, False if not found
    """
    task = await get_task(session, task_id)
    if task is None:
        return False

    await session.delete(task)
    await session.commit()

    logger.info("database.task_deleted", task_id=task_id)

    return True


async def get_task_count_by_status(session: AsyncSession) -> dict[str, int]:
    """
    Get count of tasks by status.

    Args:
        session: Database session

    Returns:
        Dictionary mapping status to count
    """
    counts = {}
    for status in TaskStatus:
        result = await session.execute(select(Task).where(Task.status == status))
        counts[status.value] = len(result.scalars().all())

    return counts
