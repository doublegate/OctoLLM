"""
Async usage example for OctoLLM Python SDK.

This example demonstrates:
- Submitting multiple tasks concurrently
- Using async context managers
- Parallel task execution
- Gathering results from multiple tasks
"""

import asyncio
from octollm_sdk import (
    OrchestratorClient,
    TaskRequest,
    ResourceBudget,
    CoderClient,
    JudgeClient,
)


async def submit_code_task(client: OrchestratorClient, task_description: str) -> dict:
    """Submit a code generation task and wait for completion."""
    task = TaskRequest(
        goal=task_description,
        constraints=["Include type hints", "Add docstring"],
        budget=ResourceBudget(max_tokens=3000, max_time_seconds=30),
    )

    # Submit task
    response = await client.submit_task(task)
    task_id = response.task_id

    # Poll until completion
    while True:
        status = await client.get_task(task_id)

        if status.status == "completed":
            return {
                "task_id": task_id,
                "goal": task_description,
                "success": True,
                "output": status.result.output if status.result else None,
                "metadata": status.metadata,
            }
        elif status.status == "failed":
            return {
                "task_id": task_id,
                "goal": task_description,
                "success": False,
                "error": status.error.message if status.error else "Unknown error",
            }

        await asyncio.sleep(1)


async def main():
    # Initialize client
    client = OrchestratorClient(
        base_url="http://localhost:8000",
        api_key="sk-your-api-key-here",
    )

    # Define multiple tasks to execute concurrently
    tasks = [
        "Create a Python function to calculate Fibonacci numbers recursively",
        "Create a Python function to validate IPv4 addresses",
        "Create a Python function to convert temperature between C and F",
        "Create a Python function to check if a string is a palindrome",
    ]

    print(f"Submitting {len(tasks)} tasks concurrently...")
    print()

    # Submit all tasks concurrently
    results = await asyncio.gather(
        *[submit_code_task(client, task) for task in tasks],
        return_exceptions=True,
    )

    # Process results
    print("\nResults:")
    print("=" * 80)

    successful = 0
    failed = 0

    for i, result in enumerate(results, 1):
        if isinstance(result, Exception):
            print(f"\n{i}. Task failed with exception: {result}")
            failed += 1
            continue

        print(f"\n{i}. {result['goal']}")
        print(f"   Task ID: {result['task_id']}")

        if result["success"]:
            print("   Status: ✓ SUCCESS")
            if result.get("metadata"):
                metadata = result["metadata"]
                print(f"   Tokens: {metadata.tokens_used}")
                print(f"   Cost: ${metadata.cost_dollars:.4f}")
                print(f"   Duration: {metadata.duration_seconds:.2f}s")
            successful += 1
        else:
            print("   Status: ✗ FAILED")
            print(f"   Error: {result.get('error', 'Unknown')}")
            failed += 1

    print("\n" + "=" * 80)
    print(f"Summary: {successful} successful, {failed} failed out of {len(tasks)} tasks")


async def demonstrate_direct_arm_clients():
    """Demonstrate using individual arm clients directly."""
    print("\n\nDirect Arm Client Usage:")
    print("=" * 80)

    # Use Coder Arm directly for code generation
    coder = CoderClient(
        base_url="http://localhost:8005",
        bearer_token="your-service-token",  # Inter-service auth
    )

    from octollm_sdk import CodeRequest

    code_request = CodeRequest(
        operation="generate",
        prompt="Create a function to sort a list using quicksort",
        language="python",
        include_tests=True,
        include_docstrings=True,
    )

    print("\nGenerating code with Coder Arm...")
    code_result = await coder.generate_code(code_request)

    print(f"Success: {code_result.success}")
    print(f"Confidence: {code_result.confidence:.2%}")
    print("\nGenerated code:")
    print(code_result.code)

    # Use Judge Arm to validate the generated code
    judge = JudgeClient(
        base_url="http://localhost:8006",
        bearer_token="your-service-token",
    )

    from octollm_sdk import ValidationRequest

    validation_request = ValidationRequest(
        output=code_result.code,
        acceptance_criteria=[
            "Function implements quicksort algorithm",
            "Function includes type hints",
            "Function includes docstring",
        ],
        output_type="python_code",
    )

    print("\nValidating code with Judge Arm...")
    validation_result = await judge.validate(validation_request)

    print(f"Valid: {validation_result.valid}")
    print(f"Quality score: {validation_result.quality_score:.2%}")
    print(f"Passed criteria: {len(validation_result.passed_criteria)}")
    print(f"Failed criteria: {len(validation_result.failed_criteria)}")

    if validation_result.issues:
        print("\nValidation issues:")
        for issue in validation_result.issues:
            print(f"  [{issue.severity}] {issue.message}")


if __name__ == "__main__":
    # Run main concurrent example
    asyncio.run(main())

    # Uncomment to demonstrate direct arm client usage
    # asyncio.run(demonstrate_direct_arm_clients())
