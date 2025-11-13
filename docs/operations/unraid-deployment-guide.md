# OctoLLM Unraid Deployment Guide

Complete guide for deploying OctoLLM on Unraid 7.2.0 with Dell PowerEdge R730xd hardware.

## Table of Contents

1. [Introduction](#introduction)
2. [Prerequisites](#prerequisites)
3. [Hardware Requirements](#hardware-requirements)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [GPU Setup](#gpu-setup)
7. [Managing Services](#managing-services)
8. [Accessing Services](#accessing-services)
9. [Local LLM Usage](#local-llm-usage)
10. [Troubleshooting](#troubleshooting)
11. [Backup & Restore](#backup--restore)
12. [Performance Tuning](#performance-tuning)
13. [Monitoring](#monitoring)
14. [Security](#security)
15. [Migration to Cloud](#migration-to-cloud)

---

## Introduction

OctoLLM is a distributed AI architecture inspired by octopus neurobiology. This guide covers local deployment on Unraid, optimized for development with GPU-accelerated LLM inference.

### Why Unraid?

- **Native Docker Support**: Excellent Docker management UI
- **Hardware Flexibility**: Mix and match drives, use cache effectively
- **GPU Passthrough**: Strong support for NVIDIA GPUs
- **Community**: Large community with extensive documentation

### Deployment Architecture

```
┌───────────────────────────────────────────────────────────┐
│                    Unraid Host (bond0)                    │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         Docker Bridge: octollm-net (172.20.0.0/16)  │  │
│  │                                                     │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │  │
│  │  │  Reflex  │  │Orchestr. │  │  6 Arms          │   │  │
│  │  │  Layer   │  │          │  │  (Planner,       │   │  │
│  │  │  (Rust)  │  │ (Python) │  │   Executor,      │   │  │
│  │  │          │  │          │  │   Retriever,     │   │  │
│  │  │  :3001   │  │  :3000   │  │   Coder,         │   │  │
│  │  │          │  │          │  │   Judge,         │   │  │
│  │  │          │  │          │  │   Guardian)      │   │  │
│  │  │          │  │          │  │  :6001-6006      │   │  │
│  │  └────┬─────┘  └────┬─────┘  └────────┬─────────┘   │  │
│  │       │             │                 │             │  │
│  │       └─────────────┴─────────────────┘             │  │
│  │                     │                               │  │
│  │  ┌──────────────────┴──────────────────────┐        │  │
│  │  │                                         │        │  │
│  │  ▼                                         ▼        │  │
│  │  ┌──────────┐  ┌──────┐  ┌──────┐  ┌──────────┐     │  │
│  │  │PostgreSQL│  │Redis │  │Qdrant│  │  Ollama  │     │  │
│  │  │  15      │  │  7   │  │ 1.7.4│  │ (Models) │     │  │
│  │  │  :3010   │  │:3011 │  │:3012 │  │  :3014   │     │  │
│  │  └──────────┘  └──────┘  └──────┘  └──────┬───┘     │  │
│  │                                           │         │  │
│  │  ┌──────────────────────────────────────┐ │         │  │
│  │  │       Monitoring Stack               │ │         │  │
│  │  │  ┌──────────┐  ┌────────┐ ┌──────┐   │ │         │  │
│  │  │  │Prometheus│  │Grafana │ │ Loki │   │ │         │  │
│  │  │  │  :9090   │  │ :3030  │ │:3100 │   │ │         │  │
│  │  │  └──────────┘  └────────┘ └──────┘   │ │         │  │
│  │  └──────────────────────────────────────┘ │         │  │
│  └───────────────────────────────────────────┼─────────┘  │
│                                              │            │
│                                         ┌────▼──────┐     │
│                                         │ Tesla P40 │     │
│                                         │  24GB     │     │
│                                         │  VRAM     │     │
│                                         └───────────┘     │
└───────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### Software Requirements

| Software | Minimum Version | Recommended | Purpose |
|----------|----------------|-------------|---------|
| Unraid | 7.0.0 | 7.2.0+ | Host OS |
| Docker | 20.10 | 27.5.1+ | Container runtime |
| Docker Compose | 1.29 | 2.40.3+ (V2) | Orchestration |
| NVIDIA Driver | 510+ | 580.105.08+ | GPU support |

### Unraid Plugins Required

Install from Community Applications:

1. **NVIDIA Driver** (for GPU support)
   - Search: "nvidia driver"
   - Install: "nvidia-driver" by ich777
   - Reboot after installation

2. **Compose Manager** (optional, for UI management)
   - Search: "compose manager"
   - Install: "compose.manager" by dcflachs

3. **NerdTools** (optional, for additional utilities)
   - Useful for jq, git, and other tools

### User Account Setup

Create Unraid user account with access to:
- Docker management
- Console/SSH access
- Appdata shares

---

## Hardware Requirements

### Minimum Configuration

| Component | Minimum | Recommended | Notes |
|-----------|---------|-------------|-------|
| CPU | 4 cores | 8+ cores | More cores = better parallelism |
| RAM | 16GB | 64GB+ | More RAM = larger models |
| Storage | 50GB free | 200GB+ free | Models are large (5-50GB each) |
| GPU | None | NVIDIA Tesla P40 | Optional but highly recommended |
| Network | 100Mbps | 1Gbps+ | For model downloads |

### Recommended: Dell PowerEdge R730xd

This guide is optimized for:

```
CPU:     Dual Intel Xeon E5-2683 v4 @ 2.10GHz
         - 32 physical cores (64 threads with HT)
         - 2 NUMA nodes
         - 40MB L3 cache

RAM:     503.8 GiB DDR4 ECC
         - 16× 32GB DIMMs
         - 2400 MHz
         - Error-correcting for reliability

GPU:     NVIDIA Tesla P40
         - 24GB GDDR5 VRAM
         - 3840 CUDA cores
         - 250W TDP
         - CUDA 13.0 support

Storage: 144TB array (10 disks)
         - 1.8TB SSD cache (btrfs)
         - 128GB Docker vDisk

Network: 4× Intel I350 Gigabit NICs
         - Bonded to 4Gbps aggregate (bond0)
         - LACP mode 4
```

### GPU Compatibility

**Supported GPUs** (tested):
- NVIDIA Tesla P40 (24GB) ✅
- NVIDIA Tesla P100 (16GB) ✅
- NVIDIA Tesla V100 (32GB) ✅
- NVIDIA RTX 3090 (24GB) ✅
- NVIDIA RTX 4090 (24GB) ✅

**Minimum VRAM for models**:
- Small models (7-13B): 8GB VRAM
- Medium models (30-70B): 24GB VRAM
- Large models (70B+): 48GB+ VRAM or multi-GPU

---

## Installation

### Step 1: Install NVIDIA Driver Plugin

1. Open Unraid WebUI: http://tower.local (or your server IP)
2. Navigate to **Apps** tab
3. Search for "nvidia driver"
4. Click **Install** on "nvidia-driver" by ich777
5. Wait for installation to complete
6. **Reboot server**
7. After reboot, verify:

```bash
# SSH to Unraid
ssh root@tower.local

# Test NVIDIA driver
nvidia-smi
```

**Expected Output**:
```
+-----------------------------------------------------------------------------+
| NVIDIA-SMI 580.105.08     Driver Version: 580.105.08   CUDA Version: 13.0 |
|-------------------------------+----------------------+----------------------+
| GPU  Name        Persistence-M| Bus-Id        Disp.A | Volatile Uncorr. ECC |
| Fan  Temp  Perf  Pwr:Usage/Cap|         Memory-Usage | GPU-Util  Compute M. |
|===============================+======================+======================|
|   0  Tesla P40           Off  | 00000000:03:00.0 Off |                    0 |
| N/A   30C    P0    49W / 250W |      0MiB / 24576MiB |      0%      Default |
+-------------------------------+----------------------+----------------------+
```

### Step 2: Clone Repository

```bash
# SSH to Unraid
ssh root@tower.local

# Navigate to appdata
cd /mnt/user/appdata

# Clone OctoLLM repository
git clone https://github.com/your-org/octollm.git
cd octollm
```

### Step 3: Run Setup Script

The automated setup script will:
- Create directory structure
- Generate secure passwords
- Configure environment files
- Download Ollama models
- Initialize databases
- Start all services

```bash
cd /mnt/user/appdata/octollm/infrastructure/unraid

# Make script executable (if needed)
chmod +x setup-unraid.sh

# Run setup
bash setup-unraid.sh
```

**Setup Process**:
```
[INFO] Checking prerequisites...
[SUCCESS] Docker is installed: Docker version 27.5.1
[SUCCESS] Docker Compose V2 is installed: 2.40.3
[SUCCESS] NVIDIA driver is installed: 580.105.08
[SUCCESS] Detected GPU: Tesla P40 with 24576 MiB VRAM

[INFO] Creating directory structure in /mnt/user/appdata/octollm/...
[SUCCESS] Created directory: /mnt/user/appdata/octollm/postgres/data
[SUCCESS] Created directory: /mnt/user/appdata/octollm/redis/data
...

[INFO] Setting up environment configuration...
[SUCCESS] Environment file created: .env.unraid
[INFO] Secure passwords generated. Save these credentials:
PostgreSQL Password: xK9fL2mN8vP4qR7sT1wU6yZ3aB5cD0eF
Redis Password: gH4jK1lM7nP9qR2sT8vW5xY0zA3bC6dE
Qdrant API Key: fG1hI4jK7lM0nP3qR6sT9uV2wX5yZ8aB
Grafana Admin Password: cD0eF3gH6iJ9kL2mN5oP8qR1sT4uV7wX

[INFO] Creating PostgreSQL initialization script...
[SUCCESS] PostgreSQL initialization script created

[INFO] Setting up GPU and downloading Ollama models...
[WARNING] This may take 15-30 minutes depending on your internet speed.
[INFO] Pulling model: llama3.1:8b
[SUCCESS] Model llama3.1:8b downloaded successfully
...

[INFO] Starting OctoLLM services...
[SUCCESS] OctoLLM services started successfully

============================================================================
[SUCCESS] OctoLLM Unraid Setup Complete!
============================================================================

Access URLs:
  Orchestrator API:    http://192.168.4.6:3000
  Orchestrator Docs:   http://192.168.4.6:3000/docs
  Reflex Layer API:    http://192.168.4.6:3001
  Grafana Dashboard:   http://192.168.4.6:3030
  Prometheus:          http://192.168.4.6:9090
  Ollama API:          http://192.168.4.6:3014

Credentials:
  Grafana:
    Username: admin
    Password: cD0eF3gH6iJ9kL2mN5oP8qR1sT4uV7wX
```

### Step 4: Verify Installation

Run test suite:

```bash
# Test prerequisites
bash tests/test-prerequisites.sh

# Test GPU access
bash tests/test-gpu.sh

# Test Ollama inference
bash tests/test-ollama.sh

# Test service health (wait 2-3 minutes after startup)
bash tests/test-services.sh
```

**All tests should pass**:
```
============================================================================
OctoLLM Service Health Test
============================================================================

[PASS] orchestrator is healthy
[PASS] reflex-layer is healthy
[PASS] planner-arm is healthy
...

============================================================================
Summary: 11 passed, 0 failed
============================================================================
[SUCCESS] All services are healthy!
```

---

## Configuration

### Environment Variables

Edit `/mnt/user/appdata/octollm/infrastructure/unraid/.env.unraid`:

```bash
# Network Configuration
HOST_IP=192.168.4.6                    # Change to your Unraid server IP

# Database Credentials (auto-generated by setup)
POSTGRES_DB=octollm
POSTGRES_USER=octollm
POSTGRES_PASSWORD=xK9fL2mN8vP4qR7sT1wU6yZ3aB5cD0eF
REDIS_PASSWORD=gH4jK1lM7nP9qR2sT8vW5xY0zA3bC6dE
QDRANT_API_KEY=fG1hI4jK7lM0nP3qR6sT9uV2wX5yZ8aB

# Local LLM Configuration
PREFER_LOCAL_LLM=true                  # Use GPU-accelerated local inference
OLLAMA_PRIMARY_MODEL=llama3.1:8b       # Fast general-purpose model
OLLAMA_FALLBACK_MODEL=mixtral:8x7b     # Advanced reasoning model
OLLAMA_NUM_PARALLEL=4                  # Concurrent requests (GPU memory limited)

# Cloud LLM APIs (optional fallback)
OPENAI_API_KEY=                        # Leave empty to skip
ANTHROPIC_API_KEY=                     # Leave empty to skip

# Performance Tuning
MAX_PARALLEL_ARMS=5                    # Max concurrent arm executions
TASK_TIMEOUT=300                       # Task timeout in seconds
CACHE_TTL=3600                         # Cache time-to-live in seconds

# Monitoring
LOG_LEVEL=INFO                         # DEBUG, INFO, WARNING, ERROR
GRAFANA_ADMIN_PASSWORD=cD0eF3gH6iJ9kL2mN5oP8qR1sT4uV7wX
```

### Port Customization

If ports conflict with existing services, edit `docker-compose.unraid.yml`:

```yaml
services:
  orchestrator:
    ports:
      - "8000:8000"  # Change 3000 → 8000 if needed

  grafana:
    ports:
      - "3050:3000"  # Change 3030 → 3050 if needed
```

**After changes, restart services**:
```bash
docker-compose down
docker-compose up -d
```

---

## GPU Setup

### Installing NVIDIA Driver

**Method 1: Unraid Plugin (Recommended)**

1. Apps → Search "nvidia driver"
2. Install "nvidia-driver" by ich777
3. Reboot
4. Verify: `nvidia-smi`

**Method 2: Manual Installation**

```bash
# Download driver
cd /tmp
wget https://us.download.nvidia.com/XFree86/Linux-x86_64/580.105.08/NVIDIA-Linux-x86_64-580.105.08.run

# Install
chmod +x NVIDIA-Linux-x86_64-580.105.08.run
./NVIDIA-Linux-x86_64-580.105.08.run --no-questions --ui=none

# Reboot
reboot
```

### Configuring Docker NVIDIA Runtime

Edit `/etc/docker/daemon.json`:

```json
{
  "runtimes": {
    "nvidia": {
      "path": "nvidia-container-runtime",
      "runtimeArgs": []
    }
  },
  "default-runtime": "nvidia"
}
```

Restart Docker:
```bash
/etc/rc.d/rc.docker restart
```

### Testing GPU Access

```bash
# Test from host
nvidia-smi

# Test from Docker
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi
```

### GPU Monitoring

**Real-time monitoring**:
```bash
# Simple watch
nvidia-smi -l 1

# Detailed with scripts/monitor-resources.sh
cd /mnt/user/appdata/octollm/infrastructure/unraid
bash scripts/monitor-resources.sh
```

**Grafana dashboard**:
- Navigate to http://192.168.4.6:3030
- Login with admin / [password from .env.unraid]
- Dashboard: "OctoLLM Unraid Dashboard"
- GPU section shows:
  - Utilization %
  - Temperature
  - Memory usage
  - Power consumption

---

## Managing Services

### Docker Compose Commands

**Navigate to compose directory first**:
```bash
cd /mnt/user/appdata/octollm/infrastructure/unraid
```

**Start all services**:
```bash
docker-compose up -d
```

**Stop all services**:
```bash
docker-compose stop
```

**Restart all services**:
```bash
docker-compose restart
```

**Stop and remove containers**:
```bash
docker-compose down
```

**View status**:
```bash
docker-compose ps
```

**View logs**:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f orchestrator

# Last 100 lines
docker-compose logs --tail=100 orchestrator
```

### Individual Service Management

**Restart single service**:
```bash
docker-compose restart orchestrator
```

**Rebuild single service**:
```bash
docker-compose build orchestrator
docker-compose up -d orchestrator
```

**Scale arms** (if needed):
```bash
docker-compose up -d --scale planner-arm=2
```

### Unraid Docker UI

Services also appear in Unraid Docker tab:
- Click container name to view logs
- Click "Console" for shell access
- Click "Edit" to modify settings
- Use "Autostart" to start on boot

---

## Accessing Services

### Web Interfaces

| Service | URL | Credentials |
|---------|-----|-------------|
| Grafana | http://192.168.4.6:3030 | admin / [.env.unraid] |
| Prometheus | http://192.168.4.6:9090 | None |
| Orchestrator Docs | http://192.168.4.6:3000/docs | None |
| cAdvisor | http://192.168.4.6:8080 | None |

### API Endpoints

**Orchestrator (Main API)**:
```bash
# Health check
curl http://192.168.4.6:3000/health

# API documentation
open http://192.168.4.6:3000/docs

# Submit task
curl -X POST http://192.168.4.6:3000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{
    "goal": "Explain quantum computing in simple terms",
    "constraints": {"max_tokens": 500}
  }'

# Get task status
curl http://192.168.4.6:3000/api/v1/tasks/abc123
```

**Ollama (Local LLM)**:
```bash
# List models
curl http://192.168.4.6:3014/api/tags

# Generate completion
curl http://192.168.4.6:3014/api/generate -d '{
  "model": "llama3.1:8b",
  "prompt": "Why is the sky blue?",
  "stream": false
}'

# Chat completion
curl http://192.168.4.6:3014/api/chat -d '{
  "model": "llama3.1:8b",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ]
}'
```

**Prometheus (Metrics)**:
```bash
# Query API
curl 'http://192.168.4.6:9090/api/v1/query?query=up'

# GPU metrics
curl 'http://192.168.4.6:9090/api/v1/query?query=DCGM_FI_DEV_GPU_UTIL'
```

---

## Local LLM Usage

### Ollama Model Management

**List installed models**:
```bash
docker exec octollm-ollama ollama list
```

**Pull new model**:
```bash
# Small model (< 10GB)
docker exec octollm-ollama ollama pull llama3:8b

# Medium model (< 30GB)
docker exec octollm-ollama ollama pull mixtral:8x7b

# Large model (requires 48GB+ VRAM or multi-GPU)
docker exec octollm-ollama ollama pull llama3:70b

# Specialized models
docker exec octollm-ollama ollama pull codellama:13b    # Code generation
docker exec octollm-ollama ollama pull nomic-embed-text # Embeddings
docker exec octollm-ollama ollama pull llama3-vision    # Image understanding
```

**Remove model**:
```bash
docker exec octollm-ollama ollama rm llama3:70b
```

**Model disk usage**:
```bash
du -sh /mnt/user/appdata/octollm/ollama/models
```

### Recommended Models by Use Case

| Use Case | Model | VRAM | Speed | Quality |
|----------|-------|------|-------|---------|
| **General Chat** | llama3.1:8b | 8GB | Fast | Good |
| **Advanced Reasoning** | mixtral:8x7b | 24GB | Medium | Excellent |
| **Code Generation** | codellama:13b | 13GB | Medium | Excellent |
| **Code Completion** | codellama:7b | 7GB | Fast | Good |
| **Embeddings** | nomic-embed-text | 1GB | Very Fast | Excellent |
| **Long Context** | llama3-longcontext:70b | 48GB | Slow | Excellent |

### Performance Tuning

**Concurrent requests**:
```bash
# .env.unraid
OLLAMA_NUM_PARALLEL=4  # Reduce if OOM errors, increase if underutilized
```

**Model keep-alive**:
```bash
# .env.unraid
OLLAMA_KEEP_ALIVE=5m   # How long to keep model in VRAM
```

**Max loaded models**:
```bash
# .env.unraid
OLLAMA_MAX_LOADED_MODELS=3  # Max models in VRAM simultaneously
```

### Switching Between Local and Cloud

**Use local LLM** (default, cost-free):
```bash
# .env.unraid
PREFER_LOCAL_LLM=true
```

**Use cloud APIs** (when local unavailable):
```bash
# .env.unraid
PREFER_LOCAL_LLM=false
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Automatic fallback** (best of both worlds):
```bash
# .env.unraid
PREFER_LOCAL_LLM=true
OPENAI_API_KEY=sk-proj-...  # Used only if local fails
```

---

## Troubleshooting

### Common Issues

#### 1. Services Won't Start

**Symptom**: `docker-compose up -d` fails or services crash immediately.

**Check logs**:
```bash
docker-compose logs orchestrator
```

**Common causes**:
- Port conflicts
- Insufficient resources
- Missing environment variables

**Solutions**:
```bash
# Check port availability
ss -tuln | grep -E ':(3000|3001|6001|9090)'

# Check Docker resources
docker info | grep -E "CPUs|Total Memory"

# Verify .env.unraid exists
ls -la .env.unraid

# Recreate from scratch
docker-compose down -v
bash setup-unraid.sh
```

#### 2. GPU Not Detected

**Symptom**: `nvidia-smi: command not found` or Ollama not using GPU.

**Diagnose**:
```bash
# Test NVIDIA driver
nvidia-smi

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

# Check Ollama logs
docker logs octollm-ollama | grep -i gpu
```

**Solutions**:
```bash
# Reinstall NVIDIA driver plugin
# Apps → nvidia-driver → Force Update
# Reboot server

# Check Docker NVIDIA runtime
cat /etc/docker/daemon.json
# Should have "nvidia" runtime configured

# Restart Ollama with GPU
docker-compose restart ollama
```

#### 3. Out of Memory Errors

**Symptom**: Containers killed with OOM, logs show memory errors.

**Check memory usage**:
```bash
free -h
docker stats --no-stream
```

**Solutions**:
```bash
# Reduce concurrent requests
# Edit .env.unraid:
OLLAMA_NUM_PARALLEL=2
MAX_PARALLEL_ARMS=3

# Increase container memory limits
# Edit docker-compose.unraid.yml:
services:
  ollama:
    deploy:
      resources:
        limits:
          memory: 24G  # Increase from 16G

# Use smaller models
docker exec octollm-ollama ollama pull llama3:8b
# Instead of mixtral:8x7b
```

#### 4. Slow Inference

**Symptom**: LLM responses take > 30 seconds.

**Check GPU usage**:
```bash
nvidia-smi -l 1
```

**If GPU usage is low**:
- Model not loaded properly
- CPU inference fallback
- Queue backlog

**Solutions**:
```bash
# Force model load
docker exec octollm-ollama ollama run llama3.1:8b "Hello"

# Check Ollama logs for errors
docker logs octollm-ollama --tail=100

# Verify GPU passthrough
docker inspect octollm-ollama | grep -A5 DeviceRequests

# Restart Ollama
docker-compose restart ollama
```

**If GPU usage is high (100%)**:
- Normal behavior during inference
- Consider faster model or more GPUs
- Reduce parallel requests

#### 5. Database Connection Errors

**Symptom**: Services can't connect to PostgreSQL/Redis.

**Check database health**:
```bash
docker-compose ps postgres redis
docker logs octollm-postgres --tail=50
docker logs octollm-redis --tail=50
```

**Solutions**:
```bash
# Wait for health checks
docker-compose ps  # Check health status

# Manual health check
docker exec octollm-postgres pg_isready -U octollm
docker exec octollm-redis redis-cli ping

# Restart databases
docker-compose restart postgres redis

# Check network connectivity
docker exec octollm-orchestrator ping postgres
docker exec octollm-orchestrator ping redis
```

#### 6. Port Conflicts

**Symptom**: "bind: address already in use"

**Find conflicting process**:
```bash
ss -tuln | grep :3000
lsof -i :3000
```

**Solutions**:
```bash
# Stop conflicting service
docker stop conflicting-container
# Or change OctoLLM ports in docker-compose.unraid.yml

# Use alternative ports
# Edit docker-compose.unraid.yml:
services:
  orchestrator:
    ports:
      - "8000:8000"  # Changed from 3000
```

### Logging and Debugging

**Enable debug logging**:
```bash
# Edit .env.unraid
LOG_LEVEL=DEBUG
RUST_LOG=debug
RUST_BACKTRACE=1

# Restart services
docker-compose restart
```

**View aggregated logs**:
```bash
# All services, follow mode
docker-compose logs -f

# Specific time range
docker-compose logs --since="2024-01-15T10:00:00"

# Filter by keyword
docker-compose logs | grep ERROR
```

**Access container shell**:
```bash
# Orchestrator (Python)
docker exec -it octollm-orchestrator bash

# Ollama (check models)
docker exec -it octollm-ollama bash
ls -lh /root/.ollama/models
```

**Check resource usage**:
```bash
# Real-time stats
docker stats

# Per-container stats
docker stats octollm-ollama

# Custom monitoring script
bash scripts/monitor-resources.sh
```

### Getting Help

1. **Check logs first**: `docker-compose logs [service]`
2. **Search GitHub issues**: https://github.com/your-org/octollm/issues
3. **Ask in discussions**: https://github.com/your-org/octollm/discussions
4. **Unraid forum**: https://forums.unraid.net

**When reporting issues, include**:
- Unraid version: `cat /etc/unraid-version`
- Hardware specs: CPU, RAM, GPU
- Docker version: `docker --version`
- Logs: `docker-compose logs [service] --tail=100`
- Config: `.env.unraid` (redact passwords!)

---

## Backup & Restore

### Automated Backup

**Run backup script**:
```bash
cd /mnt/user/appdata/octollm/infrastructure/unraid
bash scripts/backup-data.sh
```

**Output**:
```
Starting OctoLLM backup...
Timestamp: 20250112_143022
Stopping services...
Backing up PostgreSQL...
Backing up data directories...
Backup complete!
  PostgreSQL: 150M
  Data files: 2.5G
  Location: /mnt/user/backups/octollm
Restarting services...
Done!
```

**Backup location**:
```
/mnt/user/backups/octollm/
├── octollm_backup_20250112_143022_postgres.sql
└── octollm_backup_20250112_143022_data.tar.gz
```

### Manual Backup

**PostgreSQL only**:
```bash
docker exec octollm-postgres pg_dumpall -U octollm > backup_$(date +%Y%m%d).sql
```

**Data directories**:
```bash
tar -czf octollm_data_$(date +%Y%m%d).tar.gz \
  -C /mnt/user/appdata \
  --exclude='octollm/ollama/models' \
  octollm/
```

**Ollama models** (optional, large):
```bash
tar -czf octollm_models_$(date +%Y%m%d).tar.gz \
  -C /mnt/user/appdata/octollm/ollama \
  models/
```

### Restore from Backup

**Step 1: Stop services**:
```bash
cd /mnt/user/appdata/octollm/infrastructure/unraid
docker-compose down
```

**Step 2: Restore data directories**:
```bash
cd /mnt/user/appdata
tar -xzf /mnt/user/backups/octollm/octollm_backup_20250112_143022_data.tar.gz
```

**Step 3: Restore PostgreSQL**:
```bash
docker-compose up -d postgres
sleep 10
docker exec -i octollm-postgres psql -U octollm < /mnt/user/backups/octollm/octollm_backup_20250112_143022_postgres.sql
```

**Step 4: Restart all services**:
```bash
docker-compose up -d
```

### Backup Schedule

**Unraid User Scripts plugin** (recommended):

1. Install "User Scripts" plugin from Community Applications
2. Add new script:

```bash
#!/bin/bash
cd /mnt/user/appdata/octollm/infrastructure/unraid
bash scripts/backup-data.sh

# Optional: Keep only last 7 backups
find /mnt/user/backups/octollm -type f -mtime +7 -delete
```

3. Schedule: Daily at 2:00 AM

### Cloud Backup

**Sync to cloud storage**:
```bash
# AWS S3
aws s3 sync /mnt/user/backups/octollm s3://my-bucket/octollm-backups/

# Google Cloud Storage
gsutil -m rsync -r /mnt/user/backups/octollm gs://my-bucket/octollm-backups/

# Rclone (any provider)
rclone sync /mnt/user/backups/octollm remote:octollm-backups/
```

---

## Performance Tuning

### CPU Pinning (NUMA Optimization)

Dell PowerEdge R730xd has 2 NUMA nodes. Pin containers to specific nodes for better performance.

**Check NUMA topology**:
```bash
lscpu | grep NUMA
numactl --hardware
```

**Edit docker-compose.unraid.yml**:
```yaml
services:
  ollama:
    cpuset: "0-15,32-47"  # NUMA node 0
    mem: "0"              # NUMA node 0 memory

  orchestrator:
    cpuset: "16-31,48-63" # NUMA node 1
    mem: "1"              # NUMA node 1 memory
```

### PostgreSQL Tuning

**Create custom config**:
```bash
cat > /mnt/user/appdata/octollm/postgres/postgresql.conf << EOF
# OctoLLM PostgreSQL Performance Tuning

# Memory
shared_buffers = 2GB                  # 25% of dedicated RAM
effective_cache_size = 8GB            # 50% of system RAM
work_mem = 64MB                       # Per query operation
maintenance_work_mem = 512MB          # VACUUM, CREATE INDEX

# Connections
max_connections = 200

# Query Planner
random_page_cost = 1.1               # SSD optimization
effective_io_concurrency = 200       # SSD parallel I/O

# WAL
wal_buffers = 16MB
checkpoint_completion_target = 0.9
max_wal_size = 4GB
min_wal_size = 1GB

# Logging
log_destination = 'stderr'
logging_collector = on
log_directory = 'log'
log_filename = 'postgresql-%Y%m%d.log'
log_line_prefix = '%t [%p]: [%l-1] user=%u,db=%d,app=%a,client=%h '
log_statement = 'none'               # 'all' for debugging
log_duration = off
log_min_duration_statement = 1000    # Log slow queries (> 1s)
EOF
```

**Mount in docker-compose.unraid.yml**:
```yaml
services:
  postgres:
    volumes:
      - /mnt/user/appdata/octollm/postgres/postgresql.conf:/var/lib/postgresql/data/postgresql.conf:ro
    command: postgres -c config_file=/var/lib/postgresql/data/postgresql.conf
```

### Redis Tuning

**Edit .env.unraid**:
```bash
# Redis Configuration
REDIS_MAXMEMORY=4gb
REDIS_MAXMEMORY_POLICY=allkeys-lru

# Persistence (reduce writes for performance)
REDIS_SAVE_SECONDS=900 1            # Save after 15 min if 1+ key changed
REDIS_SAVE_SECONDS_2=300 10         # Save after 5 min if 10+ keys changed
```

### Ollama GPU Performance

**Maximize throughput**:
```bash
# .env.unraid
OLLAMA_NUM_PARALLEL=4              # Max concurrent requests (GPU memory limited)
OLLAMA_KEEP_ALIVE=10m              # Keep models loaded longer
OLLAMA_MAX_LOADED_MODELS=2         # Reduce model swapping
```

**Power limit** (Tesla P40 defaults to 250W):
```bash
# Increase to maximum (if cooling allows)
nvidia-smi -pl 250

# Monitor temperature
nvidia-smi -l 1
# Should stay below 85°C
```

### Network Optimization

**MTU tuning** (for 4Gbps bond):
```bash
# Check current MTU
ip link show bond0

# Increase MTU (if switch supports)
ifconfig bond0 mtu 9000

# Test with jumbo frames
ping -M do -s 8972 192.168.4.6
```

**Docker network tuning**:
```bash
# Edit docker-compose.unraid.yml
networks:
  octollm-net:
    driver: bridge
    driver_opts:
      com.docker.network.driver.mtu: 9000  # Jumbo frames
```

---

## Monitoring

### Grafana Dashboards

**Access Grafana**:
- URL: http://192.168.4.6:3030
- Username: admin
- Password: [from .env.unraid]

**Pre-configured dashboards**:

1. **OctoLLM Unraid Dashboard** (default)
   - System overview (CPU, RAM, disk, network)
   - GPU metrics (utilization, temperature, memory, power)
   - Service health status
   - Database performance
   - Ollama LLM metrics
   - Container resources

2. **Import additional dashboards**:
   - Click "+ → Import"
   - Enter dashboard ID or upload JSON
   - Recommended IDs:
     - 1860: Node Exporter Full
     - 179: Docker Host & Container Overview
     - 12321: NVIDIA DCGM Exporter

### Prometheus Alerts

**View alerts**:
- URL: http://192.168.4.6:9090/alerts

**Alert rules** (from `prometheus/alerts.unraid.yml`):
- High CPU usage (> 80%)
- High memory usage (> 85%)
- Low disk space (< 10%)
- High GPU temperature (> 80°C)
- Service down
- Database connection exhaustion
- High error rate

**Configure alerting** (Slack, email, PagerDuty):

Edit `/mnt/user/appdata/octollm/prometheus/config/prometheus.yml`:
```yaml
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - 'alertmanager:9093'
```

Deploy Alertmanager:
```yaml
# Add to docker-compose.unraid.yml
services:
  alertmanager:
    image: prom/alertmanager:latest
    ports:
      - "9093:9093"
    volumes:
      - ./alertmanager.yml:/etc/alertmanager/alertmanager.yml:ro
```

### Real-Time Monitoring

**Custom monitoring script**:
```bash
bash scripts/monitor-resources.sh
```

**Output**:
```
╔════════════════════════════════════════════════════════════════════════════╗
║  OctoLLM Resource Monitor - tower
║  Uptime: up 5 days, 12 hours
╚════════════════════════════════════════════════════════════════════════════╝

CPU (64 cores): 45.2%
[██████████████████████░░░░░░░░░░░░░░░░░░░░░░░░░░]

RAM (504GB): 125GB / 504GB (24.8%)
[████████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NVIDIA Tesla P40 GPU
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Utilization:  87%
VRAM:         18432MB / 24576MB (75.0%)
Temperature:  72°C
Power:        187W / 250W

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Storage (/mnt/user)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Usage: 93TB / 144TB (64%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Network (bond0 - 4Gbps)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Download: 42 MB/s  |  Upload: 18 MB/s
```

### Logging

**View logs in Grafana** (Loki integration):
- Navigate to Explore
- Select "Loki" datasource
- Query: `{container_name=~"octollm-.*"}`

**Command-line log access**:
```bash
# Real-time logs
docker-compose logs -f orchestrator

# Search logs
docker-compose logs orchestrator | grep ERROR

# Export logs
docker-compose logs --no-color > octollm-logs-$(date +%Y%m%d).txt
```

---

## Security

### Network Isolation

**Firewall rules** (iptables):
```bash
# Allow from local network only
iptables -A INPUT -p tcp -s 192.168.0.0/16 --dport 3000:9999 -j ACCEPT

# Block from internet
iptables -A INPUT -p tcp --dport 3000:9999 -j DROP

# Save rules (Unraid persists in /boot/config/network.cfg)
iptables-save > /boot/config/firewall-rules
```

**Docker network isolation**:
```yaml
# docker-compose.unraid.yml
networks:
  octollm-net:
    driver: bridge
    internal: false  # Set to true to disable internet access
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### VPN Access (Recommended)

**Option 1: Tailscale** (easiest):
```bash
# Install Tailscale on Unraid
curl -fsSL https://tailscale.com/install.sh | sh

# Authenticate
tailscale up

# Access from anywhere
# http://tower.tail-scale.ts.net:3000
```

**Option 2: WireGuard** (manual):
- Install WireGuard plugin from Community Applications
- Configure peer
- Access via VPN tunnel

### Secrets Management

**Never commit these files**:
- `.env.unraid`
- `.env.unraid.backup`
- `backups/*.sql`

**Verify gitignore**:
```bash
cd /mnt/user/appdata/octollm
git status --ignored
# Should NOT list .env.unraid
```

**Rotate passwords regularly**:
```bash
# Regenerate all passwords
cd infrastructure/unraid
bash setup-unraid.sh
# Answer "y" when prompted to overwrite .env.unraid
```

### TLS/SSL (Production)

**Behind reverse proxy** (NGINX Proxy Manager):

1. Install NGINX Proxy Manager from Community Applications
2. Create proxy host:
   - Domain: octollm.yourdomain.com
   - Forward to: 192.168.4.6:3000
   - Enable SSL (Let's Encrypt)
3. Access via: https://octollm.yourdomain.com

**Direct TLS** (advanced):
```bash
# Generate self-signed cert
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout /mnt/user/appdata/octollm/certs/key.pem \
  -out /mnt/user/appdata/octollm/certs/cert.pem \
  -days 365

# Edit .env.unraid
ENABLE_TLS=true
TLS_CERT_PATH=/mnt/user/appdata/octollm/certs/cert.pem
TLS_KEY_PATH=/mnt/user/appdata/octollm/certs/key.pem
```

### Audit Logging

**PostgreSQL audit table** (already created by setup):
```sql
SELECT * FROM audit.api_logs
ORDER BY timestamp DESC
LIMIT 100;
```

**Query audit logs**:
```bash
docker exec -it octollm-postgres psql -U octollm -c "
SELECT
  timestamp,
  endpoint,
  method,
  status_code,
  user_id,
  ip_address
FROM audit.api_logs
WHERE timestamp > NOW() - INTERVAL '1 hour'
ORDER BY timestamp DESC;
"
```

---

## Migration to Cloud

When ready to deploy to production (GKE/EKS):

### Step 1: Export Data

```bash
# Backup all data
cd /mnt/user/appdata/octollm/infrastructure/unraid
bash scripts/backup-data.sh

# Upload to cloud storage
aws s3 cp /mnt/user/backups/octollm/ s3://my-bucket/octollm-migration/ --recursive
```

### Step 2: Update Configuration

**Switch to cloud LLMs**:
```bash
# .env.cloud
PREFER_LOCAL_LLM=false
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
```

**Use managed databases**:
```bash
# .env.cloud
DATABASE_URL=postgresql://user:pass@cloud-sql-instance:5432/octollm
REDIS_URL=redis://redis-memorystore:6379
QDRANT_URL=https://my-cluster.qdrant.io
```

### Step 3: Deploy to Kubernetes

```bash
cd /mnt/user/appdata/octollm/infrastructure/kubernetes

# Apply namespace
kubectl apply -f namespaces/octollm-prod-namespace.yaml

# Deploy with Helm (recommended)
helm install octollm ./charts/octollm \
  --namespace octollm-prod \
  --values ./charts/octollm/values-prod.yaml

# Or apply manifests directly
kubectl apply -k overlays/prod
```

### Step 4: Data Migration

**PostgreSQL**:
```bash
# Restore to Cloud SQL
cat backup_postgres.sql | psql "$DATABASE_URL"
```

**Qdrant vectors**:
```bash
# Use Qdrant snapshot API
curl -X POST http://192.168.4.6:3012/collections/octollm/snapshots
curl -X GET http://192.168.4.6:3012/collections/octollm/snapshots/snapshot_name/download > snapshot.tar

# Upload to Qdrant Cloud
curl -X POST https://my-cluster.qdrant.io/collections/octollm/snapshots/upload \
  -F "snapshot=@snapshot.tar"
```

### Cost Comparison

| Component | Unraid (Monthly) | GKE (Monthly) | Difference |
|-----------|------------------|---------------|------------|
| Compute | $0 (owned) | $200-500 | +$200-500 |
| LLM APIs | $0 (local) | $150-700 | +$150-700 |
| Databases | $0 | $100-300 | +$100-300 |
| Storage | $0 | $20-50 | +$20-50 |
| Networking | $0 | $50-100 | +$50-100 |
| **Total** | **~$50 electricity** | **$520-1,650** | **+$470-1,600/mo** |

**Break-even analysis**:
- Development on Unraid: ~$50/month
- Production on GKE: ~$1,000/month
- **Savings during development**: $950/month × 6 months = $5,700

See full [Cloud Migration Guide](./cloud-migration-from-unraid.md) for detailed steps.

---

## Conclusion

You now have a fully functional OctoLLM deployment on Unraid with:

✅ GPU-accelerated local LLM inference (Tesla P40)
✅ Complete monitoring stack (Prometheus, Grafana, Loki)
✅ Automated backups and health checks
✅ Production-ready architecture
✅ Cost savings: $150-700/month in LLM API fees

### Next Steps

1. **Explore API**: http://192.168.4.6:3000/docs
2. **Monitor with Grafana**: http://192.168.4.6:3030
3. **Submit test tasks**: See API examples above
4. **Optimize performance**: Tune based on your workload
5. **Join community**: https://github.com/your-org/octollm/discussions

### Support

- **Documentation**: https://github.com/your-org/octollm/docs
- **Issues**: https://github.com/your-org/octollm/issues
- **Discord**: https://discord.gg/octollm
- **Email**: support@octollm.io

---

**Last Updated**: 2025-11-12
**Version**: 1.0.0
**Tested On**: Unraid 7.2.0, Dell PowerEdge R730xd, Tesla P40
