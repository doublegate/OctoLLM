# ADR-007: Unraid Local Deployment Strategy

**Status**: Proposed
**Date**: 2025-11-12
**Decision Makers**: OctoLLM Architecture Team
**Consulted**: DevOps, Infrastructure Team

## Context

OctoLLM is a distributed AI architecture for offensive security and developer tooling that requires significant computational resources, particularly GPU acceleration for LLM inference. The project needs a local development deployment strategy that:

1. **Leverages Available Hardware**: Dell PowerEdge R730xd with dual Xeon E5-2683 v4 (64 threads), 504GB RAM, and NVIDIA Tesla P40 (24GB VRAM)
2. **Minimizes Cloud Costs**: Reduce dependency on expensive cloud LLM APIs (OpenAI/Anthropic)
3. **Matches Production Architecture**: Stay as close as possible to Kubernetes production deployment
4. **Supports Rapid Iteration**: Enable fast development cycles without complex orchestration overhead
5. **Runs on Unraid 7.2.0**: Integrate seamlessly with existing Unraid server infrastructure

### Hardware Profile

**Dell PowerEdge R730xd Specifications:**
- **CPU**: Dual Intel Xeon E5-2683 v4 @ 2.10GHz (32 physical cores, 64 threads with HT)
- **RAM**: 503.8 GiB (492 GiB available)
- **GPU**: NVIDIA Tesla P40 (24GB VRAM, CUDA 13.0, Driver 580.105.08)
- **Storage**: 144TB array (51TB available), 1.8TB SSD cache
- **Network**: 4× Gigabit NICs bonded to 4Gbps aggregate (bond0)
- **OS**: Unraid 7.2.0 with Docker 27.5.1
- **NUMA**: 2 NUMA nodes (optimal for memory-intensive workloads)

### Current Production Target

- **Platform**: Kubernetes (GKE/EKS) with multi-zone deployment
- **LLM Strategy**: Cloud APIs (OpenAI GPT-4, Anthropic Claude 3)
- **Cost**: $150-700/month for moderate development usage
- **Complexity**: High (requires K8s knowledge, Helm, kubectl, cloud account setup)

## Decision

We will adopt a **Hybrid Docker Compose + Local GPU Inference** approach for Unraid local deployment:

### Architecture Components

1. **Docker Compose Stack**:
   - All OctoLLM services (Orchestrator, Reflex, 6 Arms)
   - Infrastructure (PostgreSQL, Redis, Qdrant)
   - Monitoring (Prometheus, Grafana, Loki)
   - Exporters (node, cAdvisor, postgres, redis, nvidia-dcgm)

2. **Local LLM Inference (Ollama)**:
   - GPU-accelerated inference on Tesla P40
   - Models: Llama 3.1 8B, Mixtral 8×7B, CodeLlama 13B, Nomic Embed Text
   - Replaces OpenAI/Anthropic APIs for 95% of requests
   - Cloud APIs available as fallback for edge cases

3. **Unraid Integration**:
   - App data in `/mnt/user/appdata/octollm/` (standard Unraid location)
   - Permissions: `nobody:users` (99:100) per Unraid convention
   - Restart policy: `unless-stopped` (survives reboots)
   - Custom Docker network: `octollm-net` (172.20.0.0/16)

### Resource Allocation

| Service Category | CPU Cores | RAM | VRAM | Notes |
|------------------|-----------|-----|------|-------|
| PostgreSQL | 4 | 4GB | - | Global memory, task history |
| Redis | 2 | 2GB | - | Caching, pub/sub |
| Qdrant | 4 | 4GB | - | Vector embeddings |
| Orchestrator | 4 | 4GB | - | Main coordinator |
| Reflex Layer | 4 | 2GB | - | Fast preprocessing |
| 6 Arms | 2 each | 2GB each | - | 12 cores, 12GB total |
| Ollama | 8 | 16GB | 24GB | GPU-accelerated LLM |
| Monitoring | 4 | 4GB | - | Prometheus, Grafana, Loki |
| **Total Allocated** | **38** | **48GB** | **24GB** | |
| **Available Remaining** | **26** | **450GB** | **0GB** | For other Unraid services |

**Utilization**: 59% CPU, 9.5% RAM, 100% GPU during inference

### Port Mapping

```
Core Services:
  3000  - Orchestrator API (main entry point)
  3001  - Reflex Layer API

Infrastructure:
  3010  - PostgreSQL
  3011  - Redis
  3012  - Qdrant HTTP API
  3013  - Qdrant gRPC API
  3014  - Ollama API

Arms:
  6001  - Planner Arm
  6002  - Executor Arm
  6003  - Retriever Arm
  6004  - Coder Arm
  6005  - Judge Arm
  6006  - Safety Guardian Arm

Monitoring:
  3030  - Grafana UI
  3100  - Loki (logs)
  8080  - cAdvisor
  9090  - Prometheus
  9100  - Node Exporter
  9121  - Redis Exporter
  9187  - PostgreSQL Exporter
  9400  - NVIDIA DCGM Exporter
```

### Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Orchestrator | Python 3.11, FastAPI | Matches production, easy debugging |
| Reflex Layer | Rust, Axum | Performance-critical, optional initially |
| Arms | Python (AI) / Rust (security) | Flexibility vs. safety trade-off |
| LLM Inference | Ollama 0.1.x | GPU-optimized, simple API, model management |
| Database | PostgreSQL 15 | Production parity, robust |
| Cache | Redis 7 | Production parity, pub/sub support |
| Vectors | Qdrant 1.7.4 | Best-in-class vector DB |
| Monitoring | Prometheus + Grafana | Industry standard, rich ecosystem |

## Alternatives Considered

### Option 1: Pure Docker Compose (No GPU)

**Approach**: Docker Compose with all services, use cloud LLM APIs exclusively.

**Pros**:
- Simplest setup (no GPU drivers needed)
- Proven Docker Compose workflow
- Works on any hardware

**Cons**:
- **Cost**: $150-700/month in LLM API fees
- Wastes available Tesla P40 GPU
- Slower iteration (network latency to cloud APIs)
- API rate limits during development

**Verdict**: ❌ Rejected - Unnecessarily expensive, doesn't leverage available hardware

### Option 2: K3s Virtual Machines (Lightweight Kubernetes)

**Approach**: Run k3s (lightweight K8s) in Unraid VMs, deploy with Helm charts.

**Pros**:
- **Production parity**: Near-identical to GKE/EKS deployment
- Kubernetes experience for team
- Could run multiple isolated environments
- GPU passthrough to VMs possible

**Cons**:
- **Complexity overkill**: Too heavy for single-developer local setup
- VM overhead (need 32GB+ RAM per VM for reasonable performance)
- Slower iteration (rebuild/deploy cycles)
- Requires Kubernetes expertise
- More failure points (VM networking, k3s networking, pod networking)
- Harder to debug (kubectl exec, logs aggregation)

**Verdict**: ⚠️ Deferred - Can add later for production testing, overkill for initial dev

### Option 3: Hybrid Docker Compose + Local GPU (CHOSEN)

**Approach**: Docker Compose for services, Ollama for local GPU-accelerated LLM inference.

**Pros**:
- **Cost savings**: ~$0/month (electricity only vs. $150-700/month cloud APIs)
- **Fast iteration**: `docker-compose up/down` in seconds
- **Leverages GPU**: Tesla P40 runs Llama 3 70B, Mixtral 8×7B, CodeLlama 34B
- **Unraid-native**: Uses standard Unraid Docker patterns
- **Production-similar**: Services identical, only orchestration differs
- **Debuggable**: Direct `docker logs`, `docker exec` access
- **Flexible**: Can still use cloud APIs as fallback

**Cons**:
- Not 100% production-identical (Docker Compose vs. Kubernetes)
- Manual service management (no K8s auto-scaling, self-healing)
- Single-host limitations (no multi-node scheduling)

**Mitigation**:
- Services are containerized identically (Dockerfiles work in both)
- Can add k3s VMs later for Kubernetes testing
- Production deployment guide shows migration path

**Verdict**: ✅ **CHOSEN** - Best balance of cost, performance, and developer experience

### Option 4: Docker Swarm

**Approach**: Docker Swarm for orchestration instead of Kubernetes.

**Pros**:
- Native Docker clustering
- Simpler than Kubernetes
- Built into Docker Engine

**Cons**:
- **Production divergence**: No one uses Swarm in production anymore
- Limited ecosystem compared to K8s
- Harder migration path to GKE/EKS
- Less learning value for team

**Verdict**: ❌ Rejected - Dead-end technology, no production alignment

## Consequences

### Positive

1. **Dramatic Cost Reduction**:
   - **Before**: $150-700/month in LLM API costs
   - **After**: ~$0/month (only electricity: ~$50/month for full server)
   - **Annual Savings**: $1,800-8,400

2. **Faster Development Iteration**:
   - Local inference: 2-10s latency (GPU-bound)
   - Cloud API: 5-30s latency (network + queue + inference)
   - No rate limits or quota concerns

3. **Full Hardware Utilization**:
   - Tesla P40 GPU: 100% utilized during inference
   - 64 CPU threads: 38 allocated (59%), 26 available for other services
   - 504GB RAM: 48GB allocated (9.5%), 450GB available
   - Efficient use of enterprise hardware

4. **Production-Ready Learning Path**:
   - Docker Compose → Docker images → Kubernetes deployment
   - Same service code, only orchestration changes
   - Team learns containerization first, orchestration second

5. **Unraid Ecosystem Integration**:
   - Appears in Unraid Docker tab
   - Uses standard appdata paths
   - Works with existing backup strategies
   - Compatible with Unraid Community Applications

6. **Offline Development**:
   - No internet required after initial setup
   - Works during cloud API outages
   - Data privacy (no external API calls)

### Negative

1. **Production Divergence**:
   - **Docker Compose** vs. **Kubernetes** orchestration
   - Manual scaling vs. HorizontalPodAutoscaler
   - Docker networks vs. K8s Services/Ingress
   - **Mitigation**: Identical Docker images, migration guide provided

