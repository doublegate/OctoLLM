# Shared Libraries

This directory contains shared code, schemas, and types used across multiple OctoLLM services.

## Structure

```
shared/
├── proto/              # Protocol Buffer definitions (future)
├── schemas/            # JSON schemas for validation
├── types/              # Shared type definitions
├── python/             # Python shared libraries
│   ├── common/        # Common utilities
│   ├── models/        # Pydantic models
│   └── clients/       # Client libraries
└── rust/               # Rust shared libraries
    ├── common/        # Common utilities
    ├── types/         # Type definitions
    └── clients/       # Client libraries
```

## Python Shared Library

The Python shared library (`shared/python/`) provides:
- **Common Models**: Pydantic models for TaskContract, ArmCapability, etc.
- **Database Clients**: PostgreSQL, Redis, Qdrant connection managers
- **LLM Clients**: OpenAI and Anthropic SDK wrappers
- **Observability**: Logging, metrics, tracing utilities

## Rust Shared Library

The Rust shared library (`shared/rust/`) provides:
- **Common Types**: Shared data structures
- **Error Handling**: Custom error types
- **Serialization**: Serde implementations
- **Utilities**: Helper functions

## Usage

### Python

```python
from octollm_common.models import TaskContract, ArmCapability
from octollm_common.db import get_postgres_client, get_redis_client
from octollm_common.llm import OpenAIClient, AnthropicClient
```

### Rust

```rust
use octollm_common::{TaskContract, ArmCapability};
use octollm_common::error::{OctoLLMError, Result};
```

## References

- [API Contracts](../docs/api/component-contracts.md)
- [Data Models](../docs/architecture/data-models.md)
