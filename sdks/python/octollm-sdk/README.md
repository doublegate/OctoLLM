# OctoLLM Python SDK

Official Python client library for the [OctoLLM](https://github.com/octollm/octollm) distributed AI architecture.

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![Version](https://img.shields.io/badge/version-0.4.0-brightgreen)](https://github.com/octollm/octollm)

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Authentication](#authentication)
- [Usage Examples](#usage-examples)
- [Service Clients](#service-clients)
- [Error Handling](#error-handling)
- [Configuration](#configuration)
- [Development](#development)
- [Contributing](#contributing)
- [License](#license)

## Overview

OctoLLM is a distributed AI architecture inspired by octopus neurobiology, featuring:
- **Central Brain (Orchestrator)**: Strategic planning and coordination
- **Autonomous Arms**: Specialized domain experts (Planner, Coder, Judge, etc.)
- **Reflex Layer**: Fast preprocessing without LLM involvement
- **Distributed Memory**: Global semantic + local episodic stores

This SDK provides type-safe, async Python clients for all OctoLLM services with automatic retry, error handling, and comprehensive documentation.

## Features

✨ **Complete Service Coverage**
- All 8 OctoLLM services (Orchestrator, Reflex, Planner, Executor, Retriever, Coder, Judge, Safety Guardian)
- Type-safe Pydantic models matching OpenAPI 3.0 specifications
- Comprehensive docstrings and type hints

🔒 **Robust Authentication**
- API key authentication (external clients)
- Bearer token authentication (inter-service)
- Environment variable configuration
- Flexible configuration management

🔄 **Reliability Features**
- Automatic retry with exponential backoff
- Request ID tracking for distributed tracing
- Configurable timeouts (per-request and global)
- Circuit breaker pattern support

📝 **Developer Experience**
- Async/await support with `httpx`
- Clear exception hierarchy
- Comprehensive examples
- Full IDE autocomplete support

## Installation

### Requirements

- Python 3.11 or higher
- OctoLLM services running (local or remote)

### Install from source

```bash
# Clone repository
git clone https://github.com/octollm/octollm.git
cd octollm/sdks/python/octollm-sdk

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Install from PyPI (future)

```bash
pip install octollm-sdk
```

## Quick Start

### Submit a Task

```python
import asyncio
from octollm_sdk import OrchestratorClient, TaskRequest, ResourceBudget

async def main():
    # Initialize client
    client = OrchestratorClient(
        base_url="http://localhost:8000",
        api_key="sk-your-api-key-here"
    )

    # Create task
    task = TaskRequest(
        goal="Create a Python function to validate email addresses",
        constraints=["Include type hints", "Add docstring"],
        budget=ResourceBudget(max_tokens=5000, max_time_seconds=30)
    )

    # Submit and wait for completion
    response = await client.submit_task(task)
    print(f"Task ID: {response.task_id}")

    # Check status
    status = await client.get_task(response.task_id)
    print(f"Status: {status.status}")
    if status.result:
        print(f"Output: {status.result.output}")

asyncio.run(main())
```

### Health Check

```python
from octollm_sdk import OrchestratorClient

async def check_health():
    client = OrchestratorClient(api_key="sk-your-key")
    health = await client.health()
    print(f"Status: {health.status}")
    print(f"Version: {health.version}")

asyncio.run(check_health())
```

## Authentication

### API Key (External Clients)

```python
from octollm_sdk import OrchestratorClient

# Method 1: Pass directly
client = OrchestratorClient(
    base_url="http://localhost:8000",
    api_key="sk-12345abcdef67890"
)

# Method 2: Environment variable
# export OCTOLLM_API_KEY="sk-12345abcdef67890"
client = OrchestratorClient()  # Automatically loads from env
```

### Bearer Token (Inter-Service)

```python
from octollm_sdk import CoderClient

# Used for service-to-service communication
client = CoderClient(
    base_url="http://localhost:8005",
    bearer_token="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."
)
```

### Configuration Object

```python
from octollm_sdk import OrchestratorClient, OctoLLMConfig

# Create config
config = OctoLLMConfig(
    base_url="http://localhost:8000",
    api_key="sk-12345",
    timeout=60.0,
    max_retries=3
)

# Or load from environment
config = OctoLLMConfig.from_env()

# Use with client
client = OrchestratorClient(
    base_url=config.base_url,
    api_key=config.api_key,
    timeout=config.timeout
)
```

## Usage Examples

### Code Generation

```python
from octollm_sdk import CoderClient, CodeRequest

async def generate_code():
    client = CoderClient(api_key="sk-your-key")

    request = CodeRequest(
        operation="generate",
        prompt="Create a function to calculate Fibonacci numbers",
        language="python",
        include_tests=True,
        include_docstrings=True
    )

    result = await client.generate_code(request)
    print(f"Code:\n{result.code}")
    if result.tests:
        print(f"\nTests:\n{result.tests}")

asyncio.run(generate_code())
```

### Knowledge Retrieval

```python
from octollm_sdk import RetrieverClient, SearchRequest

async def search_knowledge():
    client = RetrieverClient(api_key="sk-your-key")

    request = SearchRequest(
        query="nginx security vulnerabilities",
        method="hybrid",
        max_results=5
    )

    results = await client.search(request)
    print(f"Found {results.total_results} results")
    for result in results.results:
        print(f"- {result.content[:100]}... (score: {result.score:.2f})")

asyncio.run(search_knowledge())
```

### Output Validation

```python
from octollm_sdk import JudgeClient, ValidationRequest

async def validate_output():
    client = JudgeClient(api_key="sk-your-key")

    request = ValidationRequest(
        output="def validate_email(email):\n    return '@' in email",
        acceptance_criteria=[
            "Function includes type hints",
            "Function includes docstring"
        ],
        output_type="python_code"
    )

    result = await client.validate(request)
    print(f"Valid: {result.valid}")
    print(f"Quality score: {result.quality_score:.2%}")
    for issue in result.issues:
        print(f"- [{issue.severity}] {issue.message}")

asyncio.run(validate_output())
```

### Safety Checks

```python
from octollm_sdk import SafetyGuardianClient, SafetyRequest

async def check_safety():
    client = SafetyGuardianClient(api_key="sk-your-key")

    request = SafetyRequest(
        content="My SSN is 123-45-6789",
        check_types=["pii"],
        sanitize=True
    )

    result = await client.check_safety(request)
    print(f"Safe: {result.safe}")
    print(f"Risk score: {result.risk_score}")
    print(f"Sanitized: {result.sanitized_content}")

asyncio.run(check_safety())
```

### Concurrent Tasks

```python
import asyncio
from octollm_sdk import OrchestratorClient, TaskRequest, ResourceBudget

async def submit_task(client, goal):
    task = TaskRequest(
        goal=goal,
        budget=ResourceBudget(max_tokens=3000)
    )
    response = await client.submit_task(task)
    return response.task_id

async def concurrent_tasks():
    client = OrchestratorClient(api_key="sk-your-key")

    tasks = [
        "Create a function for Fibonacci",
        "Create a function for factorial",
        "Create a function for prime check"
    ]

    # Submit all tasks concurrently
    task_ids = await asyncio.gather(*[
        submit_task(client, goal) for goal in tasks
    ])

    print(f"Submitted {len(task_ids)} tasks: {task_ids}")

asyncio.run(concurrent_tasks())
```

## Service Clients

### OrchestratorClient (Port 8000)

Central brain that coordinates task execution.

**Methods:**
- `health()` - Check service health
- `submit_task(task)` - Submit new task
- `get_task(task_id)` - Get task status
- `cancel_task(task_id)` - Cancel running task
- `list_arms()` - List registered arms
- `get_metrics()` - Get Prometheus metrics

### ReflexClient (Port 8001)

Fast preprocessing layer (cache, PII detection, injection detection).

**Methods:**
- `health()` - Check service health
- `preprocess(request)` - Preprocess input text
- `get_cache_stats()` - Get cache statistics
- `clear_cache()` - Clear cache

### PlannerClient (Port 8002)

Task decomposition and execution planning.

**Methods:**
- `health()` - Check service health
- `create_plan(request)` - Create execution plan
- `get_capabilities()` - Get planner capabilities

### ExecutorClient (Port 8003)

Sandboxed command execution.

**Methods:**
- `health()` - Check service health
- `execute(request)` - Execute command in sandbox
- `get_capabilities()` - Get executor capabilities

### RetrieverClient (Port 8004)

Knowledge base search (vector + keyword + hybrid).

**Methods:**
- `health()` - Check service health
- `search(request)` - Search knowledge base
- `get_capabilities()` - Get retriever capabilities

### CoderClient (Port 8005)

Code generation, debugging, and refactoring.

**Methods:**
- `health()` - Check service health
- `generate_code(request)` - Generate/debug/refactor code
- `get_capabilities()` - Get coder capabilities

### JudgeClient (Port 8006)

Output validation and quality assurance.

**Methods:**
- `health()` - Check service health
- `validate(request)` - Validate output against criteria
- `get_capabilities()` - Get judge capabilities

### SafetyGuardianClient (Port 8007)

PII detection and content filtering.

**Methods:**
- `health()` - Check service health
- `check_safety(request)` - Perform safety checks
- `get_capabilities()` - Get safety guardian capabilities

## Error Handling

The SDK provides a clear exception hierarchy:

```python
from octollm_sdk import (
    OctoLLMError,           # Base exception
    AuthenticationError,    # 401 errors
    AuthorizationError,     # 403 errors
    ValidationError,        # 400/422 errors
    NotFoundError,          # 404 errors
    RateLimitError,         # 429 errors
    ServiceUnavailableError,# 503 errors
    TimeoutError,           # Timeout errors
    APIError,               # Generic API errors
)

async def handle_errors():
    client = OrchestratorClient(api_key="sk-your-key")

    try:
        response = await client.submit_task(task)
    except AuthenticationError as e:
        print(f"Auth failed: {e.message}")
        print(f"Request ID: {e.request_id}")
    except ValidationError as e:
        print(f"Validation failed: {e.message}")
        print(f"Details: {e.details}")
    except RateLimitError as e:
        print(f"Rate limited, retry after {e.retry_after}s")
    except OctoLLMError as e:
        print(f"API error: {e.message}")
```

### Automatic Retry

The SDK automatically retries transient errors:

```python
client = OrchestratorClient(
    api_key="sk-your-key",
    max_retries=3,  # Retry up to 3 times
    timeout=30.0     # 30 second timeout per request
)

# Automatically retries on:
# - Network errors (exponential backoff)
# - Rate limits (respects Retry-After header)
# - 5xx server errors
# - Timeouts
```

## Configuration

### Environment Variables

```bash
# Base configuration
export OCTOLLM_BASE_URL="http://localhost:8000"
export OCTOLLM_API_KEY="sk-12345abcdef67890"

# Optional configuration
export OCTOLLM_TIMEOUT="60.0"
export OCTOLLM_MAX_RETRIES="3"
export OCTOLLM_VERIFY_SSL="true"

# Bearer token (alternative to API key)
export OCTOLLM_BEARER_TOKEN="eyJ0eXAiOi..."
```

### Configuration Object

```python
from octollm_sdk import OctoLLMConfig

# Manual configuration
config = OctoLLMConfig(
    base_url="http://localhost:8000",
    api_key="sk-12345",
    timeout=60.0,
    max_retries=3,
    verify_ssl=True
)

# Load from environment
config = OctoLLMConfig.from_env()
```

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/octollm/octollm.git
cd octollm/sdks/python/octollm-sdk

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install with development dependencies
pip install -e ".[dev]"
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=octollm_sdk --cov-report=html

# Run specific test file
pytest tests/test_client.py
```

### Code Quality

```bash
# Format code
black octollm_sdk tests examples

# Lint code
ruff octollm_sdk tests examples

# Type check
mypy octollm_sdk
```

### Run Examples

```bash
# Start OctoLLM services (Docker Compose)
docker-compose up -d

# Run examples
python examples/basic_usage.py
python examples/async_usage.py
python examples/error_handling.py
python examples/authentication.py
```

## API Documentation

For complete API documentation, see:
- [API Overview](../../../docs/api/API-OVERVIEW.md)
- [OpenAPI Specifications](../../../docs/api/openapi/)
- [Service Documentation](../../../docs/api/services/)

## Contributing

Contributions are welcome! Please read our [Contributing Guide](../../../CONTRIBUTING.md) for details on:
- Code of Conduct
- Development workflow
- Coding standards
- Pull request process

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## Support

- **Documentation**: https://docs.octollm.example.com
- **Issues**: https://github.com/octollm/octollm/issues
- **Discussions**: https://github.com/octollm/octollm/discussions

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for a list of changes in each version.

## Acknowledgments

- Inspired by octopus neurobiology and distributed intelligence
- Built with [Pydantic](https://pydantic-docs.helpmanual.io/) for data validation
- HTTP client powered by [httpx](https://www.python-httpx.org/)