2. **Single-Host Limitations**:
   - No multi-node redundancy
   - No automatic failover
   - **Mitigation**: Acceptable for development, not for production

3. **GPU Contention**:
   - Only one GPU, shared by all arms
   - Ollama queues requests (max 4 parallel)
   - **Mitigation**: Still faster than cloud APIs, acceptable for dev

4. **Model Management Overhead**:
   - Need to pull/update models manually
   - 50-100GB model storage required
   - **Mitigation**: Setup script automates initial pull

5. **Learning Curve for Ollama**:
   - Team needs to understand local LLM deployment
   - Different prompt engineering vs. cloud APIs
   - **Mitigation**: Documentation provided, cloud APIs available as fallback

### Migration Path to Production

When ready for cloud deployment:

1. **Phase 1: Same Images, Different Orchestration**
   - Use same Docker images from local development
   - Deploy to Kubernetes (GKE/EKS) with Helm charts
   - Switch from Ollama to OpenAI/Anthropic APIs

2. **Phase 2: Cloud Infrastructure**
   - Replace PostgreSQL with Cloud SQL
   - Replace Redis with Memorystore
   - Replace Qdrant self-hosted with Qdrant Cloud

3. **Phase 3: Production Hardening**
   - Add Ingress with TLS (cert-manager)
   - Configure HorizontalPodAutoscaler
   - Set up multi-region redundancy
   - Implement GitOps (ArgoCD/Flux)

**Estimated Migration Time**: 2-3 days for experienced team

## Implementation Plan

### Phase 1: Infrastructure Setup (Week 1)

- [x] Create `infrastructure/unraid/` directory structure
- [x] Write `docker-compose.unraid.yml` (300-500 lines)
- [x] Write `.env.unraid.example` (100 lines)
- [x] Create `setup-unraid.sh` automated setup script (200-300 lines)
- [x] Configure Prometheus with Unraid-specific metrics
- [x] Create Grafana dashboard for Dell PowerEdge R730xd
- [x] Write test suite (`tests/*.sh`)

### Phase 2: Documentation (Week 1-2)

- [x] Write ADR-007 (this document)
- [ ] Write comprehensive Unraid deployment guide (5,000 lines)
- [ ] Document Ollama model management
- [ ] Create troubleshooting playbook
- [ ] Write migration guide (Unraid → GKE)

### Phase 3: Service Implementation (Week 2-4)

- [ ] Implement Orchestrator (Python FastAPI)
- [ ] Implement Reflex Layer (Rust Axum) - optional
- [ ] Implement 6 Arms (Planner, Executor, Retriever, Coder, Judge, Safety Guardian)
- [ ] Add Prometheus metrics to all services
- [ ] Integrate Ollama API calls

### Phase 4: Testing & Validation (Week 4)

- [ ] Run full test suite
- [ ] Performance benchmarking (latency, throughput)
- [ ] Cost analysis (local vs. cloud)
- [ ] Load testing with multiple concurrent requests
- [ ] GPU utilization optimization

## Metrics for Success

| Metric | Target | Measurement |
|--------|--------|-------------|
| Monthly LLM API Cost | < $50 | OpenAI/Anthropic billing |
| Local Inference Latency (P95) | < 10s | Prometheus metrics |
| GPU Utilization | > 60% | nvidia-smi, DCGM exporter |
| Service Uptime | > 99% | Prometheus `up` metric |
| Setup Time (Fresh Install) | < 30 min | Setup script execution time |
| Developer Satisfaction | > 4/5 | Team survey |

## Risks and Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| GPU thermal throttling | Medium | High | Alert at 80°C, fans at 100%, monitor with DCGM |
| Model inference OOM | Low | Medium | Queue requests, limit parallel inference |
| Docker storage exhaustion | Low | High | Monitor disk usage, prune images, 200GB reserved |
| Network port conflicts | Medium | Low | Use non-standard ports, document in setup |
| Unraid kernel panics | Low | High | Regular backups, test on spare hardware first |
| Team resistance to local LLM | Low | Medium | Provide cloud API fallback, document benefits |

## References

- [OctoLLM Architecture](../../ref-docs/OctoLLM-Architecture-Implementation.md)
- [Docker Compose Best Practices](https://docs.docker.com/compose/production/)
- [Ollama Documentation](https://github.com/ollama/ollama)
- [NVIDIA Tesla P40 Specifications](https://www.nvidia.com/en-us/data-center/tesla-p40/)
- [Unraid Docker Documentation](https://wiki.unraid.net/Docker_Management)
- [Prometheus Exporters](https://prometheus.io/docs/instrumenting/exporters/)

## Approval

- [ ] Architecture Lead: ___________________  Date: __________
- [ ] DevOps Lead: ___________________  Date: __________
- [ ] Security Lead: ___________________  Date: __________

## Changelog

- **2025-11-12**: Initial proposal - Hybrid Docker Compose + Local GPU approach
