# Architecture Decision Records (ADRs)

## Overview

This directory contains Architecture Decision Records (ADRs) documenting significant architectural decisions made in the OctoLLM project.

## What is an ADR?

An Architecture Decision Record captures an important architectural decision made along with its context and consequences. ADRs help teams understand:
- Why certain decisions were made
- What alternatives were considered
- What trade-offs were accepted
- What constraints influenced the decision

## ADR Format

Each ADR follows this structure:

```markdown
# ADR-XXX: Title

**Status**: Accepted | Rejected | Superseded | Deprecated
**Date**: YYYY-MM-DD
**Decision Makers**: Names/Roles
**Consulted**: Names/Roles

## Context

What is the issue we're seeing that motivates this decision?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?

## Alternatives Considered

What other options were evaluated?

## References

Links to relevant resources, discussions, or documentation.
```

## Index of ADRs

### Core Architecture

- [ADR-001: Technology Stack Selection](./001-technology-stack.md)
  - **Status**: Accepted
  - **Summary**: Choice of Python (FastAPI) for services, Rust for performance-critical components, PostgreSQL for data, Redis for caching, Qdrant for vectors

- [ADR-002: Communication Patterns](./002-communication-patterns.md)
  - **Status**: Accepted
  - **Summary**: HTTP/REST for synchronous operations, Redis pub/sub for events, direct HTTP for arm-to-arm communication

- [ADR-003: Memory Architecture](./003-memory-architecture.md)
  - **Status**: Accepted
  - **Summary**: Three-tier memory (PostgreSQL global, Qdrant episodic, Redis cache) with routing layer and data diodes

- [ADR-004: Security Model](./004-security-model.md)
  - **Status**: Accepted
  - **Summary**: Capability-based security with JWT tokens, PII detection in Reflex layer, defense in depth approach

- [ADR-005: Deployment Platform](./005-deployment-platform.md)
  - **Status**: Accepted
  - **Summary**: Kubernetes for production with Docker Compose for development, cloud-agnostic design

## Creating New ADRs

When making a significant architectural decision:

1. **Copy template**:
   ```bash
   cp adr/template.md adr/00X-your-decision.md
   ```

2. **Fill in details**:
   - Context: Why is this decision needed?
   - Decision: What are we doing?
   - Consequences: What are the trade-offs?
   - Alternatives: What else was considered?

3. **Review with team**:
   - Share draft ADR for feedback
   - Discuss alternatives
   - Update based on feedback

4. **Update status**:
   - Start with "Proposed"
   - Move to "Accepted" after approval
   - Update this index

5. **Link in PR**:
   - Reference ADR in pull request
   - Include ADR number in commits

## ADR Statuses

- **Proposed**: Under discussion
- **Accepted**: Decision made and approved
- **Rejected**: Decision was considered but not adopted
- **Superseded**: Replaced by a newer ADR
- **Deprecated**: No longer relevant

## When to Create an ADR

Create an ADR when making decisions about:
- Technology choices (languages, frameworks, databases)
- Architecture patterns (microservices, event-driven, etc.)
- Communication protocols (REST, gRPC, messaging)
- Data models and storage
- Security approaches
- Deployment strategies
- Major refactoring plans

## When NOT to Create an ADR

Don't create ADRs for:
- Implementation details within a component
- Code style or formatting choices (use coding standards)
- Temporary workarounds
- Bug fixes
- Minor optimizations

---

**Last Updated**: 2025-11-10
**Owner**: Architecture Team
