# Summary

[Introduction](./introduction.md)

---

# Project Overview

- [Vision & Goals](./overview/vision.md)
- [Core Concept](./overview/concept.md)
- [Biological Inspiration](./overview/biology.md)
- [Project Roadmap](./overview/roadmap.md)

# Architecture

- [System Overview](./architecture/overview.md)
- [Layer Architecture](./architecture/layers.md)
  - [Ingress Layer](./architecture/layers.md#ingress-layer)
  - [Orchestration Layer](./architecture/layers.md#orchestration-layer)
  - [Execution Layer](./architecture/layers.md#execution-layer)
  - [Persistence Layer](./architecture/layers.md#persistence-layer)
  - [Observability Layer](./architecture/layers.md#observability-layer)
- [Data Structures](./architecture/data-structures.md)
  - [TaskContract](./architecture/data-structures.md#taskcontract)
  - [ArmCapability](./architecture/data-structures.md#armcapability)
  - [Memory Models](./architecture/data-structures.md#memory-models)
- [Data Flow](./architecture/data-flow.md)
- [Swarm Decision Making](./architecture/swarm-decision-making.md)
- [Architecture Decision Records](./architecture/adr.md)
  - [ADR-001: Technology Stack](./architecture/adr/001-technology-stack.md)
  - [ADR-002: Communication Patterns](./architecture/adr/002-communication-patterns.md)
  - [ADR-003: Memory Architecture](./architecture/adr/003-memory-architecture.md)
  - [ADR-004: Security Model](./architecture/adr/004-security-model.md)
  - [ADR-005: Deployment Platform](./architecture/adr/005-deployment-platform.md)
  - [ADR-006: Cloud Provider Selection](./architecture/adr/006-cloud-provider-selection.md)
  - [ADR-007: Unraid Local Deployment](./architecture/adr/007-unraid-local-deployment.md)

# Components

- [Reflex Layer](./components/reflex-layer.md)
  - [Architecture](./components/reflex-layer.md#architecture)
  - [Pattern Matching](./components/reflex-layer.md#pattern-matching)
  - [Performance](./components/reflex-layer.md#performance)
  - [API Reference](./components/reflex-layer.md#api-reference)
- [Orchestrator](./components/orchestrator.md)
  - [Core Functionality](./components/orchestrator.md#core-functionality)
  - [Database Layer](./components/orchestrator.md#database-layer)
  - [API Endpoints](./components/orchestrator.md#api-endpoints)
  - [Circuit Breaker](./components/orchestrator.md#circuit-breaker)
  - [Implementation Details](./components/orchestrator.md#implementation)
- [Arms (Specialized Modules)](./components/arms.md)
  - [Planner Arm](./components/arms/planner-arm.md)
  - [Tool Executor Arm](./components/arms/executor-arm.md)
  - [Retriever Arm](./components/arms/retriever-arm.md)
  - [Coder Arm](./components/arms/coder-arm.md)
  - [Judge Arm](./components/arms/judge-arm.md)
  - [Safety Guardian Arm](./components/arms/guardian-arm.md)
- [Persistence Layer](./components/persistence.md)

# API Documentation

- [REST API Overview](./api/rest-api.md)
- [Component Contracts](./api/component-contracts.md)
- [OpenAPI Specifications](./api/openapi-specs.md)
  - [Orchestrator API](./api/openapi/orchestrator.md)
  - [Reflex Layer API](./api/openapi/reflex-layer.md)
  - [Planner Arm API](./api/openapi/planner.md)
  - [Executor Arm API](./api/openapi/executor.md)
  - [Retriever Arm API](./api/openapi/retriever.md)
  - [Coder Arm API](./api/openapi/coder.md)
  - [Judge Arm API](./api/openapi/judge.md)
  - [Safety Guardian API](./api/openapi/safety-guardian.md)
- [Data Models](./api/data-models.md)
  - [TaskContract Schema](./api/schemas/task-contract.md)
  - [ArmCapability Schema](./api/schemas/arm-capability.md)
  - [CodeGeneration Schema](./api/schemas/code-generation.md)
  - [ValidationResult Schema](./api/schemas/validation-result.md)
  - [RetrievalResult Schema](./api/schemas/retrieval-result.md)
  - [PIIDetection Schema](./api/schemas/pii-detection.md)

# Development

- [Getting Started](./development/getting-started.md)
  - [Prerequisites](./development/getting-started.md#prerequisites)
  - [Installation](./development/getting-started.md#installation)
  - [Configuration](./development/getting-started.md#configuration)
- [Development Environment](./development/dev-environment.md)
  - [Python Setup](./development/dev-environment.md#python-setup)
  - [Rust Setup](./development/dev-environment.md#rust-setup)
  - [Docker Setup](./development/dev-environment.md#docker-setup)
- [Development Workflow](./development/workflow.md)
- [Testing](./development/testing.md)
  - [Unit Tests](./development/testing.md#unit-tests)
  - [Integration Tests](./development/testing.md#integration-tests)
  - [Coverage](./development/testing.md#coverage)
  - [Testing Strategy](./development/testing.md#strategy)
- [Debugging Guide](./development/debugging.md)
- [Custom Arms](./development/custom-arms.md)
- [Integration Patterns](./development/integration-patterns.md)
- [Memory Systems](./development/memory-systems.md)
- [Contributing](./development/contributing.md)
- [Migration Guide](./development/migration-guide.md)

# Operations

- [Deployment Guide](./operations/deployment.md)
  - [Docker Compose](./operations/deployment.md#docker-compose)
  - [Kubernetes](./operations/deployment.md#kubernetes)
  - [Unraid Deployment](./operations/deployment.md#unraid)
- [Kubernetes Deployment](./operations/kubernetes-deployment.md)
- [Docker Compose Setup](./operations/docker-compose-setup.md)
- [Unraid Deployment Guide](./operations/unraid-deployment-guide.md)
- [Monitoring & Alerting](./operations/monitoring-alerting.md)
- [Monitoring Runbook](./operations/monitoring-runbook.md)
- [Alert Response Procedures](./operations/alert-response-procedures.md)
- [Troubleshooting Playbooks](./operations/troubleshooting-playbooks.md)
- [Performance Tuning](./operations/performance-tuning.md)
- [Scaling](./operations/scaling.md)
- [Disaster Recovery](./operations/disaster-recovery.md)
- [Kubernetes Access](./operations/kubernetes-access.md)

# Security

- [Security Overview](./security/overview.md)
- [Threat Model](./security/threat-model.md)
- [Security Model](./security/security-model.md)
- [Capability Isolation](./security/capability-isolation.md)
- [PII Protection](./security/pii-protection.md)
- [Secrets Management Strategy](./security/secrets-management.md)
- [Security Testing](./security/security-testing.md)
- [Compliance](./security/compliance.md)
- [Phase 0 Security Audit](./security/phase0-security-audit.md)
- [GitLeaks Configuration Audit](./security/gitleaks-configuration-audit.md)

# Engineering Standards

- [Code Review Guidelines](./engineering/code-review.md)
- [Coding Standards](./engineering/coding-standards.md)
- [Error Handling](./engineering/error-handling.md)
- [Logging & Observability](./engineering/logging-observability.md)
- [Performance Optimization](./engineering/performance-optimization.md)

# Sprint Progress

- [Sprint Overview](./sprints/overview.md)
- [Phase 0 Sprints](./sprints/phase-0/overview.md)
  - [Sprint 0.1 - Repository Setup](./sprints/phase-0/sprint-0.1.md)
  - [Sprint 0.2 - CI/CD Pipeline](./sprints/phase-0/sprint-0.2.md)
  - [Sprint 0.3 - CI/CD Complete](./sprints/phase-0/sprint-0.3.md)
  - [Sprint 0.4 - Documentation](./sprints/phase-0/sprint-0.4.md)
  - [Sprint 0.5 - Specifications](./sprints/phase-0/sprint-0.5.md)
  - [Sprint 0.6 - Integration Testing](./sprints/phase-0/sprint-0.6.md)
  - [Sprint 0.7 - Final Phase 0](./sprints/phase-0/sprint-0.7.md)
- [Phase 1 Sprints](./sprints/phase-1/overview.md)
  - [Sprint 1.1 - Reflex Layer](./sprints/phase-1/sprint-1.1.md)
  - [Sprint 1.2 - Orchestrator Core](./sprints/phase-1/sprint-1.2.md)
  - [Sprint 1.3 - Planner Arm (Planned)](./sprints/phase-1/sprint-1.3-plan.md)

# Project Tracking

- [Master TODO](./project-tracking/master-todo.md)
- [Roadmap & Phases](./project-tracking/roadmap.md)
  - [Phase 0: Project Setup](./project-tracking/phases/phase-0.md)
  - [Phase 1: Proof of Concept](./project-tracking/phases/phase-1.md)
  - [Phase 2: Core Capabilities](./project-tracking/phases/phase-2.md)
  - [Phase 3: Operations](./project-tracking/phases/phase-3.md)
  - [Phase 4: Engineering](./project-tracking/phases/phase-4.md)
  - [Phase 5: Security](./project-tracking/phases/phase-5.md)
  - [Phase 6: Production](./project-tracking/phases/phase-6.md)
- [Current Status](./project-tracking/status.md)
- [Checklists](./project-tracking/checklists.md)
  - [Testing Checklist](./project-tracking/checklists.md#testing)
  - [Security Checklist](./project-tracking/checklists.md#security)
  - [Compliance Checklist](./project-tracking/checklists.md#compliance)

# Reference

- [Configuration Reference](./reference/configuration.md)
  - [Environment Variables](./reference/configuration.md#environment-variables)
  - [Database Configuration](./reference/configuration.md#database)
  - [Service Configuration](./reference/configuration.md#services)
- [Glossary](./reference/glossary.md)
- [Architecture Diagrams](./reference/diagrams.md)
- [Documentation Summary](./reference/documentation-summary.md)

---

# Appendices

- [Appendix A: Phase Specifications](./appendix/phase-specifications.md)
  - [Phase 1 Specifications](./appendix/phase-specs/phase-1.md)
  - [Phase 2 Specifications](./appendix/phase-specs/phase-2.md)
  - [Phase 3 Specifications](./appendix/phase-specs/phase-3.md)
  - [Phase 4 Specifications](./appendix/phase-specs/phase-4.md)
- [Appendix B: Handoff Documents](./appendix/handoffs.md)
  - [Phase 0 Handoff](./appendix/handoffs/phase-0.md)
  - [Sprint 1.2 Handoff](./appendix/handoffs/sprint-1.2.md)
  - [Sprint 1.3 Handoff](./appendix/handoffs/sprint-1.3.md)
- [Appendix C: Planning Documents](./appendix/planning.md)
  - [Phase 1 Resources](./appendix/planning/phase-1-resources.md)
  - [Phase 1 Risks](./appendix/planning/phase-1-risks.md)
  - [Phase 1 Success Criteria](./appendix/planning/phase-1-success-criteria.md)
