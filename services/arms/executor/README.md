# Executor Arm

The Executor Arm runs external commands and tools in isolated, sandboxed environments.

## Overview

- **Language**: Rust 1.75+
- **Sandboxing**: Docker containers, gVisor (optional)
- **Security**: Command allowlisting, resource limits, network isolation
- **Capabilities**: Shell commands, HTTP requests, file operations

## Security Model

- **Allowlisting**: Only pre-approved commands executable
- **Resource Limits**: CPU (1 core), Memory (512MB), Disk (1GB), Time (60s)
- **Network**: Outbound HTTPS only, no internal network access
- **Filesystem**: Read-only mounted volumes, ephemeral workspace

## Supported Tools

- Shell: bash, python3, node, curl, git
- Security: nmap, nikto, sqlmap, metasploit
- Development: cargo, npm, pip, docker

## Development

```bash
cd services/arms/executor
cargo build --release
cargo test
cargo run --release
```

## References

- [Executor Arm Specification](../../../docs/components/arms/executor.md)
- [Security Hardening](../../../docs/security/capability-isolation.md)
