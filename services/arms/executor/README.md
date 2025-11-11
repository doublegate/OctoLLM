# Executor Arm

The Executor Arm provides sandboxed command execution with strict security controls and allowlisting.

## Architecture

- **Language**: Rust 1.75+
- **Framework**: Axum
- **Sandbox**: Docker + gVisor (optional)
- **Port**: 8020

## Features

- Command allowlisting with regex patterns
- Docker-based sandboxing
- Resource limits (CPU, memory, disk)
- Timeout enforcement
- Output capture and validation
- Comprehensive audit logging

## Project Structure

```
executor/
├── src/
│   ├── sandbox/      # Sandbox manager
│   ├── allowlist/    # Command validation
│   └── docker/       # Docker client wrapper
├── tests/            # Unit and integration tests
├── benches/          # Performance benchmarks
├── Cargo.toml        # Rust dependencies
├── Dockerfile        # Multi-stage Docker build
└── README.md         # This file
```

## Security

This is the most security-critical component. All commands:
- Must match allowlist patterns
- Run in isolated containers
- Have strict resource limits
- Cannot access host network
- Log all activity with provenance

## Development

See [Security Guide](../../../docs/security/executor-security.md) for implementation requirements.

## References

- [Component Specification](../../../docs/components/executor-arm.md)
- [Sandbox Design](../../../docs/security/sandbox-design.md)
