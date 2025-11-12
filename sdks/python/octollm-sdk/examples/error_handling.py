"""
Error handling example for OctoLLM Python SDK.

This example demonstrates:
- Handling different exception types
- Retry logic for transient errors
- Graceful degradation
- Error logging and debugging
"""

import asyncio
import logging
from typing import Optional
from octollm_sdk import (
    OrchestratorClient,
    TaskRequest,
    ResourceBudget,
    OctoLLMError,
    AuthenticationError,
    AuthorizationError,
    ValidationError,
    RateLimitError,
    ServiceUnavailableError,
    NotFoundError,
    TimeoutError,
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


async def submit_task_with_retry(
    client: OrchestratorClient,
    task: TaskRequest,
    max_retries: int = 3,
) -> Optional[str]:
    """
    Submit a task with automatic retry for transient errors.

    Args:
        client: OctoLLM client
        task: Task to submit
        max_retries: Maximum retry attempts

    Returns:
        Task ID if successful, None otherwise
    """
    attempt = 0

    while attempt < max_retries:
        try:
            logger.info(f"Submitting task (attempt {attempt + 1}/{max_retries})...")
            response = await client.submit_task(task)
            logger.info(f"Task submitted successfully: {response.task_id}")
            return response.task_id

        except AuthenticationError as e:
            # Authentication errors are not transient - don't retry
            logger.error(f"Authentication failed: {e.message}")
            logger.error(f"Request ID: {e.request_id}")
            logger.error("Please check your API key and try again.")
            return None

        except AuthorizationError as e:
            # Authorization errors are not transient - don't retry
            logger.error(f"Authorization failed: {e.message}")
            logger.error(f"Request ID: {e.request_id}")
            logger.error("You don't have permission to perform this operation.")
            return None

        except ValidationError as e:
            # Validation errors indicate bad input - don't retry
            logger.error(f"Validation failed: {e.message}")
            logger.error(f"Request ID: {e.request_id}")
            if e.details:
                logger.error(f"Details: {e.details}")
            logger.error("Please fix the input and try again.")
            return None

        except RateLimitError as e:
            # Rate limits are transient - retry after waiting
            logger.warning(f"Rate limit exceeded: {e.message}")
            logger.warning(f"Request ID: {e.request_id}")

            wait_time = e.retry_after or (2**attempt)
            logger.info(f"Waiting {wait_time} seconds before retry...")
            await asyncio.sleep(wait_time)
            attempt += 1
            continue

        except ServiceUnavailableError as e:
            # Service unavailable is transient - retry with backoff
            logger.warning(f"Service unavailable: {e.message}")
            logger.warning(f"Request ID: {e.request_id}")

            if attempt < max_retries - 1:
                wait_time = 2**attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                attempt += 1
                continue
            else:
                logger.error("Service unavailable after all retries")
                return None

        except TimeoutError as e:
            # Timeout errors are transient - retry
            logger.warning(f"Request timeout: {e.message}")
            logger.warning(f"Request ID: {e.request_id}")

            if attempt < max_retries - 1:
                wait_time = 2**attempt
                logger.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
                attempt += 1
                continue
            else:
                logger.error("Timeout after all retries")
                return None

        except NotFoundError as e:
            # This shouldn't happen during task submission
            logger.error(f"Unexpected NotFoundError: {e.message}")
            logger.error(f"Request ID: {e.request_id}")
            return None

        except OctoLLMError as e:
            # Generic API error
            logger.error(f"API error: {e.message}")
            logger.error(f"Status code: {e.status_code}")
            logger.error(f"Request ID: {e.request_id}")
            if e.details:
                logger.error(f"Details: {e.details}")

            # Retry on 5xx errors
            if e.status_code and e.status_code >= 500:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.info(f"Server error, retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    attempt += 1
                    continue

            return None

        except Exception as e:
            # Unexpected errors
            logger.exception(f"Unexpected error: {e}")
            return None

    logger.error(f"Failed to submit task after {max_retries} attempts")
    return None


async def check_task_with_error_handling(client: OrchestratorClient, task_id: str) -> None:
    """
    Check task status with comprehensive error handling.

    Args:
        client: OctoLLM client
        task_id: Task ID to check
    """
    try:
        logger.info(f"Checking status for task {task_id}...")
        status = await client.get_task(task_id)

        logger.info(f"Task status: {status.status}")

        if status.status == "completed" and status.result:
            logger.info(f"Task completed with confidence: {status.result.confidence:.2%}")
            logger.info(f"Validation passed: {status.result.validation_passed}")

        elif status.status == "failed" and status.error:
            logger.error(f"Task failed: {status.error.message}")
            if status.error.details:
                logger.error(f"Details: {status.error.details}")

    except NotFoundError as e:
        logger.error(f"Task not found: {task_id}")
        logger.error(f"Request ID: {e.request_id}")
        logger.error("The task may have been deleted or never existed.")

    except AuthenticationError as e:
        logger.error(f"Authentication failed while checking task: {e.message}")

    except OctoLLMError as e:
        logger.error(f"Error checking task status: {e.message}")
        if e.request_id:
            logger.error(f"Request ID: {e.request_id}")


async def demonstrate_graceful_degradation():
    """Demonstrate graceful degradation when services are unavailable."""
    logger.info("\nDemonstrating graceful degradation...")

    # Try primary orchestrator
    primary_client = OrchestratorClient(
        base_url="http://localhost:8000",
        api_key="sk-test-key",
        timeout=5.0,  # Short timeout for quick failover
    )

    # Fallback orchestrator (e.g., different region)
    fallback_client = OrchestratorClient(
        base_url="http://backup.octollm.example.com:8000",
        api_key="sk-test-key",
        timeout=5.0,
    )

    task = TaskRequest(
        goal="Simple test task",
        budget=ResourceBudget(max_tokens=1000),
    )

    # Try primary first
    logger.info("Attempting primary orchestrator...")
    try:
        response = await primary_client.submit_task(task)
        logger.info(f"Primary orchestrator succeeded: {response.task_id}")
        return response.task_id
    except (ServiceUnavailableError, TimeoutError) as e:
        logger.warning(f"Primary orchestrator failed: {e.message}")
        logger.info("Failing over to backup orchestrator...")

        # Try fallback
        try:
            response = await fallback_client.submit_task(task)
            logger.info(f"Backup orchestrator succeeded: {response.task_id}")
            return response.task_id
        except Exception as e:
            logger.error(f"Backup orchestrator also failed: {e}")
            logger.error("All orchestrators unavailable - degraded operation mode")
            return None


async def main():
    """Main demonstration function."""
    logger.info("OctoLLM SDK Error Handling Examples")
    logger.info("=" * 80)

    # Example 1: Submit task with retry logic
    logger.info("\n1. Task submission with automatic retry")
    client = OrchestratorClient(
        base_url="http://localhost:8000",
        api_key="sk-your-api-key-here",
        max_retries=3,
    )

    task = TaskRequest(
        goal="Create a Python function to calculate factorial",
        constraints=["Use recursion", "Include type hints"],
        budget=ResourceBudget(max_tokens=2000, max_time_seconds=20),
    )

    task_id = await submit_task_with_retry(client, task, max_retries=3)

    if task_id:
        logger.info(f"Task submitted successfully: {task_id}")

        # Example 2: Check task status with error handling
        logger.info("\n2. Checking task status with error handling")
        await check_task_with_error_handling(client, task_id)

        # Example 3: Try to check non-existent task
        logger.info("\n3. Attempting to check non-existent task")
        await check_task_with_error_handling(client, "task_nonexistent123")
    else:
        logger.error("Failed to submit task")

    # Example 4: Graceful degradation
    logger.info("\n4. Graceful degradation example")
    await demonstrate_graceful_degradation()

    logger.info("\n" + "=" * 80)
    logger.info("Error handling demonstration complete")


if __name__ == "__main__":
    asyncio.run(main())
