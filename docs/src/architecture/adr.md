# Architecture Decision Records

Architecture Decision Records (ADRs) document significant architectural choices made during OctoLLM development.

## ADR Index

1. [ADR-001: Technology Stack](./adr/001-technology-stack.md)
   - Python vs Rust for services
   - LLM provider selection
   - Database and caching choices

2. [ADR-002: Communication Patterns](./adr/002-communication-patterns.md)
   - REST vs gRPC
   - Message bus selection
   - Inter-service communication

3. [ADR-003: Memory Architecture](./adr/003-memory-architecture.md)
   - Global semantic memory design
   - Local episodic memory
   - Vector store selection

4. [ADR-004: Security Model](./adr/004-security-model.md)
   - Capability-based isolation
   - Secrets management
   - Authentication/authorization

5. [ADR-005: Deployment Platform](./adr/005-deployment-platform.md)
   - Kubernetes vs Docker Swarm
   - Cloud vs on-premise
   - Scaling strategy

6. [ADR-006: Cloud Provider Selection](./adr/006-cloud-provider-selection.md)
   - AWS vs GCP vs Azure
   - Cost considerations
   - Service availability

7. [ADR-007: Unraid Local Deployment](./adr/007-unraid-local-deployment.md)
   - Local development setup
   - Container orchestration
   - Resource management

## ADR Template

When creating new ADRs, use the following template:

```markdown
# ADR-XXX: Title

**Status**: Proposed | Accepted | Deprecated | Superseded
**Date**: YYYY-MM-DD
**Deciders**: Names
**Consulted**: Names

## Context

What is the issue we're facing?

## Decision

What did we decide?

## Consequences

What are the trade-offs?

### Positive
- Benefit 1
- Benefit 2

### Negative
- Drawback 1
- Drawback 2

## Alternatives Considered

1. Alternative 1
   - Pros
   - Cons
   - Why rejected

2. Alternative 2
   - Pros
   - Cons
   - Why rejected
```

## See Also

- [Architecture Overview](./overview.md)
- [System Design](./layers.md)
