# Architecture Diagrams

Visual representations of OctoLLM architecture and data flow.

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         User/Client                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│              Layer 1: Ingress (Reflex Layer)                │
│  ┌──────────┐  ┌────────────┐  ┌──────────────────────┐    │
│  │ Cache    │  │ PII Filter │  │  Pattern Matching     │    │
│  │ (Redis)  │  │            │  │  (Regex/Classifier)   │    │
│  └──────────┘  └────────────┘  └──────────────────────┘    │
└─────────────────────┬───────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────────┐
│           Layer 2: Orchestration (Brain)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ Task         │  │ Plan         │  │ Result          │   │
│  │ Decomposition│  │ Generation   │  │ Integration     │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
└─────────────────────┬───────────────────────────────────────┘
                      │
          ┌───────────┴───────────┬──────────┬────────────┐
          │                       │          │            │
          ▼                       ▼          ▼            ▼
┌─────────────────────────────────────────────────────────────┐
│            Layer 3: Execution (Arms)                        │
│  ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────┐ ┌─────────┐  │
│  │Planner │ │Executor│ │Retriever │ │Coder │ │  Judge  │  │
│  └────────┘ └────────┘ └──────────┘ └──────┘ └─────────┘  │
│                         ┌──────────────┐                    │
│                         │    Safety    │                    │
│                         │   Guardian   │                    │
│                         └──────────────┘                    │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│            Layer 4: Persistence                             │
│  ┌──────────┐  ┌────────┐  ┌────────────────────────┐      │
│  │PostgreSQL│  │ Redis  │  │   Qdrant/Weaviate      │      │
│  │ (Global) │  │(Cache) │  │   (Vector Store)       │      │
│  └──────────┘  └────────┘  └────────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────┐
│         Layer 5: Observability                              │
│  ┌──────────┐  ┌──────┐  ┌────────┐  ┌────────────┐        │
│  │Prometheus│  │ Loki │  │ Jaeger │  │  Grafana   │        │
│  └──────────┘  └──────┘  └────────┘  └────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

See [Data Flow Documentation](../architecture/data-flow.md) for detailed sequence diagrams.

## Swarm Decision Making

See [Swarm Decision Making](../architecture/swarm-decision-making.md) for parallel processing patterns.

## See Also

- [System Architecture](../architecture/overview.md)
- [Component Documentation](../components/reflex-layer.md)
