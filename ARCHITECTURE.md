# OctoLLM Architecture

## System Overview

OctoLLM is a distributed AI architecture inspired by octopus neurobiology, with intelligence distributed across specialized modules coordinated by a central orchestrator.

## Core Components

### 1. Orchestrator (Brain)
- **Location**: `services/orchestrator/`
- **Language**: Python 3.11+
- **Role**: Strategic planning, task decomposition, coordination
- **Port**: 8000

### 2. Reflex Layer
- **Location**: `services/reflex-layer/`
- **Language**: Rust 1.75+
- **Role**: Fast preprocessing, caching, PII detection
- **Port**: 8001
- **Performance**: <10ms P95 latency

### 3. Specialized Arms (6 total)

#### Planner Arm
- **Location**: `services/arms/planner/`
- **Language**: Python
- **Role**: Task decomposition
- **Port**: 8010

#### Executor Arm
- **Location**: `services/arms/executor/`
- **Language**: Rust
- **Role**: Sandboxed command execution
- **Port**: 8020

#### Retriever Arm
- **Location**: `services/arms/retriever/`
- **Language**: Python
- **Role**: Knowledge retrieval and search
- **Port**: 8030

#### Coder Arm
- **Location**: `services/arms/coder/`
- **Language**: Python
- **Role**: Code generation and analysis
- **Port**: 8040

#### Judge Arm
- **Location**: `services/arms/judge/`
- **Language**: Python
- **Role**: Output validation and quality assurance
- **Port**: 8050

#### Safety Guardian Arm
- **Location**: `services/arms/safety-guardian/`
- **Language**: Python
- **Role**: PII detection, content filtering
- **Port**: 8060

## Data Stores

- **PostgreSQL**: Global memory, knowledge graph
- **Redis**: Caching layer, pub/sub
- **Qdrant**: Vector database for episodic memory

## Communication Patterns

- **HTTP/REST**: Primary communication between components
- **WebSocket**: Real-time updates (planned)
- **gRPC**: High-performance internal communication (planned)

## Deployment

- **Development**: Docker Compose (`infrastructure/docker-compose/`)
- **Production**: Kubernetes (`infrastructure/kubernetes/`)
- **Infrastructure**: Terraform (`infrastructure/terraform/`)

## Documentation

See `docs/` for comprehensive documentation:
- Architecture: `docs/architecture/`
- Components: `docs/components/`
- Implementation: `docs/implementation/`
- Operations: `docs/operations/`
