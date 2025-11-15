# System Architecture Overview

OctoLLM implements a five-layer architecture inspired by octopus neurobiology, combining distributed intelligence with centralized governance.

## Architecture Layers

### Layer 1: Ingress (API Gateway + Reflex)

**Purpose**: Fast preprocessing and caching before expensive LLM processing.

**Technology**: NGINX/Traefik + Rust
**Latency Target**: <10ms cache hits, <50ms reflex decisions
**Current Status**: ✅ COMPLETE (Sprint 1.1, v1.1.0)

**Key Features**:
- Redis caching with <5ms latency (2x better than target)
- Pattern matching and PII detection <8ms (6x better than target)
- Request routing based on complexity
- Rate limiting and input validation

[Details: Reflex Layer Component](../components/reflex-layer.md)

### Layer 2: Orchestration (The Brain)

**Purpose**: Strategic planning, task decomposition, and arm coordination.

**Technology**: Python + FastAPI, LangChain/LlamaIndex
**Model**: GPT-4 or Claude Opus
**Current Status**: ✅ COMPLETE (Sprint 1.2, v1.2.0)

**Main Loop**:
1. Cache check (via Reflex Layer)
2. Plan generation (task decomposition)
3. Step execution (arm delegation)
4. Result integration (combining outputs)
5. Validation (quality assurance)

[Details: Orchestrator Component](../components/orchestrator.md)

### Layer 3: Execution (The Arms)

**Purpose**: Domain-specific execution with local decision-making.

**Arms Implemented**:
- ✅ **Reflex Layer** (v1.1.0) - Pattern matching, caching
- ✅ **Orchestrator** (v1.2.0) - Coordination, planning
- 🚧 **Planner Arm** (Planned Sprint 1.3) - Task decomposition
- ⏳ **Tool Executor** - Sandboxed command execution
- ⏳ **Retriever** - Knowledge base search
- ⏳ **Coder** - Code generation/debugging
- ⏳ **Judge** - Output validation
- ⏳ **Safety Guardian** - PII detection, filtering

[Details: Arms Overview](../components/arms.md)

### Layer 4: Persistence

**Purpose**: Global memory, caching, and vector stores.

**Components**:
- **PostgreSQL**: Global semantic memory (tasks, decisions, provenance)
- **Redis**: High-speed caching (responses, embeddings)
- **Qdrant/Weaviate**: Vector stores for semantic search

**Current Status**: ✅ PostgreSQL + Redis operational (Sprint 1.2)

### Layer 5: Observability

**Purpose**: Monitoring, logging, and tracing for debugging and optimization.

**Stack**:
- **Prometheus**: Metrics collection (latency, throughput, errors)
- **Loki**: Centralized logging
- **Jaeger**: Distributed tracing
- **Grafana**: Dashboards and alerting

**Current Status**: ⏳ Planned (Phase 3)

## Data Flow

```
User Request
    ↓
[API Gateway] → Reflex Layer (cache check, pattern match)
    ↓
[Orchestrator] (task decomposition, planning)
    ↓
[Arms] (parallel execution, specialized processing)
    ↓
[Orchestrator] (result aggregation, validation)
    ↓
[API Gateway] → User Response
```

Detailed flow: [Data Flow Documentation](./data-flow.md)

## Key Design Principles

1. **Modular Specialization**: Each component excels at one thing
2. **Distributed Autonomy with Centralized Governance**: Arms decide locally, brain coordinates globally
3. **Defense in Depth**: Multiple security layers (reflex, capability isolation, PII sanitization)
4. **Hierarchical Processing**: Expensive resources reserved for complex problems
5. **Active Inference**: System proactively reduces uncertainty

[Details: Architecture Principles](./layers.md)

## Performance Metrics

| Component | Metric | Target | Current |
|-----------|--------|--------|---------|
| Reflex Layer | Cache Hit Latency | <10ms | <5ms ✅ |
| Reflex Layer | Pattern Match | <50ms | <8ms ✅ |
| Orchestrator | API Latency (P95) | <500ms | <100ms ✅ |
| Orchestrator | DB Query (P95) | <10ms | <5ms ✅ |

## See Also

- [Layer Architecture Details](./layers.md)
- [Data Structures](./data-structures.md)
- [Swarm Decision Making](./swarm-decision-making.md)
- [Architecture Decision Records](./adr.md)
