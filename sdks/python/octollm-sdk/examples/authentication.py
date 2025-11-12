"""
Authentication example for OctoLLM Python SDK.

This example demonstrates:
- API key authentication (external clients)
- Bearer token authentication (inter-service)
- Environment variable configuration
- Configuration object usage
"""

import asyncio
import os
from octollm_sdk import (
    OrchestratorClient,
    CoderClient,
    TaskRequest,
    ResourceBudget,
    OctoLLMConfig,
)


async def example_api_key_auth():
    """Example 1: Direct API key authentication."""
    print("Example 1: API Key Authentication")
    print("=" * 80)

    # Method 1: Pass API key directly
    client = OrchestratorClient(
        base_url="http://localhost:8000",
        api_key="sk-12345abcdef67890",  # Your actual API key
    )

    print("Authenticating with API key...")
    health = await client.health()
    print("✓ Authentication successful!")
    print(f"  Service: {health.status}")
    print(f"  Version: {health.version}")
    print()


async def example_env_var_auth():
    """Example 2: Authentication using environment variables."""
    print("Example 2: Environment Variable Authentication")
    print("=" * 80)

    # Set environment variable (in practice, do this before running the script)
    os.environ["OCTOLLM_API_KEY"] = "sk-12345abcdef67890"
    os.environ["OCTOLLM_BASE_URL"] = "http://localhost:8000"

    # Client automatically loads from environment
    client = OrchestratorClient()  # No parameters needed!

    print("Authenticating using OCTOLLM_API_KEY environment variable...")
    health = await client.health()
    print("✓ Authentication successful!")
    print(f"  Service: {health.status}")
    print()


async def example_config_object():
    """Example 3: Using configuration object."""
    print("Example 3: Configuration Object")
    print("=" * 80)

    # Create configuration object
    config = OctoLLMConfig(
        base_url="http://localhost:8000",
        api_key="sk-12345abcdef67890",
        timeout=60.0,
        max_retries=3,
        verify_ssl=True,
    )

    print("Configuration:")
    print(f"  Base URL: {config.base_url}")
    print(f"  Timeout: {config.timeout}s")
    print(f"  Max retries: {config.max_retries}")
    print()

    # Use config with client
    client = OrchestratorClient(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout,
        max_retries=config.max_retries,
    )

    print("Authenticating with config object...")
    _health = await client.health()
    print("✓ Authentication successful!")
    print()


async def example_config_from_env():
    """Example 4: Load configuration entirely from environment."""
    print("Example 4: Load Configuration from Environment")
    print("=" * 80)

    # Set multiple environment variables
    os.environ["OCTOLLM_BASE_URL"] = "http://localhost:8000"
    os.environ["OCTOLLM_API_KEY"] = "sk-12345abcdef67890"
    os.environ["OCTOLLM_TIMEOUT"] = "45.0"
    os.environ["OCTOLLM_MAX_RETRIES"] = "5"
    os.environ["OCTOLLM_VERIFY_SSL"] = "true"

    # Load configuration from environment
    config = OctoLLMConfig.from_env()

    print("Loaded configuration from environment:")
    print(f"  Base URL: {config.base_url}")
    print(f"  Timeout: {config.timeout}s")
    print(f"  Max retries: {config.max_retries}")
    print(f"  Verify SSL: {config.verify_ssl}")
    print()

    client = OrchestratorClient(
        base_url=config.base_url,
        api_key=config.api_key,
        timeout=config.timeout,
    )

    print("Authenticating...")
    _health = await client.health()
    print("✓ Configuration and authentication successful!")
    print()


