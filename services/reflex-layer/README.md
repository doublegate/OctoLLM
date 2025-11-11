# Reflex Layer Service

The Reflex Layer provides ultra-fast preprocessing, caching, and security checks before requests reach the Orchestrator.

## Architecture

- **Language**: Rust 1.75+
- **Framework**: Axum
- **Cache**: Redis
- **Port**: 8001
- **Performance Target**: <10ms P95 latency

## Features

- Request caching (SHA-256 cache keys)
- PII detection and redaction (18+ patterns)
- Prompt injection detection
- Rate limiting
- Metrics export (Prometheus)

## Project Structure

```
reflex-layer/
├── src/
│   ├── handlers/     # HTTP request handlers
│   ├── cache/        # Redis cache manager
│   ├── pii/          # PII detection engine
│   └── metrics/      # Prometheus metrics
├── tests/            # Unit and integration tests
├── benches/          # Performance benchmarks
├── Cargo.toml        # Rust dependencies
├── Dockerfile        # Multi-stage Docker build
└── README.md         # This file
```

## Development

```bash
# Build
cargo build

# Run tests
cargo test

# Run benchmarks
cargo bench

# Check performance
cargo clippy -- -D warnings
```

## References

- [Component Specification](../../docs/components/reflex-layer.md)
- [PII Detection Guide](../../docs/security/pii-protection.md)
- [Performance Tuning](../../docs/operations/performance-tuning.md)
