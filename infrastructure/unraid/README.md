# OctoLLM Unraid Deployment

Local development deployment of OctoLLM optimized for Dell PowerEdge R730xd running Unraid 7.2.0 with NVIDIA Tesla P40 GPU.

## Quick Start

```bash
# 1. Clone repository
cd /mnt/user/appdata
git clone https://github.com/your-org/octollm.git
cd octollm/infrastructure/unraid

# 2. Run setup script
bash setup-unraid.sh

# 3. Access services
# Orchestrator API: http://192.168.4.6:3000
# Grafana Dashboard: http://192.168.4.6:3030
```

## What's Included

- **Docker Compose Stack**: All OctoLLM services, databases, monitoring
- **GPU Acceleration**: Ollama with Tesla P40 for local LLM inference
- **Monitoring**: Prometheus, Grafana, Loki with custom dashboards
- **Testing Suite**: Automated health checks and validation
- **Documentation**: Comprehensive deployment guide

## Hardware Requirements

**Minimum**:
- Unraid 7.2.0+
- 16GB RAM, 8 CPU cores
- 50GB free disk space
- NVIDIA GPU (optional, but highly recommended)

**Recommended** (Dell PowerEdge R730xd):
- 64GB+ RAM, 16+ CPU cores
- 200GB free disk space
- NVIDIA Tesla P40 (24GB VRAM)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Unraid Host (192.168.4.6)               │
│  ┌────────────────────────────────────────────────────────┐ │
│  │            Docker Network: octollm-net                 │ │
│  │                 (172.20.0.0/16)                        │ │
│  │                                                        │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐   │ │
│  │  │ Orchestrator │──│ Reflex Layer │  │ 6× Arms     │   │ │
│  │  │   :3000      │  │    :3001     │  │ :6001-6006  │   │ │
│  │  └──────────────┘  └──────────────┘  └─────────────┘   │ │
│  │          │                 │                 │         │ │
│  │  ┌───────┴─────────────────┴─────────────────┘         │ │
│  │  │                                                     │ │
│  │  ▼                                                     │ │
│  │  ┌──────────┐  ┌──────┐  ┌────────┐  ┌────────────┐    │ │
│  │  │PostgreSQL│  │Redis │  │ Qdrant │  │   Ollama   │    │ │
│  │  │  :3010   │  │:3011 │  │ :3012  │  │   :3014    │    │ │
│  │  └──────────┘  └──────┘  └────────┘  └─────┬──────┘    │ │
│  │                                            │           │ │
│  │  ┌────────────────┐  ┌──────────────┐      │           │ │
│  │  │   Prometheus   │  │   Grafana    │      │           │ │
│  │  │     :9090      │  │    :3030     │      │           │ │
│  │  └────────────────┘  └──────────────┘      │           │ │
│  └────────────────────────────────────────────┼───────────┘ │
│                                                 │           │
│                                           ┌─────▼─────┐     │
│                                           │ Tesla P40 │     │
│                                           │  24GB RAM │     │
│                                           └───────────┘     │
└─────────────────────────────────────────────────────────────┘
```

## Resource Allocation

| Component | CPU | RAM | VRAM | Purpose |
|-----------|-----|-----|------|---------|
| PostgreSQL | 4 | 4GB | - | Global memory, task history |
| Redis | 2 | 2GB | - | Caching, pub/sub |
| Qdrant | 4 | 4GB | - | Vector embeddings |
| Orchestrator | 4 | 4GB | - | Main coordinator |
| Reflex Layer | 4 | 2GB | - | Fast preprocessing |
| 6 Arms | 2 ea | 2GB ea | - | Specialized capabilities |
| Ollama | 8 | 16GB | 24GB | Local LLM inference |
| Monitoring | 4 | 4GB | - | Prometheus, Grafana, Loki |
| **Total** | **38/64** | **48GB/504GB** | **24GB/24GB** | 59% CPU, 9.5% RAM, 100% GPU |

## Directory Structure

```
infrastructure/unraid/
├── docker-compose.unraid.yml     # Main compose file (500 lines)
├── .env.unraid.example           # Environment template (100 lines)
├── .env.unraid                   # Your config (gitignored)
├── setup-unraid.sh               # Automated setup (300 lines)
├── README.md                     # This file
├── grafana/
│   ├── dashboards/
│   │   └── octollm-unraid.json   # Custom dashboard
│   └── provisioning/
│       ├── dashboards.yml
│       └── datasources.yml
├── prometheus/
│   ├── prometheus.unraid.yml     # Scrape configs
│   └── alerts.unraid.yml         # Alert rules (300 lines)
├── scripts/
│   ├── monitor-resources.sh      # Real-time monitoring
│   ├── backup-data.sh            # Backup script
│   ├── restore-data.sh           # Restore script
│   └── update-services.sh        # Update images
└── tests/
    ├── test-prerequisites.sh     # Check requirements
    ├── test-gpu.sh               # GPU passthrough test
    ├── test-services.sh          # Health checks
    └── test-ollama.sh            # LLM inference test