async def example_bearer_token_auth():
    """Example 5: Bearer token authentication (inter-service)."""
    print("Example 5: Bearer Token Authentication (Inter-Service)")
    print("=" * 80)

    # Bearer tokens are typically used for service-to-service communication
    # where you have a JWT token with specific capabilities

    bearer_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."  # Your JWT token

    # Use bearer token instead of API key
    _client = CoderClient(
        base_url="http://localhost:8005",
        bearer_token=bearer_token,
    )

    print("Authenticating with bearer token...")
    print("(This would be used by Orchestrator when calling Coder Arm)")

    # In practice, the orchestrator generates short-lived capability tokens
    # when delegating to arms
    print("✓ Bearer token authentication configured")
    print()


async def example_task_submission_with_auth():
    """Example 6: Complete workflow with authentication."""
    print("Example 6: Complete Task Workflow with Authentication")
    print("=" * 80)

    # Initialize client with API key
    client = OrchestratorClient(
        base_url="http://localhost:8000",
        api_key="sk-your-api-key-here",
    )

    # Verify authentication works
    print("Verifying authentication...")
    try:
        health = await client.health()
        print("✓ Authenticated successfully")
        print(f"  Service version: {health.version}")
        print()
    except Exception as e:
        print(f"✗ Authentication failed: {e}")
        return

    # Submit task
    task = TaskRequest(
        goal="Create a function to check if a number is prime",
        constraints=["Include type hints", "Add docstring"],
        budget=ResourceBudget(max_tokens=2000),
    )

    print("Submitting task...")
    response = await client.submit_task(task)
    print(f"✓ Task submitted: {response.task_id}")
    print()

    # Check task status
    print("Checking task status...")
    status = await client.get_task(response.task_id)
    print(f"✓ Task status: {status.status}")
    print()


async def example_multi_service_auth():
    """Example 7: Authenticate to multiple services."""
    print("Example 7: Multi-Service Authentication")
    print("=" * 80)

    api_key = "sk-your-api-key-here"

    # Each service client can use the same API key
    orchestrator = OrchestratorClient(base_url="http://localhost:8000", api_key=api_key)

    coder = CoderClient(base_url="http://localhost:8005", api_key=api_key)

    from octollm_sdk import JudgeClient

    judge = JudgeClient(base_url="http://localhost:8006", api_key=api_key)

    print("Checking authentication across multiple services...")

    # Check all services
    services = [
        ("Orchestrator", orchestrator),
        ("Coder", coder),
        ("Judge", judge),
    ]

    for name, client in services:
        try:
            health = await client.health()
            print(f"✓ {name}: {health.status} (v{health.version})")
        except Exception as e:
            print(f"✗ {name}: Failed ({e})")

    print()


async def main():
    """Run all authentication examples."""
    print("\nOctoLLM SDK Authentication Examples")
    print("=" * 80)
    print()

    # Note: These examples use placeholder API keys
    # Replace with actual API keys or set environment variables

    try:
        # Run examples (comment out if services not running)
        # await example_api_key_auth()
        # await example_env_var_auth()
        await example_config_object()
        await example_config_from_env()
        await example_bearer_token_auth()
        # await example_task_submission_with_auth()
        # await example_multi_service_auth()

    except Exception as e:
        print(f"Error running examples: {e}")
        print()
        print("Note: These examples require OctoLLM services to be running.")
        print("Start services with: docker-compose up -d")

    print("=" * 80)
    print("\nAuthentication Configuration Summary:")
    print()
    print("1. API Key (External Clients):")
    print("   - Pass directly: OrchestratorClient(api_key='sk-...')")
    print("   - Environment variable: export OCTOLLM_API_KEY='sk-...'")
    print()
    print("2. Bearer Token (Inter-Service):")
    print("   - Pass directly: CoderClient(bearer_token='eyJ...')")
    print("   - Environment variable: export OCTOLLM_BEARER_TOKEN='eyJ...'")
    print()
    print("3. Configuration Object:")
    print("   - Create: config = OctoLLMConfig(api_key='sk-...')")
    print("   - From env: config = OctoLLMConfig.from_env()")
    print()


if __name__ == "__main__":
    asyncio.run(main())
