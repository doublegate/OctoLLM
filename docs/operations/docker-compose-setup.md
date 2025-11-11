# Docker Compose Setup Guide

**Estimated Time**: 30-45 minutes
**Difficulty**: Beginner to Intermediate
**Prerequisites**: Docker 24+, Docker Compose v2+

## Overview

This guide walks you through setting up OctoLLM using Docker Compose for:
- Local development environments
- Testing and staging environments
- Small-scale production deployments
- CI/CD testing

Docker Compose provides a simpler alternative to Kubernetes for smaller deployments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Project Structure](#project-structure)
3. [Environment Configuration](#environment-configuration)
4. [Base Configuration](#base-configuration)
5. [Database Services](#database-services)
6. [Core Services](#core-services)
7. [Networking](#networking)
8. [Volumes and Persistence](#volumes-and-persistence)
9. [Development Setup](#development-setup)
10. [Production Setup](#production-setup)
11. [Management Commands](#management-commands)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

```bash
# Check Docker version (24+ required)
docker --version

# Check Docker Compose version (v2+ required)
docker compose version

# Verify Docker daemon is running
docker info
```

### System Requirements

**Minimum** (Development):
- 4 CPU cores
- 8 GB RAM
- 20 GB disk space
- Linux, macOS, or Windows with WSL2

**Recommended** (Production):
- 8 CPU cores
- 16 GB RAM
- 50 GB SSD storage
- Linux server

### Install Docker (if needed)

**Linux (Ubuntu/Debian)**:
```bash
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

**macOS**:
```bash
# Install Docker Desktop
brew install --cask docker
```

**Windows**:
```powershell
# Install Docker Desktop with WSL2 backend
# Download from https://www.docker.com/products/docker-desktop
```

---

## Project Structure

```
octollm/
├── docker-compose.yml           # Base configuration
├── docker-compose.dev.yml       # Development overrides
├── docker-compose.prod.yml      # Production overrides
├── .env.example                 # Environment template
├── .env                         # Your environment (gitignored)
├── docker/                      # Dockerfiles
│   ├── orchestrator/
│   │   └── Dockerfile
│   ├── reflex-layer/
│   │   └── Dockerfile
│   └── arms/
│       ├── planner/Dockerfile
│       ├── executor/Dockerfile
│       └── ...
├── scripts/
│   ├── init-db.sh              # Database initialization
│   └── healthcheck.sh          # Health check script
└── data/                        # Persistent volumes (gitignored)
    ├── postgres/
    ├── redis/
    └── qdrant/
```

---

## Environment Configuration

### Create Environment File

```bash
# Copy example environment file
cp .env.example .env

# Edit with your preferred editor
nano .env
```

### Environment Variables

```bash
# .env
# ===========================================
# OctoLLM Docker Compose Environment
# ===========================================

# Environment
ENVIRONMENT=development  # development, staging, production
LOG_LEVEL=info           # debug, info, warning, error

# LLM API Keys
OPENAI_API_KEY=sk-XXXXXXXXXXXXXXXXXXXXX
ANTHROPIC_API_KEY=sk-ant-XXXXXXXXXXXXXXXXXXXXX

# Database Configuration
POSTGRES_VERSION=15-alpine
POSTGRES_DB=octollm
POSTGRES_USER=octollm
POSTGRES_PASSWORD=secure_password_change_me
POSTGRES_HOST=postgres
POSTGRES_PORT=5432

# Redis Configuration
REDIS_VERSION=7-alpine
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_MAXMEMORY=2gb
REDIS_MAXMEMORY_POLICY=allkeys-lru

# Qdrant Configuration
QDRANT_VERSION=v1.7.0
QDRANT_HOST=qdrant
QDRANT_PORT=6333

# Service Ports
REFLEX_LAYER_PORT=8001
ORCHESTRATOR_PORT=8000
PLANNER_ARM_PORT=8100
EXECUTOR_ARM_PORT=8101
CODER_ARM_PORT=8102
JUDGE_ARM_PORT=8103
GUARDIAN_ARM_PORT=8104
RETRIEVER_ARM_PORT=8105

# Resource Limits (Development)
POSTGRES_MEMORY_LIMIT=2g
REDIS_MEMORY_LIMIT=2g
QDRANT_MEMORY_LIMIT=2g
ORCHESTRATOR_MEMORY_LIMIT=4g
ARM_MEMORY_LIMIT=2g

# JWT Authentication
JWT_SECRET=your-secret-key-min-32-chars-change-me
JWT_ALGORITHM=HS256
JWT_EXPIRATION=3600

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090

# Development Settings
HOT_RELOAD=true
DEBUG_MODE=false
```

---

## Base Configuration

### Main Docker Compose File

```yaml
# docker-compose.yml
version: '3.8'

services:
  # ===========================================
  # Databases
  # ===========================================

  postgres:
    image: postgres:${POSTGRES_VERSION:-15-alpine}
    container_name: octollm-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init-db.sh:/docker-entrypoint-initdb.d/init-db.sh:ro
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - octollm-network

  redis:
    image: redis:${REDIS_VERSION:-7-alpine}
    container_name: octollm-redis
    restart: unless-stopped
    command: >
      redis-server
      --maxmemory ${REDIS_MAXMEMORY:-2gb}
      --maxmemory-policy ${REDIS_MAXMEMORY_POLICY:-allkeys-lru}
      --appendonly yes
      --appendfsync everysec
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - octollm-network

  qdrant:
    image: qdrant/qdrant:${QDRANT_VERSION:-v1.7.0}
    container_name: octollm-qdrant
    restart: unless-stopped
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
      - "6334:6334"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:6333/readyz || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - octollm-network

  # ===========================================
  # Core Services
  # ===========================================

  reflex-layer:
    build:
      context: .
      dockerfile: docker/reflex-layer/Dockerfile
    container_name: octollm-reflex-layer
    restart: unless-stopped
    environment:
      ENVIRONMENT: ${ENVIRONMENT}
      LOG_LEVEL: ${LOG_LEVEL}
      REDIS_HOST: ${REDIS_HOST}
      REDIS_PORT: ${REDIS_PORT}
    ports:
      - "${REFLEX_LAYER_PORT:-8001}:8001"
    depends_on:
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8001/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
    networks:
      - octollm-network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 512M

  orchestrator:
    build:
      context: .
      dockerfile: docker/orchestrator/Dockerfile
    container_name: octollm-orchestrator
    restart: unless-stopped
    environment:
      ENVIRONMENT: ${ENVIRONMENT}
      LOG_LEVEL: ${LOG_LEVEL}

      # Database connections
      POSTGRES_HOST: ${POSTGRES_HOST}
      POSTGRES_PORT: ${POSTGRES_PORT}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}

      REDIS_HOST: ${REDIS_HOST}
      REDIS_PORT: ${REDIS_PORT}

      QDRANT_HOST: ${QDRANT_HOST}
      QDRANT_PORT: ${QDRANT_PORT}

      # LLM API Keys
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}

      # JWT
      JWT_SECRET: ${JWT_SECRET}
      JWT_ALGORITHM: ${JWT_ALGORITHM}
      JWT_EXPIRATION: ${JWT_EXPIRATION}

      # Arm endpoints
      PLANNER_ARM_URL: http://planner-arm:8100
      EXECUTOR_ARM_URL: http://executor-arm:8101
      CODER_ARM_URL: http://coder-arm:8102
      JUDGE_ARM_URL: http://judge-arm:8103
      GUARDIAN_ARM_URL: http://guardian-arm:8104
      RETRIEVER_ARM_URL: http://retriever-arm:8105
    ports:
      - "${ORCHESTRATOR_PORT:-8000}:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
      qdrant:
        condition: service_healthy
      reflex-layer:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    networks:
      - octollm-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: ${ORCHESTRATOR_MEMORY_LIMIT:-4g}

  # ===========================================
  # Arms
  # ===========================================

  planner-arm:
    build:
      context: .
      dockerfile: docker/arms/planner/Dockerfile
    container_name: octollm-planner-arm
    restart: unless-stopped
    environment:
      ENVIRONMENT: ${ENVIRONMENT}
      LOG_LEVEL: ${LOG_LEVEL}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      POSTGRES_HOST: ${POSTGRES_HOST}
      POSTGRES_PORT: ${POSTGRES_PORT}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    ports:
      - "${PLANNER_ARM_PORT:-8100}:8100"
    depends_on:
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8100/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
    networks:
      - octollm-network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: ${ARM_MEMORY_LIMIT:-2g}

  executor-arm:
    build:
      context: .
      dockerfile: docker/arms/executor/Dockerfile
    container_name: octollm-executor-arm
    restart: unless-stopped
    privileged: false  # Run sandboxed for security
    environment:
      ENVIRONMENT: ${ENVIRONMENT}
      LOG_LEVEL: ${LOG_LEVEL}
    ports:
      - "${EXECUTOR_ARM_PORT:-8101}:8101"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8101/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
    networks:
      - octollm-network
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: ${ARM_MEMORY_LIMIT:-2g}

  coder-arm:
    build:
      context: .
      dockerfile: docker/arms/coder/Dockerfile
    container_name: octollm-coder-arm
    restart: unless-stopped
    environment:
      ENVIRONMENT: ${ENVIRONMENT}
      LOG_LEVEL: ${LOG_LEVEL}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      QDRANT_HOST: ${QDRANT_HOST}
      QDRANT_PORT: ${QDRANT_PORT}
    ports:
      - "${CODER_ARM_PORT:-8102}:8102"
    depends_on:
      qdrant:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8102/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
    networks:
      - octollm-network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: ${ARM_MEMORY_LIMIT:-2g}

  judge-arm:
    build:
      context: .
      dockerfile: docker/arms/judge/Dockerfile
    container_name: octollm-judge-arm
    restart: unless-stopped
    environment:
      ENVIRONMENT: ${ENVIRONMENT}
      LOG_LEVEL: ${LOG_LEVEL}
      OPENAI_API_KEY: ${OPENAI_API_KEY}
    ports:
      - "${JUDGE_ARM_PORT:-8103}:8103"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8103/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
    networks:
      - octollm-network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: ${ARM_MEMORY_LIMIT:-2g}

  guardian-arm:
    build:
      context: .
      dockerfile: docker/arms/guardian/Dockerfile
    container_name: octollm-guardian-arm
    restart: unless-stopped
    environment:
      ENVIRONMENT: ${ENVIRONMENT}
      LOG_LEVEL: ${LOG_LEVEL}
    ports:
      - "${GUARDIAN_ARM_PORT:-8104}:8104"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8104/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
    networks:
      - octollm-network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: ${ARM_MEMORY_LIMIT:-2g}

  retriever-arm:
    build:
      context: .
      dockerfile: docker/arms/retriever/Dockerfile
    container_name: octollm-retriever-arm
    restart: unless-stopped
    environment:
      ENVIRONMENT: ${ENVIRONMENT}
      LOG_LEVEL: ${LOG_LEVEL}
      POSTGRES_HOST: ${POSTGRES_HOST}
      POSTGRES_PORT: ${POSTGRES_PORT}
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      QDRANT_HOST: ${QDRANT_HOST}
      QDRANT_PORT: ${QDRANT_PORT}
    ports:
      - "${RETRIEVER_ARM_PORT:-8105}:8105"
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8105/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
    networks:
      - octollm-network
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: ${ARM_MEMORY_LIMIT:-2g}

# ===========================================
# Networks
# ===========================================

networks:
  octollm-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

# ===========================================
# Volumes
# ===========================================

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  qdrant_data:
    driver: local
```

---

## Development Setup

### Development Override File

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  orchestrator:
    build:
      target: development
    volumes:
      - ./orchestrator:/app:delegated
      - /app/.venv  # Don't override virtual environment
    environment:
      HOT_RELOAD: "true"
      DEBUG_MODE: "true"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  planner-arm:
    volumes:
      - ./arms/planner:/app:delegated
      - /app/.venv
    command: uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload

  coder-arm:
    volumes:
      - ./arms/coder:/app:delegated
      - /app/.venv
    command: uvicorn app.main:app --host 0.0.0.0 --port 8102 --reload

  # Add similar overrides for other arms...

  # Development tools
  adminer:
    image: adminer:latest
    container_name: octollm-adminer
    restart: unless-stopped
    ports:
      - "8080:8080"
    environment:
      ADMINER_DEFAULT_SERVER: postgres
    networks:
      - octollm-network

  redis-commander:
    image: rediscommander/redis-commander:latest
    container_name: octollm-redis-commander
    restart: unless-stopped
    environment:
      REDIS_HOSTS: local:redis:6379
    ports:
      - "8081:8081"
    networks:
      - octollm-network
```

### Start Development Environment

```bash
# Start with development overrides
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

---

## Production Setup

### Production Override File

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  postgres:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    volumes:
      - /var/lib/octollm/postgres:/var/lib/postgresql/data
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"

  redis:
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
    volumes:
      - /var/lib/octollm/redis:/data
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "10"

  qdrant:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    volumes:
      - /var/lib/octollm/qdrant:/qdrant/storage
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "10"

  orchestrator:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "10"

  # Scale arms for production
  planner-arm:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 4G

  coder-arm:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 4G

  # Add nginx reverse proxy
  nginx:
    image: nginx:alpine
    container_name: octollm-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - orchestrator
    networks:
      - octollm-network
    logging:
      driver: "json-file"
      options:
        max-size: "50m"
        max-file: "10"
```

### NGINX Configuration

```nginx
# nginx/nginx.conf
events {
    worker_connections 1024;
}

http {
    upstream orchestrator {
        least_conn;
        server orchestrator:8000;
    }

    server {
        listen 80;
        server_name api.octollm.example.com;

        # Redirect to HTTPS
        return 301 https://$server_name$request_uri;
    }

    server {
        listen 443 ssl http2;
        server_name api.octollm.example.com;

        ssl_certificate /etc/nginx/ssl/cert.pem;
        ssl_certificate_key /etc/nginx/ssl/key.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers HIGH:!aNULL:!MD5;

        client_max_body_size 10M;

        location / {
            proxy_pass http://orchestrator;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;

            proxy_connect_timeout 60s;
            proxy_send_timeout 120s;
            proxy_read_timeout 120s;
        }

        location /health {
            proxy_pass http://orchestrator/health;
            access_log off;
        }
    }
}
```

### Start Production Environment

```bash
# Build images
docker compose -f docker-compose.yml -f docker-compose.prod.yml build

# Start services
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify all services are healthy
docker compose ps

# View aggregated logs
docker compose logs -f
```

---

## Management Commands

### Common Operations

```bash
# Start all services
docker compose up -d

# Start specific service
docker compose up -d orchestrator

# Stop all services
docker compose stop

# Stop and remove containers
docker compose down

# Stop, remove containers, and delete volumes (WARNING: Data loss!)
docker compose down -v

# View service status
docker compose ps

# View logs
docker compose logs -f [service-name]

# Restart service
docker compose restart orchestrator

# Rebuild and restart service
docker compose up -d --build orchestrator

# Scale a service
docker compose up -d --scale planner-arm=3

# Execute command in running container
docker compose exec orchestrator /bin/sh

# View resource usage
docker stats
```

### Database Operations

```bash
# Backup PostgreSQL
docker compose exec postgres pg_dump -U octollm octollm > backup.sql

# Restore PostgreSQL
cat backup.sql | docker compose exec -T postgres psql -U octollm octollm

# Access PostgreSQL shell
docker compose exec postgres psql -U octollm

# Backup Redis
docker compose exec redis redis-cli SAVE
docker compose exec redis cat /data/dump.rdb > redis-backup.rdb

# Access Redis CLI
docker compose exec redis redis-cli

# Backup Qdrant
docker compose exec qdrant tar -czf /tmp/qdrant-backup.tar.gz /qdrant/storage
docker compose cp qdrant:/tmp/qdrant-backup.tar.gz ./qdrant-backup.tar.gz
```

### Monitoring and Debugging

```bash
# View container resource usage
docker compose top

# Inspect service
docker compose inspect orchestrator

# View container logs with timestamps
docker compose logs -f --timestamps orchestrator

# Follow logs from multiple services
docker compose logs -f orchestrator planner-arm coder-arm

# Check service health
docker compose exec orchestrator curl http://localhost:8000/health

# Run health checks manually
./scripts/healthcheck.sh
```

---

## Troubleshooting

### Service Won't Start

```bash
# Check service logs
docker compose logs [service-name]

# Check container status
docker compose ps

# Inspect container
docker compose exec [service-name] /bin/sh

# Rebuild without cache
docker compose build --no-cache [service-name]
docker compose up -d [service-name]
```

### Database Connection Issues

```bash
# Verify database is healthy
docker compose exec postgres pg_isready -U octollm

# Check network connectivity
docker compose exec orchestrator ping postgres

# View database logs
docker compose logs postgres

# Reset database (WARNING: Data loss!)
docker compose down
docker volume rm octollm_postgres_data
docker compose up -d postgres
```

### Out of Memory Errors

```bash
# Check memory usage
docker stats

# Increase memory limits in .env
ARM_MEMORY_LIMIT=4g
ORCHESTRATOR_MEMORY_LIMIT=8g

# Restart services
docker compose up -d
```

### Port Conflicts

```bash
# Find what's using the port
sudo lsof -i :8000

# Change port in .env
ORCHESTRATOR_PORT=8001

# Restart service
docker compose up -d orchestrator
```

### Image Build Failures

```bash
# Clear Docker build cache
docker builder prune

# Rebuild from scratch
docker compose build --no-cache --pull

# Check Dockerfile syntax
docker compose config
```

---

## Production Best Practices

### 1. Environment Variables

- **Never commit `.env`** to version control
- Use different `.env` files for dev/staging/prod
- Store secrets in a secret manager (Vault, AWS Secrets Manager)

### 2. Logging

Configure log rotation to prevent disk space issues:

```yaml
# Add to each service in docker-compose.prod.yml
logging:
  driver: "json-file"
  options:
    max-size: "100m"
    max-file: "10"
```

### 3. Backups

Set up automated backups:

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/backups/$(date +%Y-%m-%d)"
mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker compose exec -T postgres pg_dump -U octollm octollm > $BACKUP_DIR/postgres.sql

# Backup Redis
docker compose exec redis redis-cli SAVE
docker compose cp redis:/data/dump.rdb $BACKUP_DIR/redis.rdb

# Backup Qdrant
docker compose exec qdrant tar -czf /tmp/qdrant.tar.gz /qdrant/storage
docker compose cp qdrant:/tmp/qdrant.tar.gz $BACKUP_DIR/qdrant.tar.gz

# Upload to S3 or backup server
# aws s3 sync $BACKUP_DIR s3://your-backup-bucket/octollm/
```

### 4. Health Monitoring

Set up automated health checks:

```bash
#!/bin/bash
# scripts/healthcheck.sh

SERVICES="orchestrator reflex-layer planner-arm coder-arm"
FAILED=""

for service in $SERVICES; do
  if ! docker compose exec -T $service curl -sf http://localhost:8000/health > /dev/null; then
    FAILED="$FAILED $service"
  fi
done

if [ -n "$FAILED" ]; then
  echo "Health check failed for:$FAILED"
  # Send alert (email, Slack, PagerDuty, etc.)
  exit 1
fi
```

### 5. Resource Limits

Always set resource limits in production:

```yaml
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 4G
    reservations:
      cpus: '1'
      memory: 2G
```

---

## Next Steps

After successful setup:

1. **Monitoring** - Set up Prometheus and Grafana
2. **Backups** - Configure automated backup scripts
3. **CI/CD** - Integrate with your deployment pipeline
4. **Scaling** - Consider Kubernetes for larger deployments
5. **Security** - Implement TLS, rotate secrets, scan images

## See Also

- [Kubernetes Deployment Guide](kubernetes-deployment.md) - For production at scale
- [Monitoring and Alerting](monitoring-alerting.md) - Set up observability
- [Performance Tuning](performance-tuning.md) - Optimize resource usage
- [Troubleshooting Playbooks](troubleshooting-playbooks.md) - Common issues
