"""
Basic usage example for OctoLLM Python SDK.

This example demonstrates:
- Initializing the orchestrator client
- Submitting a task
- Polling for task completion
- Handling results
"""

import asyncio
from octollm_sdk import (
    OrchestratorClient,
    TaskRequest,
    ResourceBudget,
    OctoLLMError,
)


async def main():
    # Initialize client with API key
    # You can also set OCTOLLM_API_KEY environment variable
    client = OrchestratorClient(
        base_url="http://localhost:8000",
        api_key="sk-your-api-key-here",  # Replace with your actual API key
        timeout=60.0,  # 60 second timeout
    )

    # Check service health
    print("Checking service health...")
    health = await client.health()
    print(f"Service status: {health.status}")
    print(f"Version: {health.version}")
    print()

    # Create a task request
    task = TaskRequest(
        goal="Create a Python function to validate email addresses using regex",
        constraints=[
            "Include type hints",
            "Add comprehensive docstring",
            "Handle edge cases (empty string, multiple @, etc.)",
        ],
        acceptance_criteria=[
            "Function validates RFC 5322 email format",
            "Function includes at least 3 test cases",
            "Code follows PEP 8 style guide",
        ],
        budget=ResourceBudget(
            max_tokens=5000,
            max_time_seconds=30,
            max_cost_dollars=0.10,
        ),
    )

    # Submit task
    print("Submitting task...")
    print(f"Goal: {task.goal}")
    try:
        response = await client.submit_task(task)
        print(f"Task submitted successfully!")
        print(f"Task ID: {response.task_id}")
        print(f"Status: {response.status}")
        print()
    except OctoLLMError as e:
        print(f"Error submitting task: {e}")
        return

    # Poll for completion
    print("Waiting for task completion...")
    max_attempts = 30
    attempt = 0

    while attempt < max_attempts:
        try:
            status = await client.get_task(response.task_id)

            if status.status == "completed":
                print("\nTask completed successfully!")
                if status.result:
                    print(f"Confidence: {status.result.confidence:.2%}")
                    print(f"Validation passed: {status.result.validation_passed}")
                    print("\nGenerated code:")
                    print("=" * 80)
                    print(status.result.output)
                    print("=" * 80)

                if status.metadata:
                    print(f"\nMetadata:")
                    print(f"  Arms used: {', '.join(status.metadata.arms_used)}")
                    print(f"  Tokens used: {status.metadata.tokens_used}")
                    print(f"  Cost: ${status.metadata.cost_dollars:.4f}")
                    print(f"  Duration: {status.metadata.duration_seconds:.2f}s")
                break

            elif status.status == "failed":
                print("\nTask failed!")
                if status.error:
                    print(f"Error type: {status.error.type}")
                    print(f"Error message: {status.error.message}")
                    if status.error.details:
                        print(f"Details: {status.error.details}")
                break

            elif status.status == "processing":
                if status.progress:
                    print(
                        f"Progress: {status.progress.percentage}% "
                        f"(step {status.progress.completed_steps}/{status.progress.total_steps}: "
                        f"{status.progress.current_step})"
                    )

            # Wait before next poll
            await asyncio.sleep(2)
            attempt += 1

        except OctoLLMError as e:
            print(f"Error checking task status: {e}")
            break

    if attempt >= max_attempts:
        print(f"\nTimeout: Task did not complete within {max_attempts * 2} seconds")


if __name__ == "__main__":
    asyncio.run(main())
