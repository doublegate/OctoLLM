# Layer Architecture

Detailed documentation of OctoLLM's five-layer architecture.

## Layer 1: Ingress Layer

**Components**: API Gateway, Reflex Layer
**Technology**: NGINX/Traefik + Rust
**Latency Target**: <10ms cache, <50ms reflex

The ingress layer handles all incoming requests with fast preprocessing before expensive LLM processing.

[Details: Reflex Layer](../components/reflex-layer.md)

## Layer 2: Orchestration Layer

**Components**: Orchestrator service
**Technology**: Python + FastAPI, GPT-4/Claude Opus
**Latency Target**: <500ms API calls

Strategic planning and coordination of all arms.

[Details: Orchestrator](../components/orchestrator.md)

## Layer 3: Execution Layer

**Components**: 6 specialized Arms
**Technology**: Python/Rust, various LLMs
**Latency Target**: Varies by arm

Domain-specific execution with local autonomy.

[Details: Arms](../components/arms.md)

## Layer 4: Persistence Layer

**Components**: PostgreSQL, Redis, Qdrant/Weaviate
**Technology**: Databases and vector stores

Global and local memory storage.

[Details: Persistence](../components/persistence.md)

## Layer 5: Observability Layer

**Components**: Prometheus, Loki, Jaeger, Grafana
**Technology**: Monitoring stack

Metrics, logs, and traces for debugging.

[Details: Monitoring](../operations/monitoring-alerting.md)

## See Also

- [Architecture Overview](./overview.md)
- [Data Flow](./data-flow.md)
- [System Design](./system-overview-original.md)
