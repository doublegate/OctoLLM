# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**OctoLLM** is a distributed AI architecture for offensive security and developer tooling, inspired by octopus neurobiology. Implementation is underway: a Rust workspace (reflex layer, executor arm, three shared crates), a Python FastAPI orchestrator, six arm service images, and Python + TypeScript SDKs all exist alongside the architectural documentation.

### Core Concept

The system mirrors the octopus's distributed nervous system where:
- **Central Brain (Orchestrator)**: Strategic planning and coordination using frontier LLMs (GPT-4, Claude Opus)
- **Autonomous Arms (Specialized Modules)**: Domain-specific execution with local decision-making
- **Reflex Layer**: Fast preprocessing for common patterns without LLM involvement
- **Distributed Memory**: Global semantic memory + local episodic stores per arm

### Key Architectural Principles

1. **Modular Specialization**: Each component excels at one thing
2. **Distributed Autonomy with Centralized Governance**: Arms decide locally, brain coordinates globally
3. **Defense in Depth**: Multiple security layers (reflex preprocessing, capability isolation, PII sanitization)
4. **Hierarchical Processing**: Expensive resources reserved for complex problems
5. **Active Inference**: System proactively reduces uncertainty rather than waiting for instructions

## Documentation Structure

### Primary References (read these first)

- `ref-docs/OctoLLM-Project-Overview.md` - Strategic vision, biological inspiration, use cases, success metrics, roadmap
- `ref-docs/OctoLLM-Architecture-Implementation.md` - Technical blueprint, component specs, deployment patterns, code examples
- `ref-docs/OctoLLM-Concept_Idea.md` - Quick-start patterns and concrete design decisions

### Understanding the Architecture

**Layer 1: Ingress** (API Gateway + Reflex)
- Technology: NGINX/Traefik + Python/Rust for reflex logic
- Latency Target: <10ms for cache hits, <50ms for reflex decisions

**Layer 2: Orchestration** (The Brain)
- Technology: Python + FastAPI, LangChain/LlamaIndex
- Main Loop: Cache check → Plan generation → Step execution → Result integration → Validation

**Layer 3: Execution** (The Arms)
- **Planner Arm**: Task decomposition (Python, uses GPT-3.5-turbo)
- **Tool Executor Arm**: External actions in sandboxed environments (Rust for safety)
- **Retriever Arm**: Knowledge base search
- **Coder Arm**: Code generation, debugging, refactoring
- **Judge Arm**: Output validation and quality assurance
- **Safety Guardian Arm**: PII detection, content filtering

**Layer 4: Persistence**
- PostgreSQL (global memory), Redis (caching), Qdrant/Weaviate (vector stores)

**Layer 5: Observability**
- Prometheus (metrics), Loki (logs), Jaeger (tracing)

## Key Data Structures

**TaskContract** (core orchestration object):
- `task_id`: Unique identifier
- `goal`: Natural language description
- `constraints`: Hard constraints (time, cost, safety)
- `context`: Background information
- `acceptance_criteria`: Success conditions
- `budget`: Resource limits (tokens, time)
- `assigned_arm`: Target arm identifier

**ArmCapability** (arm registry):
- `arm_id`, `name`, `description`
- `input_schema`, `output_schema`: JSON schemas
- `capabilities`: Tags for routing (e.g., "code", "security")
- `cost_tier`: 1 (cheap) to 5 (expensive)
- `endpoint`: Kubernetes service URL

## Development Roadmap

**Phase 1: Proof of Concept** (Months 1-2) - IN PROGRESS
- Reflex preprocessing layer
- Orchestrator (basic planning/delegation)
- Two arms: Planner + Tool Executor
- Docker Compose deployment

**Phase 2: Core Capabilities** (Months 3-5)
- Additional arms: Retriever, Coder, Judge, Safety Guardian
- Kubernetes deployment
- Distributed memory system
- Swarm decision-making

**Phase 3: Optimization** (Months 6-9)
- Rust reimplementation of performance-critical arms
- Fine-tuned specialist models
- Skill distillation

**Phase 4: Production Hardening** (Months 10-12)
- Comprehensive observability
- SOC 2 / ISO 27001 compliance
- Public API and documentation

## When Implementing Components

### Technology Choices

**Orchestrator (Brain)**:
```python
# Python 3.11+, FastAPI, Pydantic
# LLM: OpenAI SDK (GPT-4) or Anthropic SDK (Claude 3)
# Dependencies: langchain, redis, psycopg, prometheus-client, structlog
```

**Reflex Layer (Performance-Critical)**:
```rust
// Rust 1.75+, actix-web
// Redis for caching, regex for PII/injection detection
// Target: <10ms latency for 95% of requests
```

**Arms (Mixed)**:
- Python for AI-heavy arms (Planner, Coder, Judge)
- Rust for security-critical arms (Tool Executor)
- Small models (Mistral 7B, GPT-3.5-turbo) for cost efficiency

### Security Patterns

