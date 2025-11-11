# OctoLLM System Architecture Overview

**Version**: 1.0
**Last Updated**: 2025-11-10
**Status**: Draft

## Table of Contents

- [Introduction](#introduction)
- [Biological Inspiration](#biological-inspiration)
- [High-Level Architecture](#high-level-architecture)
- [Component Interaction](#component-interaction)
- [Data Flow](#data-flow)
- [Deployment Models](#deployment-models)
- [See Also](#see-also)

## Introduction

OctoLLM is a distributed AI architecture inspired by the octopus's nervous system, designed for offensive security operations and advanced developer tooling. Unlike monolithic LLM systems, OctoLLM distributes intelligence across specialized modules (arms) coordinated by a central orchestrator (brain).

### Design Principles

1. **Modular Specialization**: Each component excels at one thing
2. **Distributed Autonomy**: Local decisions are fast and efficient
3. **Defense in Depth**: Multiple overlapping security layers
4. **Hierarchical Processing**: Expensive resources reserved for complex problems
5. **Active Inference**: Proactive uncertainty reduction

## Biological Inspiration

The octopus provides a proven blueprint for distributed intelligence:

| Biological Feature | OctoLLM Equivalent | Benefits |
|-------------------|-------------------|----------|
| Central brain (40M neurons) | Orchestrator LLM | Strategic planning, conflict resolution |
| Autonomous arms (350M neurons) | Specialized agent modules | Domain expertise, parallel execution |
| Neural ring | Message bus/API layer | Direct inter-module communication |
| Reflexes | Preprocessing filters | Fast responses without cognition |
| Parallel exploration | Swarm decision-making | Robust solutions via ensemble |

### Key Insights

- **70% of neurons in arms**: Most processing happens locally
- **Direct arm-to-arm communication**: Not all coordination requires the brain
- **Reflexes handle routine**: Complex brain reserved for novel situations
- **Parallel processing**: Multiple arms can work independently

## High-Level Architecture

```mermaid
graph TB
    subgraph "Ingress Layer"
        API[API Gateway<br/>Auth & Rate Limiting]
        REF[Reflex Layer<br/>Cache, PII Filter, Schema Validation]
    end

    subgraph "Orchestration Layer"
        ORCH[Orchestrator Brain<br/>Planning & Coordination]
        GMEM[(Global Memory<br/>Knowledge Graph)]
    end

    subgraph "Execution Layer - Arms"
        PLAN[Planner Arm]
        RETR[Retriever Arm]
        CODE[Coder Arm]
        EXEC[Tool Executor Arm]
        JUDG[Judge Arm]
        SAFE[Safety Guardian Arm]
    end

    subgraph "Persistence Layer"
        LMEM1[(Planner Memory)]
        LMEM2[(Coder Memory)]
        LMEM3[(Retriever Memory)]
        REDIS[(Redis Cache)]
        PSQL[(PostgreSQL)]
        VECT[(Vector DB)]
    end

    subgraph "Observability"
        PROM[Prometheus]
        GRAF[Grafana]
        JAEG[Jaeger]
    end

    API --> REF
    REF --> ORCH
    ORCH <--> GMEM

    ORCH --> PLAN
    ORCH --> RETR
    ORCH --> CODE
    ORCH --> EXEC
    ORCH --> JUDG
    ORCH --> SAFE

    PLAN <--> LMEM1
    CODE <--> LMEM2
    RETR <--> LMEM3

    REF --> REDIS
    GMEM --> PSQL
    RETR --> VECT

    ORCH -.-> PROM
    PLAN -.-> PROM
    CODE -.-> PROM
    EXEC -.-> PROM

    PROM --> GRAF
    ORCH -.-> JAEG
```

## Component Interaction

### Request Processing Flow

```mermaid
sequenceDiagram
    participant User
    participant API as API Gateway
    participant Reflex as Reflex Layer
    participant Orch as Orchestrator
    participant Planner as Planner Arm
    participant Executor as Executor Arm
    participant Judge as Judge Arm

    User->>API: Submit Task Request
    API->>Reflex: Forward (after auth)

    alt Cache Hit
        Reflex-->>User: Return Cached Result
    else Novel Query
        Reflex->>Orch: Sanitized Request
        Orch->>Planner: Generate Plan
        Planner-->>Orch: Execution Plan

        loop For each step
            Orch->>Executor: Execute Step
            Executor-->>Orch: Step Result
        end

        Orch->>Judge: Validate Result
        Judge-->>Orch: Validation Status

        alt Valid
            Orch->>Reflex: Cache Result
            Orch-->>User: Final Result
        else Invalid
            Orch->>Orch: Repair Loop
        end
    end
```

### Inter-Arm Communication

Arms can communicate directly without orchestrator involvement:

```mermaid
graph LR
    PLAN[Planner Arm] -->|Task Context| EXEC[Executor Arm]
    CODE[Coder Arm] -->|Generated Code| JUDG[Judge Arm]
    JUDG -->|Validation Feedback| CODE
    RETR[Retriever Arm] -->|Context| CODE
```

## Data Flow

### Information Movement

```mermaid
flowchart TD
    INPUT[User Input] --> PII[PII Sanitization]
    PII --> CACHE{Cache?}

    CACHE -->|Hit| OUTPUT[Return to User]
    CACHE -->|Miss| PARSE[Parse Intent]

    PARSE --> PLAN[Generate Plan]
    PLAN --> SELECT[Select Arms]

    SELECT --> ARM1[Arm 1 Execution]
    SELECT --> ARM2[Arm 2 Execution]
    SELECT --> ARM3[Arm 3 Execution]

    ARM1 --> LMEM1[(Local Memory 1)]
    ARM2 --> LMEM2[(Local Memory 2)]
    ARM3 --> LMEM3[(Local Memory 3)]

    ARM1 --> INTEGRATE[Integrate Results]
    ARM2 --> INTEGRATE
    ARM3 --> INTEGRATE

    INTEGRATE --> VALIDATE[Validate]
    VALIDATE -->|Pass| GMEM[(Global Memory)]
    VALIDATE -->|Fail| REPAIR[Repair Loop]

    REPAIR --> INTEGRATE
    GMEM --> OUTPUT
```

### Memory Hierarchy

```mermaid
graph TB
    subgraph "Fast Access - <10ms"
        L1[L1: Reflex Cache<br/>Redis]
    end

    subgraph "Medium Access - 100ms"
        L2[L2: Local Arm Memory<br/>Vector DB per domain]
    end

    subgraph "Slow Access - 1s"
        L3[L3: Global Knowledge Graph<br/>PostgreSQL]
    end

    QUERY[Query] --> L1
    L1 -->|Miss| L2
    L2 -->|Miss| L3
    L3 -->|Not Found| EXT[External Sources]

    L1 -.Update.-> L2
    L2 -.Update.-> L3
```

## Deployment Models

### Development (Docker Compose)

```mermaid
graph TB
    subgraph "Developer Machine"
        DC[Docker Compose]

        subgraph "Containers"
            NGINX[NGINX]
            ORCH[Orchestrator]
            REFLEX[Reflex Layer]
            ARM1[Planner Arm]
            ARM2[Executor Arm]
            REDIS[Redis]
            PG[PostgreSQL]
        end
    end

    DEV[Developer] --> DC
    DC --> NGINX
    NGINX --> REFLEX
    REFLEX --> ORCH
    ORCH --> ARM1
    ORCH --> ARM2
```

### Production (Kubernetes)

```mermaid
graph TB
    subgraph "Kubernetes Cluster"
        ING[Ingress Controller]

        subgraph "octollm namespace"
            SVC1[orchestrator-svc]
            SVC2[reflex-svc]

            subgraph "Orchestrator Deployment"
                ORCH1[orchestrator-1]
                ORCH2[orchestrator-2]
            end

            subgraph "Reflex Deployment"
                REF1[reflex-1]
                REF2[reflex-2]
                REF3[reflex-3]
            end

            subgraph "Arm Deployments"
                ARM1[planner-arm]
                ARM2[executor-arm]
                ARM3[coder-arm]
            end
        end

        subgraph "Data Layer"
            REDIS[Redis Cluster]
            PG[PostgreSQL HA]
            QDRANT[Qdrant Vector DB]
        end

        subgraph "Monitoring"
            PROM[Prometheus]
            GRAF[Grafana]
        end
    end

    ING --> SVC2
    SVC2 --> REF1 & REF2 & REF3
    REF1 --> SVC1
    SVC1 --> ORCH1 & ORCH2
    ORCH1 --> ARM1 & ARM2 & ARM3

    ARM1 & ARM2 & ARM3 --> REDIS
    ORCH1 & ORCH2 --> PG
    ARM1 & ARM2 --> QDRANT
```

### Edge Deployment

For air-gapped or low-latency scenarios:

```mermaid
graph TB
    subgraph "Edge Location"
        EDGE[Edge Gateway]
        MINI_ORCH[Minimal Orchestrator<br/>Smaller Model]
        MINI_ARM1[Core Arms Only]
        LOCAL_CACHE[Local Cache]
    end

    subgraph "Central Cloud"
        CLOUD_ORCH[Full Orchestrator]
        ALL_ARMS[All Arms]
        CENTRAL_MEM[Central Memory]
    end

    USER[User] --> EDGE
    EDGE --> MINI_ORCH

    MINI_ORCH -->|Simple Tasks| MINI_ARM1
    MINI_ORCH -->|Complex Tasks| CLOUD_ORCH

    MINI_ARM1 --> LOCAL_CACHE
    CLOUD_ORCH --> ALL_ARMS
    ALL_ARMS --> CENTRAL_MEM

    LOCAL_CACHE -.Sync.-> CENTRAL_MEM
```

## State Management

### Orchestrator State Machine

```mermaid
stateDiagram-v2
    [*] --> Idle

    Idle --> Parsing: New Task
    Parsing --> Planning: Intent Extracted
    Parsing --> Error: Invalid Input

    Planning --> Executing: Plan Ready
    Planning --> Error: Planning Failed

    Executing --> Integrating: All Steps Done
    Executing --> Recovering: Step Failed

    Recovering --> Executing: Retry
    Recovering --> Error: Max Retries

    Integrating --> Validating: Results Combined

    Validating --> Caching: Valid
    Validating --> Repairing: Invalid

    Repairing --> Integrating: Repaired
    Repairing --> Error: Unrepairable

    Caching --> Complete: Cached
    Complete --> [*]
    Error --> [*]
```

### Arm Execution States

```mermaid
stateDiagram-v2
    [*] --> Ready

    Ready --> Processing: Task Assigned
    Processing --> Querying: Need Context
    Processing --> Executing: Direct Execution

    Querying --> LocalMemory: Check Local
    LocalMemory --> Processing: Context Found
    LocalMemory --> GlobalMemory: Not Found
    GlobalMemory --> Processing: Context Retrieved

    Executing --> SelfCheck: Execution Complete

    SelfCheck --> Confident: High Confidence
    SelfCheck --> Uncertain: Low Confidence

    Confident --> ReportSuccess: Validation Pass
    Uncertain --> EscalateOrchestrator: Need Help

    ReportSuccess --> UpdateMemory: Store Result
    UpdateMemory --> Ready

    EscalateOrchestrator --> Ready

    Processing --> ReportFailure: Error
    ReportFailure --> Ready
```

## Network Topology

### Production Network Segmentation

```mermaid
graph TB
    subgraph "Public Zone"
        LB[Load Balancer]
        WAF[Web Application Firewall]
    end

    subgraph "DMZ"
        NGINX[NGINX Ingress]
        REFLEX[Reflex Layer Pods]
    end

    subgraph "Application Zone"
        ORCH[Orchestrator Pods]
        ARMS[Arm Pods]
    end

    subgraph "Data Zone"
        DB[PostgreSQL]
        CACHE[Redis]
        VECTOR[Vector DB]
    end

    subgraph "Management Zone"
        PROM[Prometheus]
        GRAF[Grafana]
        ALERTS[AlertManager]
    end

    LB --> WAF
    WAF --> NGINX
    NGINX --> REFLEX
    REFLEX --> ORCH
    ORCH --> ARMS

    REFLEX -.-> CACHE
    ORCH -.-> DB
    ARMS -.-> VECTOR
    ARMS -.-> CACHE

    ORCH -.Metrics.-> PROM
    ARMS -.Metrics.-> PROM
    PROM --> GRAF
    PROM --> ALERTS

    style LB fill:#ff9999
    style WAF fill:#ff9999
    style NGINX fill:#ffcc99
    style REFLEX fill:#ffcc99
    style ORCH fill:#99ccff
    style ARMS fill:#99ccff
    style DB fill:#99ff99
    style CACHE fill:#99ff99
    style VECTOR fill:#99ff99
```

## Scalability Patterns

### Horizontal Scaling

| Component | Min Replicas | Max Replicas | Scale Trigger | Scale Down |
|-----------|-------------|-------------|---------------|------------|
| Reflex Layer | 3 | 20 | CPU > 60% | CPU < 30% for 5m |
| Orchestrator | 2 | 10 | Memory > 80% | Active tasks < 10 |
| Planner Arm | 1 | 5 | Queue depth > 10 | Queue empty for 10m |
| Coder Arm | 1 | 8 | Avg latency > 5s | Latency < 2s for 15m |
| Executor Arm | 2 | 15 | Active executions > 80% | < 20% for 5m |
| Judge Arm | 1 | 5 | Validation queue > 5 | Queue < 2 for 10m |

### Vertical Scaling

Resource allocation by component tier:

**Tier 1 (Lightweight)**:
- Reflex Layer: 128Mi-512Mi RAM, 100m-500m CPU
- Judge Arm: 256Mi-1Gi RAM, 200m-1000m CPU

**Tier 2 (Medium)**:
- Orchestrator: 512Mi-2Gi RAM, 500m-2000m CPU
- Planner Arm: 256Mi-1Gi RAM, 200m-1000m CPU

**Tier 3 (Heavy)**:
- Coder Arm: 1Gi-4Gi RAM, 1000m-4000m CPU
- Executor Arm: 512Mi-2Gi RAM, 500m-2000m CPU

## Performance Targets

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Reflex cache hit | > 60% | `octollm_cache_hits_total / octollm_tasks_total` |
| P50 latency | < 2s | `histogram_quantile(0.5, octollm_task_duration_seconds)` |
| P95 latency | < 10s | `histogram_quantile(0.95, octollm_task_duration_seconds)` |
| P99 latency | < 30s | `histogram_quantile(0.99, octollm_task_duration_seconds)` |
| Task success rate | > 95% | `octollm_tasks_total{status="success"} / octollm_tasks_total` |
| Cost per task | < 50% baseline | Token usage metrics |
| Orchestrator routing accuracy | > 90% | Manual evaluation |

## See Also

- [Component Specifications](../components/README.md)
- [Data Flow Diagrams](./data-flow.md)
- [Network Architecture](./network-topology.md)
- [Deployment Guide](../operations/deployment-guide.md)
- [Performance Tuning](../operations/performance-tuning.md)
