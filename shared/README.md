# Shared Libraries

Common code shared across multiple services in the OctoLLM monorepo.

## Structure

```
shared/
├── proto/              # Protocol Buffers definitions (gRPC)
├── schemas/            # JSON schemas for API contracts
├── types/              # Language-agnostic type definitions
├── python/             # Python shared libraries
│   ├── common/         # Common utilities
│   ├── models/         # Pydantic models
│   └── clients/        # API clients for inter-service communication
└── rust/               # Rust shared libraries
    ├── common/         # Common utilities
    ├── types/          # Rust type definitions
    └── clients/        # API clients for inter-service communication
```

## Protocol Buffers

gRPC service definitions for high-performance inter-service communication:

- `task_contract.proto` - Core TaskContract message
- `arm_capability.proto` - Arm capability registry
- `execution_state.proto` - Execution tracking

Generate code:
```bash
cd shared/proto
./generate.sh  # Generates Python and Rust code
```

## Python Shared Libraries

Install as local package:
```bash
cd shared/python
poetry install
```

Key modules:
- `common.logging` - Structured logging setup
- `common.metrics` - Prometheus metrics helpers
- `common.cache` - Redis caching utilities
- `models.task_contract` - TaskContract Pydantic model
- `clients.orchestrator` - Orchestrator API client

## Rust Shared Libraries

Add to Cargo.toml:
```toml
[dependencies]
octollm-common = { path = "../../shared/rust/common" }
octollm-types = { path = "../../shared/rust/types" }
```

Key crates:
- `octollm-common` - Common utilities (error handling, tracing)
- `octollm-types` - Core type definitions (TaskContract, ArmCapability)
- `octollm-clients` - Async HTTP clients for services

## Development

```bash
# Python
cd shared/python
poetry run pytest tests/ -v

# Rust
cd shared/rust
cargo test --all
```

## References

- [API Contracts](../docs/api/component-contracts.md)
- [Integration Patterns](../docs/implementation/integration-patterns.md)