1. **Capability-Based Access**: Each arm gets time-limited tokens for specific permissions
2. **Sandboxing**: Tool Executor runs in isolated containers (Docker/gVisor)
3. **PII Protection**: Input sanitization, output filtering, differential privacy
4. **Allowlisting**: Commands and hosts explicitly permitted
5. **Provenance Tracking**: Every artifact tagged with source, timestamp, confidence

### Deployment

- **Local Dev**: `docker-compose.yml` with all services
- **Production**: Kubernetes with namespace `octollm`
- **Monitoring**: Prometheus + Grafana dashboards
- **Scaling**: HorizontalPodAutoscaler based on CPU/memory

## Testing Strategy

```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests (requires services)
docker-compose up -d
pytest tests/integration/ -v

# Coverage
pytest --cov=orchestrator --cov=arms --cov-report=html
```

## Key Metrics to Track

| Metric | Target |
|--------|--------|
| Task Success Rate | >95% vs baseline |
| P99 Latency | <30s for critical tasks |
| Cost per Task | <50% of monolithic LLM |
| Reflex Cache Hit Rate | >60% over time |
| PII Leakage Rate | <0.1% of outputs |
| Prompt Injection Blocks | >99% detection |

## Important Conventions

1. **JSON Schemas**: All arm inputs/outputs validated with Pydantic schemas
2. **Provenance Metadata**: Always include `arm_id`, `timestamp`, `confidence`, `command_hash`
3. **Error Handling**: Retry logic with exponential backoff, graceful degradation
4. **Resource Limits**: Enforce timeouts (default 30s max) and token budgets
5. **Logging**: Structured logging with `structlog` (JSON format for aggregation)

## Design Patterns in Use

1. **Mixture of Experts (MoE)**: Multiple specialists with gating function
2. **Swarm Decision-Making**: N parallel proposals → aggregation → conflict resolution
3. **Hierarchical Planning**: Recursive task decomposition with acceptance criteria
4. **Active Inference Loops**: Observe → Hypothesize → Predict → Act → Update
5. **Skill Distillation**: Fine-tune smaller models from decision traces

## Future Implementation Notes

- Use LangGraph or custom state machine for workflow orchestration
- Abstract LLM calls behind provider-agnostic interface (support OpenAI, Anthropic, local models via vLLM/Ollama)
- Implement uncertainty-based routing (ML classifier predicts best arm from task features)
- Add distributed tracing with OpenTelemetry for debugging complex flows
- Consider speculative execution (predict next arm in parallel)

## Current Status

Implementation is underway. This is no longer a documentation-only repository.

### What exists

| Area | Location | State |
|---|---|---|
| Rust workspace | `Cargo.toml` (5 members) | `reflex-layer`, `arms/executor`, `shared/rust/{common,types,clients}`; 240 tests passing |
| Orchestrator | `services/orchestrator/` | FastAPI app, SQLAlchemy models, Reflex client with circuit breaker; 150 tests passing |
| Arm images | `services/arms/{coder,judge,planner,retriever,safety-guardian}/` | Dockerfiles only; no service code yet |
| Python SDK | `sdks/python/octollm-sdk/` | 8 service clients; 17 tests passing |
| TypeScript SDK | `sdks/typescript/octollm-sdk/` | 8 service clients; 22 tests passing |

### Toolchain

- **Python 3.14** (`>=3.14,<3.15` at the root; the `<3.15` bound comes from presidio).
  Service images are `python:3.14.7-slim`.
- **Rust** edition 2021, MSRV 1.91.1; builder images are `rust:1.98.1-slim`, runtime
  `debian:13.6-slim`.
- Poetry for the root Python environment; `services/orchestrator/` and each SDK carry
  their own manifest.

### Commands

```bash
# Rust
cargo clippy --workspace --all-targets --all-features -- -D warnings
cargo test --workspace
cargo fmt --all -- --check

# Python (root: ruff + black are the blocking CI gates)
ruff check .
black --check .
cd services/orchestrator && pytest tests/          # 150 tests
cd sdks/python/octollm-sdk && pytest tests/        # 17 tests

# TypeScript SDK
cd sdks/typescript/octollm-sdk && npm ci && npm run build && npm test && npm run lint
```

### What CI does and does not cover

`lint.yml` (ruff, black, rustfmt, clippy) and `security.yml` (bandit, gitleaks) are the
only blocking gates. Note the gaps before trusting a green check:

- `test.yml` runs `pytest tests/unit/` from the repository root, which contains only a
  placeholder. **The orchestrator and SDK suites are not run by CI.** The Rust test steps
  are `continue-on-error: true`.
- The TypeScript SDK has no CI job at all.
- Container builds in `build.yml` and the Trivy scan in `security.yml` are `if: false`,
  so Dockerfile changes are not validated by CI. Build them locally before merging one.

### Known gaps

- The arm services have Dockerfiles but no application code.
- `services/orchestrator/pyproject.toml` declares the OpenTelemetry dependencies that
  `app/telemetry.py` imports, but the orchestrator image installs the **root**
  `pyproject.toml`, which does not. The two manifests need reconciling before that image
  can serve traced traffic.
- The app returns `{"error": ...}` for `HTTPException` but FastAPI's default
  `{"detail": [...]}` for 422 validation errors. The envelope is inconsistent by
  accident, not design.