```

## Configuration

### Environment Variables

Edit `.env.unraid` (created by setup script):

```bash
# Network
HOST_IP=192.168.4.6

# Databases (auto-generated secure passwords)
POSTGRES_PASSWORD=***
REDIS_PASSWORD=***
QDRANT_API_KEY=***

# Local LLM (preferred)
PREFER_LOCAL_LLM=true
OLLAMA_PRIMARY_MODEL=llama3.1:8b

# Cloud APIs (optional fallback)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
```

### Ollama Models

The setup script downloads these models automatically:

- **llama3.1:8b** (8GB) - General purpose, fast inference
- **mixtral:8x7b** (24GB) - Advanced reasoning, slower
- **codellama:13b** (13GB) - Code generation specialist
- **nomic-embed-text** (768D) - Vector embeddings

Add more models manually:
```bash
docker exec octollm-ollama ollama pull llama3:70b
```

## Common Operations

### Start Services

```bash
cd /mnt/user/appdata/octollm/infrastructure/unraid
docker-compose up -d
```

### Stop Services

```bash
docker-compose stop
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker logs -f octollm-orchestrator
```

### Check Health

```bash
# Run health check tests
bash tests/test-services.sh

# Docker status
docker-compose ps

# Resource usage
docker stats --no-stream --filter "name=octollm-"
```

### Monitor Resources

```bash
# Real-time dashboard
bash scripts/monitor-resources.sh

# GPU monitoring
nvidia-smi -l 1
```

### Backup Data

```bash
bash scripts/backup-data.sh
```

### Update Services

```bash
bash scripts/update-services.sh
```

## Accessing Services

### Web Interfaces

- **Grafana**: http://192.168.4.6:3030 (admin / [password from .env.unraid])
- **Prometheus**: http://192.168.4.6:9090
- **Orchestrator API Docs**: http://192.168.4.6:3000/docs

### API Endpoints

```bash
# Test orchestrator
curl http://192.168.4.6:3000/health

# Test Ollama
curl http://192.168.4.6:3014/api/tags

# Submit task
curl -X POST http://192.168.4.6:3000/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"goal": "Explain quantum computing", "constraints": {"max_tokens": 500}}'
```

## Troubleshooting

### Services Won't Start

```bash
# Check Docker daemon
docker info

# Check logs
docker-compose logs

# Verify ports
ss -tuln | grep -E ':(3000|3001|6001|9090)'
```

### GPU Not Detected

```bash
# Test NVIDIA driver
nvidia-smi

# Test Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0.0-base-ubuntu22.04 nvidia-smi

# Check Unraid NVIDIA plugin
ls -la /boot/config/plugins/nvidia-driver.plg
```

### Out of Memory

```bash
# Check current usage
free -h
docker stats --no-stream

# Increase container memory limits in docker-compose.unraid.yml
# Reduce OLLAMA_NUM_PARALLEL in .env.unraid
```

### Slow Inference

```bash
# Check GPU usage
nvidia-smi

# Verify model loaded
curl http://192.168.4.6:3014/api/tags

# Check Ollama logs
docker logs octollm-ollama

# Reduce parallel requests
# Set OLLAMA_NUM_PARALLEL=2 in .env.unraid
```

### Port Conflicts

```bash
# Find conflicting process
ss -tuln | grep :3000

# Change port in docker-compose.unraid.yml
# Update HOST_IP and port mappings
```

## Performance Tuning

### CPU Pinning (Advanced)

Edit `docker-compose.unraid.yml`:

```yaml
services:
  ollama:
    cpuset: "0-7,32-39"  # NUMA node 0
```

### GPU Power Limit

```bash
# Increase power limit for Tesla P40 (default 250W, max 250W)
nvidia-smi -pl 250
```

### PostgreSQL Tuning

Add to `/mnt/user/appdata/octollm/postgres/data/postgresql.conf`:

```
shared_buffers = 2GB
effective_cache_size = 8GB
max_connections = 200
```

### Redis Tuning

Edit `.env.unraid`:

```bash
REDIS_MAXMEMORY=4gb
REDIS_MAXMEMORY_POLICY=allkeys-lru
```

## Cost Savings

### Local vs. Cloud LLM APIs

| Scenario | Cloud Cost/Month | Local Cost/Month | Savings/Year |
|----------|------------------|------------------|--------------|
| Light Dev (1000 requests) | $50 | $0 | $600 |
| Medium Dev (10000 requests) | $200 | $0 | $2,400 |
| Heavy Dev (50000 requests) | $700 | $0 | $8,400 |

**Note**: Local cost = electricity only (~$50/month for full server, not incremental)

### Total Cost of Ownership (TCO)

**One-Time Costs**:
- Dell PowerEdge R730xd: $2,000 (used)
- NVIDIA Tesla P40: $500 (used)
- Setup time: 4 hours @ $100/hr = $400
- **Total**: $2,900

**Monthly Costs**:
- Electricity: ~$50/month (full server)
- **vs. Cloud APIs**: $150-700/month

**Break-even**: 4-20 months depending on usage

## Security

### Firewall Configuration

Add Unraid firewall rules (Settings → Network):

```
# Allow from local network only
iptables -A INPUT -p tcp -s 192.168.0.0/16 --dport 3000:3100 -j ACCEPT
iptables -A INPUT -p tcp -s 192.168.0.0/16 --dport 6000:6999 -j ACCEPT
iptables -A INPUT -p tcp -s 192.168.0.0/16 --dport 9090 -j ACCEPT

# Block from internet
iptables -A INPUT -p tcp --dport 3000:9999 -j DROP
```

### VPN Access (Recommended)

Use Tailscale or WireGuard for remote access:

```bash
# Install Tailscale on Unraid
# Access services via: http://unraid.tail-scale.ts.net:3000
```

### Secrets Management

**Never commit** `.env.unraid` to version control!

```bash
# Rotate passwords regularly
bash setup-unraid.sh  # Regenerates secure passwords
```

## Migration to Cloud

When ready for production deployment:

1. **Export Data**:
   ```bash
   bash scripts/backup-data.sh
   # Uploads to S3/GCS
   ```

2. **Update Environment**:
   ```bash
   # Switch from local to cloud LLMs
   PREFER_LOCAL_LLM=false
   OPENAI_API_KEY=sk-...
   ```

3. **Deploy to Kubernetes**:
   ```bash
   cd ../kubernetes
   kubectl apply -k overlays/prod
   ```

See [Cloud Migration Guide](../../docs/operations/cloud-migration-from-unraid.md) for details.

## Support

- **Documentation**: [Unraid Deployment Guide](../../docs/operations/unraid-deployment-guide.md)
- **Issues**: https://github.com/your-org/octollm/issues
- **Discussions**: https://github.com/your-org/octollm/discussions

## License

MIT License - See [LICENSE](../../LICENSE)
