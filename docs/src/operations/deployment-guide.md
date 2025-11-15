# Kubernetes Production Deployment Guide

**Version**: 2.0
**Last Updated**: 2025-11-10
**Estimated Time**: 3-4 hours
**Difficulty**: Advanced
**Target**: Production-Ready Kubernetes Deployment

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Cluster Requirements](#cluster-requirements)
4. [Architecture Overview](#architecture-overview)
5. [Complete Kubernetes Manifests](#complete-kubernetes-manifests)
6. [Helm Chart Structure](#helm-chart-structure)
7. [Deployment Procedures](#deployment-procedures)
8. [Multi-Environment Setup](#multi-environment-setup)
9. [Security Configuration](#security-configuration)
10. [Post-Deployment Verification](#post-deployment-verification)
11. [Troubleshooting](#troubleshooting)
12. [Production Checklist](#production-checklist)

---

## Overview

This guide provides **complete, production-ready Kubernetes manifests** for deploying OctoLLM to a Kubernetes cluster with:

- **High Availability**: Multiple replicas with pod disruption budgets
- **Auto-Scaling**: Horizontal Pod Autoscalers for all components
- **Security**: Network policies, Pod Security Standards, RBAC
- **Persistence**: StatefulSets with persistent volumes for databases
- **Observability**: Prometheus metrics, structured logging, distributed tracing
- **TLS Encryption**: HTTPS ingress with automatic certificate management

### What This Guide Covers

- 15+ complete YAML manifests (copy-pasteable, production-ready)
- Helm chart structure with values files for dev/staging/prod
- Database initialization and migration procedures
- Secret management with sealed-secrets
- Network policy configuration for zero-trust architecture
- Complete troubleshooting playbook

---

## Prerequisites

### Required Tools

```bash
# Verify kubectl (v1.27+)
kubectl version --client
# Expected: Client Version: v1.28.0

# Verify Helm (v3.12+)
helm version
# Expected: version.BuildInfo{Version:"v3.13.0"...}

# Verify cluster access
kubectl cluster-info
kubectl get nodes

# Verify metrics-server (required for HPA)
kubectl get deployment metrics-server -n kube-system

# Verify Prometheus Operator (optional, for monitoring)
kubectl get crd servicemonitors.monitoring.coreos.com
```

### Install Missing Tools

**kubectl**:
```bash
# Linux
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# macOS
brew install kubectl
```

**Helm**:
```bash
# Linux/macOS
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Verify
helm version
```

**metrics-server** (if not installed):
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

### Kubernetes Cluster Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **Kubernetes Version** | 1.27+ | 1.28+ |
| **Nodes** | 3 (1 control, 2 workers) | 5+ (1 control, 4+ workers) |
| **CPU per Node** | 4 vCPU | 8 vCPU |
| **RAM per Node** | 16 GB | 32 GB |
| **Storage per Node** | 100 GB SSD | 200 GB NVMe SSD |
| **Network** | 1 Gbps | 10 Gbps |

**Enabled Features**:
- ✅ RBAC
- ✅ NetworkPolicy support (Calico, Cilium, or Weave)
- ✅ PersistentVolume support (StorageClass configured)
- ✅ LoadBalancer or Ingress controller
- ✅ metrics-server (for HPA)

### External Dependencies

| Service | Version | Purpose | Alternative |
|---------|---------|---------|-------------|
| **PostgreSQL** | 15+ | Global memory, task state | Self-hosted in cluster |
| **Redis** | 7+ | Caching, reflex layer | Self-hosted in cluster |
| **Qdrant** | 1.7+ | Vector database | Weaviate, Pinecone |
| **OpenAI API** | - | LLM provider | Anthropic, Azure OpenAI |
| **Anthropic API** | - | LLM provider (optional) | OpenAI |

---

## Cluster Requirements

### Resource Allocation

**Development Cluster** (minimum viable):
```
Total Resources:
- 12 vCPU (3 nodes × 4 vCPU)
- 48 GB RAM (3 nodes × 16 GB)
- 300 GB storage

Component Breakdown:
- Databases: 4 vCPU, 8 GB RAM, 100 GB storage
- Orchestrator: 4 vCPU, 8 GB RAM
- Arms: 4 vCPU, 8 GB RAM
- Overhead: ~25% for system pods
```

**Production Cluster** (recommended):
```
Total Resources:
- 40 vCPU (5 nodes × 8 vCPU)
- 160 GB RAM (5 nodes × 32 GB)
- 1 TB storage

Component Breakdown:
- Databases: 8 vCPU, 16 GB RAM, 300 GB storage (dedicated nodes)
- Orchestrator: 8 vCPU, 16 GB RAM
- Arms: 12 vCPU, 24 GB RAM
- Reflex Layer: 4 vCPU, 8 GB RAM
- Monitoring: 4 vCPU, 8 GB RAM
- Overhead: ~25% for system pods
```

### Network Requirements

```mermaid
graph TB
    subgraph "External"
        USER[Users/Clients]
        LLM[LLM APIs<br/>OpenAI, Anthropic]
    end

    subgraph "Kubernetes Cluster"
        LB[Load Balancer<br/>443/HTTPS]

        subgraph "octollm Namespace"
            ING[Ingress<br/>TLS Termination]
            REFLEX[Reflex Layer<br/>:8001]
            ORCH[Orchestrator<br/>:8000]

            subgraph "Arms"
                PLANNER[Planner<br/>:8100]
                EXEC[Executor<br/>:8101]
                CODER[Coder<br/>:8102]
                JUDGE[Judge<br/>:8103]
                GUARD[Guardian<br/>:8104]
                RETR[Retriever<br/>:8105]
            end

            subgraph "Data Layer"
                PG[(PostgreSQL<br/>:5432)]
                REDIS[(Redis<br/>:6379)]
                QDRANT[(Qdrant<br/>:6333)]
            end
        end
    end

    USER -->|HTTPS| LB
    LB --> ING
    ING --> REFLEX
    REFLEX --> ORCH

    ORCH --> PLANNER
    ORCH --> EXEC
    ORCH --> CODER
    ORCH --> JUDGE
    ORCH --> GUARD
    ORCH --> RETR

    ORCH --> PG
    ORCH --> REDIS
    RETR --> QDRANT

    ORCH -.->|API Calls| LLM
    EXEC -.->|External Actions| LLM
```

**Firewall Rules**:
```yaml
Ingress (from internet):
  - Port 443 (HTTPS) → Load Balancer

Egress (to internet):
  - Port 443 (HTTPS) → LLM APIs (api.openai.com, api.anthropic.com)
  - Port 443 (HTTPS) → Package registries (for updates)

Internal (cluster):
  - All pods can communicate (subject to NetworkPolicies)
  - DNS resolution to kube-dns/CoreDNS
```

---

## Architecture Overview

### Kubernetes Architecture Diagram

```mermaid
graph TB
    subgraph "Namespace: octollm"
        subgraph "Ingress Layer"
            NGINX[NGINX Ingress Controller<br/>TLS, Rate Limiting]
            CERT[cert-manager<br/>Let's Encrypt]
        end

        subgraph "Application Layer"
            REFLEX[Reflex Layer<br/>Deployment: 3-10 replicas<br/>HPA: CPU 70%]
            ORCH[Orchestrator<br/>Deployment: 2-5 replicas<br/>HPA: CPU/Memory]
        end

        subgraph "Arms Layer"
            PLANNER[Planner Arm<br/>2-6 replicas]
            EXECUTOR[Executor Arm<br/>1-5 replicas<br/>gVisor sandbox]
            CODER[Coder Arm<br/>2-4 replicas]
            JUDGE[Judge Arm<br/>1-3 replicas]
            GUARDIAN[Guardian Arm<br/>2-4 replicas]
            RETRIEVER[Retriever Arm<br/>2-4 replicas]
        end

        subgraph "Data Layer"
            POSTGRES[PostgreSQL<br/>StatefulSet: 3 replicas<br/>PVC: 100Gi]
            REDIS[Redis Sentinel<br/>StatefulSet: 3 replicas<br/>PVC: 10Gi]
            QDRANT[Qdrant<br/>StatefulSet: 3 replicas<br/>PVC: 50Gi]
        end

        subgraph "Monitoring"
            PROM[Prometheus<br/>Metrics]
            GRAF[Grafana<br/>Dashboards]
            LOKI[Loki<br/>Logs]
            JAEGER[Jaeger<br/>Traces]
        end
    end

    subgraph "Storage"
        SC[StorageClass<br/>octollm-fast-ssd]
        PV1[PersistentVolume<br/>PostgreSQL]
        PV2[PersistentVolume<br/>Redis]
        PV3[PersistentVolume<br/>Qdrant]
    end

    NGINX --> REFLEX
    REFLEX --> ORCH
    ORCH --> PLANNER
    ORCH --> EXECUTOR
    ORCH --> CODER
    ORCH --> JUDGE
    ORCH --> GUARDIAN
    ORCH --> RETRIEVER

    ORCH --> POSTGRES
    ORCH --> REDIS
    RETRIEVER --> QDRANT
    GUARDIAN --> REDIS

    POSTGRES -.-> PV1
    REDIS -.-> PV2
    QDRANT -.-> PV3

    SC --> PV1
    SC --> PV2
    SC --> PV3
```

### Component Specifications

| Component | Type | Replicas | CPU (Request/Limit) | Memory (Request/Limit) | Storage |
|-----------|------|----------|---------------------|------------------------|---------|
| **Reflex Layer** | Deployment | 3-10 | 200m/500m | 256Mi/512Mi | - |
| **Orchestrator** | Deployment | 2-5 | 1000m/2000m | 2Gi/4Gi | - |
| **Planner Arm** | Deployment | 2-6 | 500m/1000m | 1Gi/2Gi | - |
| **Executor Arm** | Deployment | 1-5 | 1000m/2000m | 1Gi/2Gi | - |
| **Coder Arm** | Deployment | 2-4 | 500m/1000m | 1Gi/2Gi | - |
| **Judge Arm** | Deployment | 1-3 | 500m/1000m | 512Mi/1Gi | - |
| **Guardian Arm** | Deployment | 2-4 | 200m/500m | 512Mi/1Gi | - |
| **Retriever Arm** | Deployment | 2-4 | 500m/1000m | 1Gi/2Gi | - |
| **PostgreSQL** | StatefulSet | 3 | 1000m/2000m | 2Gi/4Gi | 100Gi |
| **Redis** | StatefulSet | 3 | 500m/1000m | 2Gi/4Gi | 10Gi |
| **Qdrant** | StatefulSet | 3 | 1000m/2000m | 2Gi/4Gi | 50Gi |

---

## Complete Kubernetes Manifests

### 1. Namespace and Resource Quotas

```yaml
# manifests/00-namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: octollm
  labels:
    name: octollm
    env: production
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: octollm-quota
  namespace: octollm
spec:
  hard:
    requests.cpu: "50"
    requests.memory: 100Gi
    requests.storage: 1Ti
    persistentvolumeclaims: "20"
    pods: "100"
    services: "30"
    secrets: "50"
    configmaps: "50"
---
apiVersion: v1
kind: LimitRange
metadata:
  name: octollm-limits
  namespace: octollm
spec:
  limits:
  - max:
      cpu: "4"
      memory: 8Gi
    min:
      cpu: 50m
      memory: 64Mi
    default:
      cpu: 500m
      memory: 512Mi
    defaultRequest:
      cpu: 100m
      memory: 128Mi
    type: Container
  - max:
      storage: 200Gi
    min:
      storage: 1Gi
    type: PersistentVolumeClaim
```

### 2. Storage Configuration

```yaml
# manifests/01-storage.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: octollm-fast-ssd
provisioner: kubernetes.io/aws-ebs  # Change for your cloud provider
parameters:
  type: gp3
  iopsPerGB: "50"
  encrypted: "true"
  fsType: ext4
allowVolumeExpansion: true
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
---
# For GCP, use:
# apiVersion: storage.k8s.io/v1
# kind: StorageClass
# metadata:
#   name: octollm-fast-ssd
# provisioner: kubernetes.io/gce-pd
# parameters:
#   type: pd-ssd
#   replication-type: regional-pd
# allowVolumeExpansion: true
# reclaimPolicy: Retain
# volumeBindingMode: WaitForFirstConsumer
---
# For Azure, use:
# apiVersion: storage.k8s.io/v1
# kind: StorageClass
# metadata:
#   name: octollm-fast-ssd
# provisioner: kubernetes.io/azure-disk
# parameters:
#   storageaccounttype: Premium_LRS
#   kind: Managed
# allowVolumeExpansion: true
# reclaimPolicy: Retain
# volumeBindingMode: WaitForFirstConsumer
```

### 3. PostgreSQL StatefulSet (High Availability)

```yaml
# manifests/10-postgresql.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-config
  namespace: octollm
data:
  POSTGRES_DB: octollm
  POSTGRES_USER: octollm
  # PostgreSQL configuration
  postgresql.conf: |
    # Memory Settings
    shared_buffers = 512MB
    effective_cache_size = 1536MB
    maintenance_work_mem = 128MB
    work_mem = 16MB

    # Checkpointing
    checkpoint_completion_target = 0.9
    wal_buffers = 16MB

    # Write-Ahead Log
    max_wal_size = 2GB
    min_wal_size = 1GB

    # Query Tuning
    random_page_cost = 1.1  # For SSD
    effective_io_concurrency = 200

    # Monitoring
    track_activities = on
    track_counts = on
    track_io_timing = on
    track_functions = all

    # Logging
    log_destination = 'stderr'
    logging_collector = on
    log_directory = 'log'
    log_filename = 'postgresql-%Y-%m-%d_%H%M%S.log'
    log_rotation_age = 1d
    log_rotation_size = 100MB
    log_line_prefix = '%m [%p] %q%u@%d '
    log_timezone = 'UTC'

    # Replication (for HA)
    wal_level = replica
    max_wal_senders = 10
    max_replication_slots = 10
    hot_standby = on
---
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
  namespace: octollm
type: Opaque
stringData:
  POSTGRES_PASSWORD: "CHANGE_ME_USE_SEALED_SECRETS_IN_PROD"
  POSTGRES_REPLICATION_PASSWORD: "CHANGE_ME_REPLICATION_PASSWORD"
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: octollm
  labels:
    app: postgres
spec:
  ports:
  - port: 5432
    name: postgres
  clusterIP: None  # Headless service for StatefulSet
  selector:
    app: postgres
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-read
  namespace: octollm
  labels:
    app: postgres
spec:
  ports:
  - port: 5432
    name: postgres
  selector:
    app: postgres
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: octollm
spec:
  serviceName: postgres
  replicas: 3  # Primary + 2 replicas for HA
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      securityContext:
        fsGroup: 999  # postgres user
        runAsNonRoot: true
        runAsUser: 999
      initContainers:
      - name: init-postgres
        image: postgres:15-alpine
        command:
        - sh
        - -c
        - |
          set -e
          # Check if this is the primary or replica
          if [ "$HOSTNAME" == "postgres-0" ]; then
            echo "Initializing as primary"
            mkdir -p /var/lib/postgresql/data
          else
            echo "Initializing as replica"
            # Wait for primary to be ready
            until pg_isready -h postgres-0.postgres.octollm.svc.cluster.local -U octollm; do
              echo "Waiting for primary..."
              sleep 2
            done
            # Create replica from primary using pg_basebackup
            if [ ! -f /var/lib/postgresql/data/PG_VERSION ]; then
              PGPASSWORD=$POSTGRES_REPLICATION_PASSWORD pg_basebackup \
                -h postgres-0.postgres.octollm.svc.cluster.local \
                -U replication \
                -D /var/lib/postgresql/data \
                -P -v
              # Create standby.signal for replica
              touch /var/lib/postgresql/data/standby.signal
            fi
          fi
        env:
        - name: POSTGRES_REPLICATION_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_REPLICATION_PASSWORD
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
          subPath: postgres
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
          name: postgres
        env:
        - name: POSTGRES_DB
          valueFrom:
            configMapKeyRef:
              name: postgres-config
              key: POSTGRES_DB
        - name: POSTGRES_USER
          valueFrom:
            configMapKeyRef:
              name: postgres-config
              key: POSTGRES_USER
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_PASSWORD
        - name: PGDATA
          value: /var/lib/postgresql/data/pgdata
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
          subPath: postgres
        - name: postgres-config
          mountPath: /etc/postgresql/postgresql.conf
          subPath: postgresql.conf
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - octollm
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 6
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - octollm
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
      volumes:
      - name: postgres-config
        configMap:
          name: postgres-config
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: octollm-fast-ssd
      resources:
        requests:
          storage: 100Gi
---
# PostgreSQL Backup CronJob
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
  namespace: octollm
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: backup
            image: postgres:15-alpine
            command:
            - sh
            - -c
            - |
              BACKUP_FILE="/backups/octollm-$(date +%Y%m%d-%H%M%S).sql.gz"
              pg_dump -h postgres-0.postgres.octollm.svc.cluster.local \
                -U octollm -d octollm | gzip > $BACKUP_FILE
              echo "Backup completed: $BACKUP_FILE"
              # Cleanup backups older than 30 days
              find /backups -name "octollm-*.sql.gz" -mtime +30 -delete
            env:
            - name: PGPASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: POSTGRES_PASSWORD
            volumeMounts:
            - name: backup-storage
              mountPath: /backups
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: postgres-backup-pvc
          restartPolicy: OnFailure
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-backup-pvc
  namespace: octollm
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: octollm-fast-ssd
  resources:
    requests:
      storage: 200Gi
```

### 4. Redis Sentinel (High Availability)

```yaml
# manifests/11-redis.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-config
  namespace: octollm
data:
  master.conf: |
    bind 0.0.0.0
    protected-mode yes
    port 6379

    # Memory
    maxmemory 2gb
    maxmemory-policy allkeys-lru

    # Persistence
    appendonly yes
    appendfsync everysec
    auto-aof-rewrite-percentage 100
    auto-aof-rewrite-min-size 64mb

    # Replication
    min-replicas-to-write 1
    min-replicas-max-lag 10

    # Performance
    tcp-backlog 511
    timeout 0
    tcp-keepalive 300

    # Logging
    loglevel notice

  replica.conf: |
    bind 0.0.0.0
    protected-mode yes
    port 6379

    # Memory
    maxmemory 2gb
    maxmemory-policy allkeys-lru

    # Persistence
    appendonly yes
    appendfsync everysec

    # Replication
    replicaof redis-0.redis.octollm.svc.cluster.local 6379

  sentinel.conf: |
    bind 0.0.0.0
    port 26379
    sentinel monitor mymaster redis-0.redis.octollm.svc.cluster.local 6379 2
    sentinel down-after-milliseconds mymaster 5000
    sentinel parallel-syncs mymaster 1
    sentinel failover-timeout mymaster 10000
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: octollm
  labels:
    app: redis
spec:
  ports:
  - port: 6379
    name: redis
  - port: 26379
    name: sentinel
  clusterIP: None  # Headless service
  selector:
    app: redis
---
apiVersion: v1
kind: Service
metadata:
  name: redis-read
  namespace: octollm
  labels:
    app: redis
spec:
  ports:
  - port: 6379
    name: redis
  selector:
    app: redis
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: octollm
spec:
  serviceName: redis
  replicas: 3  # Master + 2 replicas
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      securityContext:
        fsGroup: 999  # redis user
        runAsNonRoot: true
        runAsUser: 999
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
          name: redis
        command:
        - sh
        - -c
        - |
          if [ "$HOSTNAME" == "redis-0" ]; then
            redis-server /etc/redis/master.conf
          else
            redis-server /etc/redis/replica.conf
          fi
        volumeMounts:
        - name: redis-storage
          mountPath: /data
        - name: redis-config
          mountPath: /etc/redis
        resources:
          requests:
            cpu: 500m
            memory: 2Gi
          limits:
            cpu: 1000m
            memory: 4Gi
        livenessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - redis-cli
            - ping
          initialDelaySeconds: 5
          periodSeconds: 5
      - name: sentinel
        image: redis:7-alpine
        ports:
        - containerPort: 26379
          name: sentinel
        command:
        - redis-sentinel
        - /etc/redis/sentinel.conf
        volumeMounts:
        - name: redis-config
          mountPath: /etc/redis
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: 200m
            memory: 256Mi
      volumes:
      - name: redis-config
        configMap:
          name: redis-config
  volumeClaimTemplates:
  - metadata:
      name: redis-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: octollm-fast-ssd
      resources:
        requests:
          storage: 10Gi
```

### 5. Qdrant Vector Database

```yaml
# manifests/12-qdrant.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: qdrant-config
  namespace: octollm
data:
  config.yaml: |
    log_level: INFO

    storage:
      storage_path: /qdrant/storage
      snapshots_path: /qdrant/snapshots
      temp_path: /qdrant/temp

    service:
      host: 0.0.0.0
      http_port: 6333
      grpc_port: 6334
      enable_tls: false

    cluster:
      enabled: true
      p2p:
        port: 6335
      consensus:
        tick_period_ms: 100
---
apiVersion: v1
kind: Service
metadata:
  name: qdrant
  namespace: octollm
  labels:
    app: qdrant
spec:
  ports:
  - port: 6333
    name: http
  - port: 6334
    name: grpc
  - port: 6335
    name: p2p
  clusterIP: None  # Headless for StatefulSet
  selector:
    app: qdrant
---
apiVersion: v1
kind: Service
metadata:
  name: qdrant-client
  namespace: octollm
  labels:
    app: qdrant
spec:
  ports:
  - port: 6333
    name: http
  - port: 6334
    name: grpc
  selector:
    app: qdrant
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
  namespace: octollm
spec:
  serviceName: qdrant
  replicas: 3
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      securityContext:
        fsGroup: 1000
        runAsNonRoot: true
        runAsUser: 1000
      containers:
      - name: qdrant
        image: qdrant/qdrant:v1.7.0
        ports:
        - containerPort: 6333
          name: http
        - containerPort: 6334
          name: grpc
        - containerPort: 6335
          name: p2p
        env:
        - name: QDRANT__CLUSTER__ENABLED
          value: "true"
        - name: QDRANT__CLUSTER__P2P__PORT
          value: "6335"
        volumeMounts:
        - name: qdrant-storage
          mountPath: /qdrant/storage
        - name: qdrant-config
          mountPath: /qdrant/config
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /
            port: 6333
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /readyz
            port: 6333
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: qdrant-config
        configMap:
          name: qdrant-config
  volumeClaimTemplates:
  - metadata:
      name: qdrant-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: octollm-fast-ssd
      resources:
        requests:
          storage: 50Gi
```

### 6. Application Configuration

```yaml
# manifests/20-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: octollm-config
  namespace: octollm
data:
  # Environment
  ENVIRONMENT: "production"
  LOG_LEVEL: "info"
  LOG_FORMAT: "json"

  # Database URLs (using internal DNS)
  POSTGRES_HOST: "postgres-0.postgres.octollm.svc.cluster.local"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "octollm"
  POSTGRES_USER: "octollm"
  POSTGRES_MAX_CONNECTIONS: "100"
  POSTGRES_SSL_MODE: "prefer"

  # Redis URLs
  REDIS_HOST: "redis-0.redis.octollm.svc.cluster.local"
  REDIS_PORT: "6379"
  REDIS_DB: "0"
  REDIS_MAX_CONNECTIONS: "50"
  REDIS_SENTINEL_SERVICE: "mymaster"

  # Qdrant
  QDRANT_HOST: "qdrant-client.octollm.svc.cluster.local"
  QDRANT_PORT: "6333"
  QDRANT_GRPC_PORT: "6334"
  QDRANT_COLLECTION: "octollm_vectors"

  # Service URLs (internal)
  REFLEX_LAYER_URL: "http://reflex-layer.octollm.svc.cluster.local:8001"
  ORCHESTRATOR_URL: "http://orchestrator.octollm.svc.cluster.local:8000"
  PLANNER_ARM_URL: "http://planner-arm.octollm.svc.cluster.local:8100"
  EXECUTOR_ARM_URL: "http://executor-arm.octollm.svc.cluster.local:8101"
  CODER_ARM_URL: "http://coder-arm.octollm.svc.cluster.local:8102"
  JUDGE_ARM_URL: "http://judge-arm.octollm.svc.cluster.local:8103"
  GUARDIAN_ARM_URL: "http://guardian-arm.octollm.svc.cluster.local:8104"
  RETRIEVER_ARM_URL: "http://retriever-arm.octollm.svc.cluster.local:8105"

  # Orchestrator Settings
  TASK_TIMEOUT: "300"  # 5 minutes
  MAX_CONCURRENT_TASKS: "10"
  SWARM_ENABLED: "true"
  SWARM_SIZE: "3"

  # Rate Limiting
  RATE_LIMIT_PER_MINUTE: "100"
  RATE_LIMIT_PER_HOUR: "1000"

  # Monitoring
  METRICS_ENABLED: "true"
  METRICS_PORT: "9090"
  TRACING_ENABLED: "true"
  JAEGER_AGENT_HOST: "jaeger-agent.monitoring.svc.cluster.local"
  JAEGER_AGENT_PORT: "6831"
```

### 7. Secrets Management

```yaml
# manifests/21-secrets.yaml
# WARNING: This is an example. Use Sealed Secrets or External Secrets Operator in production!
apiVersion: v1
kind: Secret
metadata:
  name: octollm-secrets
  namespace: octollm
type: Opaque
stringData:
  # Database passwords
  POSTGRES_PASSWORD: "REPLACE_WITH_SECURE_PASSWORD"
  REDIS_PASSWORD: ""  # Empty if no password

  # LLM API Keys
  OPENAI_API_KEY: "sk-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
  ANTHROPIC_API_KEY: "sk-ant-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"

  # JWT Secret (minimum 32 characters)
  JWT_SECRET: "REPLACE_WITH_RANDOM_32_CHAR_SECRET"
  JWT_ALGORITHM: "HS256"
  JWT_EXPIRATION: "3600"  # 1 hour

  # Capability Token Secret
  CAPABILITY_SECRET: "REPLACE_WITH_ANOTHER_32_CHAR_SECRET"

  # API Keys for external services (optional)
  SLACK_WEBHOOK_URL: ""
  PAGERDUTY_SERVICE_KEY: ""
```

**Production Secret Management** (using Sealed Secrets):

```bash
# Install Sealed Secrets Controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Install kubeseal CLI
wget https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/kubeseal-0.24.0-linux-amd64.tar.gz
tar xfz kubeseal-0.24.0-linux-amd64.tar.gz
sudo install -m 755 kubeseal /usr/local/bin/kubeseal

# Seal the secrets
kubeseal --format=yaml < manifests/21-secrets.yaml > manifests/21-sealed-secrets.yaml

# Now you can safely commit manifests/21-sealed-secrets.yaml to Git
kubectl apply -f manifests/21-sealed-secrets.yaml
```

### 8. Reflex Layer Deployment

```yaml
# manifests/30-reflex-layer.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reflex-layer
  namespace: octollm
  labels:
    app: reflex-layer
    component: ingress-processing
spec:
  replicas: 3
  selector:
    matchLabels:
      app: reflex-layer
  template:
    metadata:
      labels:
        app: reflex-layer
        component: ingress-processing
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        fsGroup: 1000
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: reflex-layer
        image: octollm/reflex-layer:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8001
          name: http
          protocol: TCP
        - containerPort: 9090
          name: metrics
          protocol: TCP
        env:
        - name: PORT
          value: "8001"
        - name: METRICS_PORT
          value: "9090"
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: reflex-layer
  namespace: octollm
  labels:
    app: reflex-layer
    monitoring: "true"
spec:
  selector:
    app: reflex-layer
  ports:
  - port: 8001
    targetPort: 8001
    name: http
  - port: 9090
    targetPort: 9090
    name: metrics
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: reflex-layer-hpa
  namespace: octollm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: reflex-layer
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # 5 minutes
      policies:
      - type: Percent
        value: 50  # Scale down max 50% at a time
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0  # Scale up immediately
      policies:
      - type: Percent
        value: 100  # Double pods at a time
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Max
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: reflex-layer-pdb
  namespace: octollm
spec:
  minAvailable: 2
  selector:
    matchLabels:
      app: reflex-layer
```

### 9. Orchestrator Deployment

```yaml
# manifests/31-orchestrator.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
  namespace: octollm
  labels:
    app: orchestrator
    component: core
spec:
  replicas: 2
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
        component: core
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
        prometheus.io/path: "/metrics"
    spec:
      securityContext:
        fsGroup: 1000
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      initContainers:
      - name: wait-for-postgres
        image: postgres:15-alpine
        command:
        - sh
        - -c
        - |
          until pg_isready -h $POSTGRES_HOST -U $POSTGRES_USER; do
            echo "Waiting for PostgreSQL..."
            sleep 2
          done
          echo "PostgreSQL is ready"
        envFrom:
        - configMapRef:
            name: octollm-config
      - name: run-migrations
        image: octollm/orchestrator:latest
        command:
        - python
        - -m
        - alembic
        - upgrade
        - head
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
      containers:
      - name: orchestrator
        image: octollm/orchestrator:latest
        imagePullPolicy: IfNotPresent
        ports:
        - containerPort: 8000
          name: http
          protocol: TCP
        - containerPort: 9090
          name: metrics
          protocol: TCP
        env:
        - name: PORT
          value: "8000"
        - name: METRICS_PORT
          value: "9090"
        - name: DATABASE_URL
          value: "postgresql://$(POSTGRES_USER):$(POSTGRES_PASSWORD)@$(POSTGRES_HOST):$(POSTGRES_PORT)/$(POSTGRES_DB)"
        - name: REDIS_URL
          value: "redis://$(REDIS_HOST):$(REDIS_PORT)/$(REDIS_DB)"
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 15
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: octollm
  labels:
    app: orchestrator
    monitoring: "true"
spec:
  selector:
    app: orchestrator
  ports:
  - port: 8000
    targetPort: 8000
    name: http
  - port: 9090
    targetPort: 9090
    name: metrics
  type: ClusterIP
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orchestrator-hpa
  namespace: octollm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orchestrator
  minReplicas: 2
  maxReplicas: 8
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 75
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Pods
        value: 1
        periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Pods
        value: 2
        periodSeconds: 60
---
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata:
  name: orchestrator-pdb
  namespace: octollm
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: orchestrator
```

### 10. Arms Deployments (All 6 Arms)

```yaml
# manifests/40-planner-arm.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: planner-arm
  namespace: octollm
  labels:
    app: planner-arm
    component: arm
spec:
  replicas: 2
  selector:
    matchLabels:
      app: planner-arm
  template:
    metadata:
      labels:
        app: planner-arm
        component: arm
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      securityContext:
        fsGroup: 1000
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: planner-arm
        image: octollm/planner-arm:latest
        ports:
        - containerPort: 8100
          name: http
        - containerPort: 9090
          name: metrics
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        livenessProbe:
          httpGet:
            path: /health
            port: 8100
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8100
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: planner-arm
  namespace: octollm
  labels:
    app: planner-arm
    monitoring: "true"
spec:
  selector:
    app: planner-arm
  ports:
  - port: 8100
    targetPort: 8100
    name: http
  - port: 9090
    targetPort: 9090
    name: metrics
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: planner-arm-hpa
  namespace: octollm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: planner-arm
  minReplicas: 2
  maxReplicas: 6
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
# manifests/41-executor-arm.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: executor-arm
  namespace: octollm
  labels:
    app: executor-arm
    component: arm
spec:
  replicas: 1
  selector:
    matchLabels:
      app: executor-arm
  template:
    metadata:
      labels:
        app: executor-arm
        component: arm
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      runtimeClassName: gvisor  # Use gVisor for enhanced sandboxing
      securityContext:
        fsGroup: 1000
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: executor-arm
        image: octollm/executor-arm:latest
        ports:
        - containerPort: 8101
          name: http
        - containerPort: 9090
          name: metrics
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        resources:
          requests:
            cpu: 1000m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        livenessProbe:
          httpGet:
            path: /health
            port: 8101
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8101
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: executor-arm
  namespace: octollm
  labels:
    app: executor-arm
    monitoring: "true"
spec:
  selector:
    app: executor-arm
  ports:
  - port: 8101
    targetPort: 8101
    name: http
  - port: 9090
    targetPort: 9090
    name: metrics
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: executor-arm-hpa
  namespace: octollm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: executor-arm
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 75
---
# manifests/42-coder-arm.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: coder-arm
  namespace: octollm
  labels:
    app: coder-arm
    component: arm
spec:
  replicas: 2
  selector:
    matchLabels:
      app: coder-arm
  template:
    metadata:
      labels:
        app: coder-arm
        component: arm
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      securityContext:
        fsGroup: 1000
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: coder-arm
        image: octollm/coder-arm:latest
        ports:
        - containerPort: 8102
          name: http
        - containerPort: 9090
          name: metrics
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        livenessProbe:
          httpGet:
            path: /health
            port: 8102
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8102
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: coder-arm
  namespace: octollm
  labels:
    app: coder-arm
    monitoring: "true"
spec:
  selector:
    app: coder-arm
  ports:
  - port: 8102
    targetPort: 8102
    name: http
  - port: 9090
    targetPort: 9090
    name: metrics
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: coder-arm-hpa
  namespace: octollm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: coder-arm
  minReplicas: 2
  maxReplicas: 4
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
# manifests/43-judge-arm.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: judge-arm
  namespace: octollm
  labels:
    app: judge-arm
    component: arm
spec:
  replicas: 1
  selector:
    matchLabels:
      app: judge-arm
  template:
    metadata:
      labels:
        app: judge-arm
        component: arm
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      securityContext:
        fsGroup: 1000
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: judge-arm
        image: octollm/judge-arm:latest
        ports:
        - containerPort: 8103
          name: http
        - containerPort: 9090
          name: metrics
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        resources:
          requests:
            cpu: 500m
            memory: 512Mi
          limits:
            cpu: 1000m
            memory: 1Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        livenessProbe:
          httpGet:
            path: /health
            port: 8103
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8103
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: judge-arm
  namespace: octollm
  labels:
    app: judge-arm
    monitoring: "true"
spec:
  selector:
    app: judge-arm
  ports:
  - port: 8103
    targetPort: 8103
    name: http
  - port: 9090
    targetPort: 9090
    name: metrics
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: judge-arm-hpa
  namespace: octollm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: judge-arm
  minReplicas: 1
  maxReplicas: 3
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
# manifests/44-guardian-arm.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: guardian-arm
  namespace: octollm
  labels:
    app: guardian-arm
    component: arm
spec:
  replicas: 2
  selector:
    matchLabels:
      app: guardian-arm
  template:
    metadata:
      labels:
        app: guardian-arm
        component: arm
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      securityContext:
        fsGroup: 1000
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: guardian-arm
        image: octollm/guardian-arm:latest
        ports:
        - containerPort: 8104
          name: http
        - containerPort: 9090
          name: metrics
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        resources:
          requests:
            cpu: 200m
            memory: 512Mi
          limits:
            cpu: 500m
            memory: 1Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        livenessProbe:
          httpGet:
            path: /health
            port: 8104
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8104
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: guardian-arm
  namespace: octollm
  labels:
    app: guardian-arm
    monitoring: "true"
spec:
  selector:
    app: guardian-arm
  ports:
  - port: 8104
    targetPort: 8104
    name: http
  - port: 9090
    targetPort: 9090
    name: metrics
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: guardian-arm-hpa
  namespace: octollm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: guardian-arm
  minReplicas: 2
  maxReplicas: 4
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
---
# manifests/45-retriever-arm.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: retriever-arm
  namespace: octollm
  labels:
    app: retriever-arm
    component: arm
spec:
  replicas: 2
  selector:
    matchLabels:
      app: retriever-arm
  template:
    metadata:
      labels:
        app: retriever-arm
        component: arm
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      securityContext:
        fsGroup: 1000
        runAsNonRoot: true
        runAsUser: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: retriever-arm
        image: octollm/retriever-arm:latest
        ports:
        - containerPort: 8105
          name: http
        - containerPort: 9090
          name: metrics
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
          capabilities:
            drop:
            - ALL
        livenessProbe:
          httpGet:
            path: /health
            port: 8105
          initialDelaySeconds: 15
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8105
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: tmp
        emptyDir: {}
---
apiVersion: v1
kind: Service
metadata:
  name: retriever-arm
  namespace: octollm
  labels:
    app: retriever-arm
    monitoring: "true"
spec:
  selector:
    app: retriever-arm
  ports:
  - port: 8105
    targetPort: 8105
    name: http
  - port: 9090
    targetPort: 9090
    name: metrics
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: retriever-arm-hpa
  namespace: octollm
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: retriever-arm
  minReplicas: 2
  maxReplicas: 4
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

Due to character limits, I'll continue this comprehensive deployment guide in the next response. The guide will include:

- Network Policies (Section 11)
- Ingress Configuration with TLS (Section 12)
- RBAC Configuration (Section 13)
- Monitoring ServiceMonitors (Section 14)
- Helm Chart Structure (Section 15)
- Deployment Procedures (Section 16)
- Verification Scripts (Section 17)
- Troubleshooting (Section 18)

### 11. Network Policies (Zero-Trust Security)

```yaml
# manifests/50-network-policies.yaml
---
# Default: Deny all traffic
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: octollm
spec:
  podSelector: {}
  policyTypes:
    - Ingress
    - Egress

---
# Allow Reflex Layer to receive ingress traffic from ingress controller
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: reflex-layer-ingress
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: reflex-layer
  policyTypes:
    - Ingress
  ingress:
    # Allow from ingress controller
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8001
    # Allow from orchestrator for health checks
    - from:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 8001

---
# Allow Reflex Layer egress to Orchestrator and Redis
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: reflex-layer-egress
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: reflex-layer
  policyTypes:
    - Egress
  egress:
    # Allow to Orchestrator
    - to:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 8000
    # Allow to Redis
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
        - podSelector:
            matchLabels:
              k8s-app: kube-dns
      ports:
        - protocol: UDP
          port: 53

---
# Allow Orchestrator to communicate with all arms
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: orchestrator-to-arms
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      component: arm
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 8100  # Planner
        - protocol: TCP
          port: 8101  # Executor
        - protocol: TCP
          port: 8102  # Coder
        - protocol: TCP
          port: 8103  # Judge
        - protocol: TCP
          port: 8104  # Guardian
        - protocol: TCP
          port: 8105  # Retriever

---
# Allow Orchestrator egress to arms, databases, and LLM APIs
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: orchestrator-egress
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: orchestrator
  policyTypes:
    - Egress
  egress:
    # Allow to all arms
    - to:
        - podSelector:
            matchLabels:
              component: arm
      ports:
        - protocol: TCP
          port: 8100
        - protocol: TCP
          port: 8101
        - protocol: TCP
          port: 8102
        - protocol: TCP
          port: 8103
        - protocol: TCP
          port: 8104
        - protocol: TCP
          port: 8105
    # Allow to PostgreSQL
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    # Allow to Redis
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379
    # Allow to Qdrant
    - to:
        - podSelector:
            matchLabels:
              app: qdrant
      ports:
        - protocol: TCP
          port: 6333
        - protocol: TCP
          port: 6334
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
    # Allow external HTTPS (LLM APIs)
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 443

---
# Allow all services to access PostgreSQL
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-postgres-access
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: postgres
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              needs-db: "true"
      ports:
        - protocol: TCP
          port: 5432
    # Allow from orchestrator
    - from:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 5432

---
# Allow all services to access Redis
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-redis-access
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: redis
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              needs-cache: "true"
      ports:
        - protocol: TCP
          port: 6379
    # Allow from reflex layer
    - from:
        - podSelector:
            matchLabels:
              app: reflex-layer
      ports:
        - protocol: TCP
          port: 6379
    # Allow from orchestrator
    - from:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 6379
    # Allow from guardian (for PII cache)
    - from:
        - podSelector:
            matchLabels:
              app: guardian-arm
      ports:
        - protocol: TCP
          port: 6379

---
# Allow retriever arm to access Qdrant
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-qdrant-access
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: qdrant
  policyTypes:
    - Ingress
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: retriever-arm
      ports:
        - protocol: TCP
          port: 6333
        - protocol: TCP
          port: 6334
    # Allow from coder arm (for code context)
    - from:
        - podSelector:
            matchLabels:
              app: coder-arm
      ports:
        - protocol: TCP
          port: 6333
    # Allow from orchestrator
    - from:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 6333

---
# Arms egress policies - different for each arm type
# Executor Arm: Restricted egress (most sensitive)
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: executor-arm-egress
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: executor-arm
  policyTypes:
    - Egress
  egress:
    # ONLY allow communication with orchestrator
    - to:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 8000
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
    # Explicitly NO external egress (sandboxed execution only)

---
# Planner Arm egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: planner-arm-egress
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: planner-arm
  policyTypes:
    - Egress
  egress:
    # Allow to orchestrator
    - to:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 8000
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
    # Allow external HTTPS for LLM API
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 443

---
# Coder Arm egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: coder-arm-egress
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: coder-arm
  policyTypes:
    - Egress
  egress:
    # Allow to Qdrant
    - to:
        - podSelector:
            matchLabels:
              app: qdrant
      ports:
        - protocol: TCP
          port: 6333
    # Allow to orchestrator
    - to:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 8000
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
    # Allow external HTTPS
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 443

---
# Judge Arm egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: judge-arm-egress
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: judge-arm
  policyTypes:
    - Egress
  egress:
    # Allow to orchestrator
    - to:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 8000
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53
    # Allow external HTTPS
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 443

---
# Guardian Arm egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: guardian-arm-egress
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: guardian-arm
  policyTypes:
    - Egress
  egress:
    # Allow to Redis (PII cache)
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379
    # Allow to orchestrator
    - to:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 8000
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53

---
# Retriever Arm egress
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: retriever-arm-egress
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: retriever-arm
  policyTypes:
    - Egress
  egress:
    # Allow to Qdrant
    - to:
        - podSelector:
            matchLabels:
              app: qdrant
      ports:
        - protocol: TCP
          port: 6333
        - protocol: TCP
          port: 6334
    # Allow to PostgreSQL
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    # Allow to orchestrator
    - to:
        - podSelector:
            matchLabels:
              app: orchestrator
      ports:
        - protocol: TCP
          port: 8000
    # Allow DNS
    - to:
        - namespaceSelector:
            matchLabels:
              name: kube-system
      ports:
        - protocol: UDP
          port: 53

---
# Allow monitoring namespace to scrape metrics
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-monitoring
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      monitoring: "true"
  policyTypes:
    - Ingress
  ingress:
    - from:
        - namespaceSelector:
            matchLabels:
              name: monitoring
      ports:
        - protocol: TCP
          port: 9090  # Metrics port
```

#### Network Policy Strategy

**Zero-Trust Architecture**:
1. **Default Deny**: All traffic is blocked by default
2. **Explicit Allow**: Only necessary communications are permitted
3. **Least Privilege**: Each component gets minimal necessary network access
4. **Defense in Depth**: Multiple layers of network isolation

**Security Zones**:
```
Zone 1 (Public): Ingress Controller
  ↓ (HTTPS only)
Zone 2 (DMZ): Reflex Layer
  ↓ (Internal only)
Zone 3 (Application): Orchestrator + Arms
  ↓ (Internal only)
Zone 4 (Data): PostgreSQL, Redis, Qdrant
  ↑ (Controlled access)
Zone 5 (Monitoring): Prometheus, Grafana
```

**Traffic Flow Rules**:
- **Ingress → Reflex Layer**: External HTTPS traffic
- **Reflex → Orchestrator**: Preprocessed requests
- **Orchestrator → Arms**: Task delegation
- **Arms → Databases**: Data access (selective)
- **Arms → External**: HTTPS for LLM APIs (except Executor)
- **Monitoring → All**: Metrics scraping on port 9090

**Testing Network Policies**:

```bash
# Verify network policies are created
kubectl get networkpolicies -n octollm

# Test connectivity between pods
# 1. Create test pod
kubectl run test-pod -n octollm --image=nicolaka/netshoot --rm -it -- /bin/bash

# 2. Inside test pod, try connections
# Should succeed: DNS lookup
nslookup postgres.octollm.svc.cluster.local

# Should fail: Direct connection (no policy allows test-pod)
curl http://postgres:5432

# 3. Test from orchestrator pod
kubectl exec -n octollm deploy/orchestrator -it -- /bin/bash
# Should succeed
curl http://planner-arm:8100/health
# Should succeed
psql -h postgres -U octollm -c "SELECT 1"

# 4. Test from executor arm
kubectl exec -n octollm deploy/executor-arm -it -- /bin/bash
# Should succeed
curl http://orchestrator:8000/health
# Should FAIL (no external egress allowed)
curl https://api.openai.com

# Cleanup
kubectl delete pod test-pod -n octollm
```

**Network Policy Monitoring**:

```bash
# Monitor policy violations (if using Cilium)
kubectl logs -n kube-system -l k8s-app=cilium | grep "Policy denied"

# View policy audit logs
kubectl get events -n octollm --field-selector reason=NetworkPolicyViolation
```

**Common Issues**:

1. **DNS Resolution Fails**
   - Ensure DNS egress is allowed to `kube-system` namespace
   - Check CoreDNS/kube-dns is running: `kubectl get pods -n kube-system`

2. **Database Connection Timeout**
   - Verify database pods have correct labels (`app: postgres`)
   - Check policy allows ingress from orchestrator/arms

3. **LLM API Calls Fail**
   - Ensure HTTPS egress (port 443) is allowed for arms that need it
   - Executor arm intentionally blocks external egress

4. **Monitoring Breaks**
   - Add `monitoring: "true"` label to service definitions
   - Verify monitoring namespace has correct label

---

### 12. Ingress Configuration with TLS

This section configures HTTPS ingress with automatic TLS certificate management using cert-manager and Let's Encrypt.

#### 12.1 Install cert-manager

```bash
# Install cert-manager CRDs
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.crds.yaml

# Create cert-manager namespace
kubectl create namespace cert-manager

# Install cert-manager using Helm
helm repo add jetstack https://charts.jetstack.io
helm repo update

helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager \
  --version v1.13.0 \
  --set installCRDs=false \
  --set prometheus.enabled=true

# Verify installation
kubectl get pods -n cert-manager
# Expected: 3 pods running (cert-manager, webhook, cainjector)
```

#### 12.2 Configure ClusterIssuers

```yaml
# manifests/60-cert-manager.yaml
---
# Production Let's Encrypt Issuer
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    # Production ACME server
    server: https://acme-v02.api.letsencrypt.org/directory

    # Email for renewal notifications
    email: admin@octollm.io

    # Secret to store account private key
    privateKeySecretRef:
      name: letsencrypt-prod

    # HTTP-01 challenge solver
    solvers:
      - http01:
          ingress:
            class: nginx

---
# Staging Let's Encrypt Issuer (for testing)
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-staging
spec:
  acme:
    # Staging ACME server (higher rate limits)
    server: https://acme-staging-v02.api.letsencrypt.org/directory

    email: admin@octollm.io

    privateKeySecretRef:
      name: letsencrypt-staging

    solvers:
      - http01:
          ingress:
            class: nginx

---
# Self-Signed Issuer (for development)
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned
spec:
  selfSigned: {}
```

**Apply ClusterIssuers**:
```bash
kubectl apply -f manifests/60-cert-manager.yaml

# Verify ClusterIssuers are ready
kubectl get clusterissuers
# Expected: letsencrypt-prod and letsencrypt-staging READY=True
```

#### 12.3 Create Certificate Resource

```yaml
# manifests/61-certificate.yaml
---
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: octollm-tls
  namespace: octollm
spec:
  # Secret where certificate will be stored
  secretName: octollm-tls-secret

  # Reference to ClusterIssuer
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
    group: cert-manager.io

  # Domain names for certificate
  dnsNames:
    - api.octollm.io
    - octollm.io
    - www.octollm.io

  # Certificate usage
  usages:
    - digital signature
    - key encipherment
    - server auth

  # Renew certificate 30 days before expiry
  renewBefore: 720h  # 30 days

  # Private key configuration
  privateKey:
    algorithm: RSA
    encoding: PKCS1
    size: 2048
    rotationPolicy: Always
```

**Apply Certificate**:
```bash
kubectl apply -f manifests/61-certificate.yaml

# Monitor certificate issuance
kubectl get certificate -n octollm
kubectl describe certificate octollm-tls -n octollm

# Check certificate ready status
kubectl get certificate octollm-tls -n octollm -o jsonpath='{.status.conditions[?(@.type=="Ready")].status}'
# Expected: True

# Verify secret was created
kubectl get secret octollm-tls-secret -n octollm
```

#### 12.4 Install NGINX Ingress Controller

```bash
# Install NGINX Ingress Controller using Helm
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.metrics.enabled=true \
  --set controller.metrics.serviceMonitor.enabled=true \
  --set controller.podAnnotations."prometheus\.io/scrape"=true \
  --set controller.podAnnotations."prometheus\.io/port"="10254" \
  --set controller.service.type=LoadBalancer \
  --set controller.service.annotations."service\.beta\.kubernetes\.io/aws-load-balancer-type"="nlb" \
  --set controller.config.use-forwarded-headers="true" \
  --set controller.config.compute-full-forwarded-for="true" \
  --set controller.config.use-proxy-protocol="false"

# Verify installation
kubectl get pods -n ingress-nginx
kubectl get svc -n ingress-nginx

# Get LoadBalancer external IP
kubectl get svc ingress-nginx-controller -n ingress-nginx -o jsonpath='{.status.loadBalancer.ingress[0].hostname}'
```

**Configure DNS**:
```bash
# Point your DNS records to the LoadBalancer IP/hostname
# A record: api.octollm.io → LoadBalancer IP
# A record: octollm.io → LoadBalancer IP
# CNAME: www.octollm.io → octollm.io
```

#### 12.5 Create Ingress Resource

```yaml
# manifests/62-ingress.yaml
---
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: octollm-ingress
  namespace: octollm
  annotations:
    # TLS Configuration
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"

    # Rate Limiting
    nginx.ingress.kubernetes.io/limit-rps: "100"
    nginx.ingress.kubernetes.io/limit-connections: "50"
    nginx.ingress.kubernetes.io/limit-whitelist: ""
    nginx.ingress.kubernetes.io/limit-burst-multiplier: "5"

    # CORS Configuration
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://octollm.io, https://www.octollm.io"
    nginx.ingress.kubernetes.io/cors-allow-methods: "GET, POST, PUT, DELETE, OPTIONS"
    nginx.ingress.kubernetes.io/cors-allow-headers: "Authorization, Content-Type, X-Request-ID"
    nginx.ingress.kubernetes.io/cors-expose-headers: "X-Request-ID, X-RateLimit-Remaining"
    nginx.ingress.kubernetes.io/cors-allow-credentials: "true"
    nginx.ingress.kubernetes.io/cors-max-age: "3600"

    # Security Headers
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-XSS-Protection: 1; mode=block";
      more_set_headers "Strict-Transport-Security: max-age=31536000; includeSubDomains; preload";
      more_set_headers "Referrer-Policy: strict-origin-when-cross-origin";
      more_set_headers "Permissions-Policy: geolocation=(), microphone=(), camera=()";
      more_set_headers "Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'";

    # Request Size Limits
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/client-body-buffer-size: "1m"

    # Timeouts
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "30"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "120"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
    nginx.ingress.kubernetes.io/proxy-next-upstream-timeout: "120"

    # Load Balancing
    nginx.ingress.kubernetes.io/upstream-hash-by: "$remote_addr"
    nginx.ingress.kubernetes.io/load-balance: "ewma"  # Exponentially weighted moving average

    # Monitoring
    nginx.ingress.kubernetes.io/enable-access-log: "true"
    nginx.ingress.kubernetes.io/enable-rewrite-log: "false"
spec:
  ingressClassName: nginx

  # TLS configuration
  tls:
    - hosts:
        - api.octollm.io
        - octollm.io
        - www.octollm.io
      secretName: octollm-tls-secret

  # Routing rules
  rules:
    # Main API endpoint
    - host: api.octollm.io
      http:
        paths:
          # All requests go to reflex layer first
          - path: /
            pathType: Prefix
            backend:
              service:
                name: reflex-layer
                port:
                  number: 8001

    # Root domain redirect
    - host: octollm.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: reflex-layer
                port:
                  number: 8001

    # WWW subdomain
    - host: www.octollm.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: reflex-layer
                port:
                  number: 8001

---
# Separate ingress for direct orchestrator access (admin only)
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: octollm-admin-ingress
  namespace: octollm
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"

    # Strict rate limiting for admin
    nginx.ingress.kubernetes.io/limit-rps: "10"
    nginx.ingress.kubernetes.io/limit-connections: "5"

    # IP whitelist (replace with your admin IPs)
    nginx.ingress.kubernetes.io/whitelist-source-range: "10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16"

    # Basic auth (optional)
    nginx.ingress.kubernetes.io/auth-type: basic
    nginx.ingress.kubernetes.io/auth-secret: octollm-admin-auth
    nginx.ingress.kubernetes.io/auth-realm: "OctoLLM Administration"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - admin.octollm.io
      secretName: octollm-tls-secret
  rules:
    - host: admin.octollm.io
      http:
        paths:
          # Direct orchestrator access
          - path: /orchestrator
            pathType: Prefix
            backend:
              service:
                name: orchestrator
                port:
                  number: 8000

          # Metrics endpoints
          - path: /metrics
            pathType: Prefix
            backend:
              service:
                name: orchestrator
                port:
                  number: 9090
```

**Apply Ingress**:
```bash
kubectl apply -f manifests/62-ingress.yaml

# Verify ingress is configured
kubectl get ingress -n octollm
kubectl describe ingress octollm-ingress -n octollm
```

#### 12.6 Create Basic Auth Secret (for admin ingress)

```bash
# Install htpasswd tool
sudo apt-get install apache2-utils  # Debian/Ubuntu
# or
brew install httpd  # macOS

# Create htpasswd file
htpasswd -c auth admin
# Enter password when prompted

# Create secret
kubectl create secret generic octollm-admin-auth \
  --from-file=auth \
  -n octollm

# Verify secret
kubectl get secret octollm-admin-auth -n octollm
```

#### 12.7 Testing Ingress and TLS

```bash
# Test HTTP redirect to HTTPS
curl -I http://api.octollm.io
# Expected: HTTP 308 Permanent Redirect to https://

# Test HTTPS endpoint
curl -v https://api.octollm.io/health
# Expected: HTTP 200 OK with valid TLS certificate

# Verify certificate details
openssl s_client -connect api.octollm.io:443 -servername api.octollm.io < /dev/null 2>&1 | openssl x509 -noout -text
# Expected: Certificate issued by Let's Encrypt

# Test rate limiting
for i in {1..150}; do curl -s -o /dev/null -w "%{http_code}\n" https://api.octollm.io/health; done
# Expected: First 100 return 200, then 429 Too Many Requests

# Test CORS headers
curl -I -H "Origin: https://octollm.io" https://api.octollm.io/health
# Expected: Access-Control-Allow-Origin header present

# Test security headers
curl -I https://api.octollm.io/health | grep -E "X-Frame-Options|X-Content-Type-Options|Strict-Transport-Security"
# Expected: All security headers present
```

#### 12.8 Certificate Renewal

cert-manager automatically renews certificates 30 days before expiry. To manually trigger renewal:

```bash
# Delete certificate secret (cert-manager will recreate)
kubectl delete secret octollm-tls-secret -n octollm

# Force certificate reissuance
kubectl delete certificate octollm-tls -n octollm
kubectl apply -f manifests/61-certificate.yaml

# Monitor renewal
kubectl get certificate octollm-tls -n octollm -w

# Check certificate expiry
kubectl get secret octollm-tls-secret -n octollm -o jsonpath='{.data.tls\.crt}' | base64 -d | openssl x509 -noout -enddate
```

#### 12.9 Troubleshooting TLS Issues

**Issue: Certificate not issuing**

```bash
# Check certificate status
kubectl describe certificate octollm-tls -n octollm

# Check certificate request
kubectl get certificaterequest -n octollm
kubectl describe certificaterequest $(kubectl get certificaterequest -n octollm -o name | head -1) -n octollm

# Check ACME challenges
kubectl get challenges -n octollm
kubectl describe challenge $(kubectl get challenges -n octollm -o name | head -1) -n octollm

# Check cert-manager logs
kubectl logs -n cert-manager -l app=cert-manager --tail=100

# Common issues:
# 1. DNS not pointing to LoadBalancer - verify with: dig api.octollm.io
# 2. Ingress not accessible - test: curl http://api.octollm.io/.well-known/acme-challenge/test
# 3. Rate limit hit - use staging issuer for testing
```

**Issue: Browser shows certificate error**

```bash
# Verify certificate is valid
openssl s_client -connect api.octollm.io:443 -servername api.octollm.io < /dev/null

# Check if using staging certificate (not trusted)
kubectl get certificate octollm-tls -n octollm -o jsonpath='{.spec.issuerRef.name}'
# Should be: letsencrypt-prod (not letsencrypt-staging)

# If using staging, switch to production
kubectl delete certificate octollm-tls -n octollm
# Edit manifests/61-certificate.yaml to use letsencrypt-prod
kubectl apply -f manifests/61-certificate.yaml
```

**Issue: Rate limit errors from Let's Encrypt**

```bash
# Let's Encrypt rate limits:
# - 50 certificates per domain per week
# - 5 duplicate certificates per week

# Solution: Use staging issuer for testing
kubectl patch certificate octollm-tls -n octollm \
  --type merge \
  -p '{"spec":{"issuerRef":{"name":"letsencrypt-staging"}}}'

# Wait 24 hours, then switch back to production
```

#### 12.10 Advanced Ingress Configuration

**IP Whitelisting** (for production environments):

```yaml
# Add to ingress annotations
nginx.ingress.kubernetes.io/whitelist-source-range: "203.0.113.0/24, 198.51.100.0/24"
```

**Custom Error Pages**:

```yaml
# Add to ingress annotations
nginx.ingress.kubernetes.io/default-backend: custom-error-pages
nginx.ingress.kubernetes.io/custom-http-errors: "404,503"
```

**Request Buffering** (for large payloads):

```yaml
# Add to ingress annotations
nginx.ingress.kubernetes.io/proxy-buffering: "on"
nginx.ingress.kubernetes.io/proxy-buffers-number: "4"
nginx.ingress.kubernetes.io/proxy-buffer-size: "8k"
```

**Canary Deployments**:

```yaml
# Create separate ingress for canary traffic
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: octollm-ingress-canary
  namespace: octollm
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"  # 10% of traffic
spec:
  ingressClassName: nginx
  rules:
    - host: api.octollm.io
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: reflex-layer-canary
                port:
                  number: 8001
```

---

### 13. RBAC Configuration (Role-Based Access Control)

This section configures fine-grained access control for OctoLLM components following the principle of least privilege.

#### 13.1 ServiceAccounts

```yaml
# manifests/70-rbac-serviceaccounts.yaml
---
# ServiceAccount for Orchestrator
apiVersion: v1
kind: ServiceAccount
metadata:
  name: orchestrator
  namespace: octollm
  labels:
    app: orchestrator
    component: core
automountServiceAccountToken: true

---
# ServiceAccount for Reflex Layer
apiVersion: v1
kind: ServiceAccount
metadata:
  name: reflex-layer
  namespace: octollm
  labels:
    app: reflex-layer
    component: ingress-processing
automountServiceAccountToken: true

---
# ServiceAccount for all Arms (shared)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: arm-service-account
  namespace: octollm
  labels:
    component: arm
automountServiceAccountToken: true

---
# ServiceAccount for Tool Executor Arm (most restricted)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: executor-arm
  namespace: octollm
  labels:
    app: executor-arm
    component: arm
    security-level: high
automountServiceAccountToken: false  # No K8s API access

---
# ServiceAccount for database pods
apiVersion: v1
kind: ServiceAccount
metadata:
  name: database-sa
  namespace: octollm
  labels:
    component: data
automountServiceAccountToken: false

---
# ServiceAccount for monitoring/maintenance jobs
apiVersion: v1
kind: ServiceAccount
metadata:
  name: maintenance
  namespace: octollm
  labels:
    component: maintenance
automountServiceAccountToken: true
```

#### 13.2 Roles

```yaml
# manifests/71-rbac-roles.yaml
---
# Role for Orchestrator - needs to list pods and read configs
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: orchestrator-role
  namespace: octollm
rules:
  # Read pods for health checks and arm discovery
  - apiGroups: [""]
    resources: ["pods", "pods/log"]
    verbs: ["get", "list", "watch"]

  # Read services for service discovery
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["get", "list"]

  # Read ConfigMaps for configuration
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get", "list"]

  # Read deployments for scaling decisions
  - apiGroups: ["apps"]
    resources: ["deployments"]
    verbs: ["get", "list"]

  # Read HPA status
  - apiGroups: ["autoscaling"]
    resources: ["horizontalpodautoscalers"]
    verbs: ["get", "list"]

  # Create/update ConfigMaps for dynamic configuration
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["create", "update", "patch"]
    resourceNames: ["octollm-dynamic-config"]

---
# Role for Reflex Layer - minimal permissions
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: reflex-layer-role
  namespace: octollm
rules:
  # Read ConfigMaps only
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get"]
    resourceNames: ["octollm-config"]

  # Read services for routing
  - apiGroups: [""]
    resources: ["services"]
    verbs: ["get"]

---
# Role for Arms - read-only access to configs and secrets
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: arm-role
  namespace: octollm
rules:
  # Read ConfigMaps
  - apiGroups: [""]
    resources: ["configmaps"]
    verbs: ["get"]

  # Read specific secrets only
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get"]
    resourceNames:
      - "octollm-secrets"
      - "octollm-api-keys"

---
# Role for Maintenance Jobs - backup, migrations, etc.
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: maintenance-role
  namespace: octollm
rules:
  # Full access to pods for debugging
  - apiGroups: [""]
    resources: ["pods", "pods/log", "pods/exec"]
    verbs: ["get", "list", "create", "delete"]

  # Access to jobs
  - apiGroups: ["batch"]
    resources: ["jobs", "cronjobs"]
    verbs: ["get", "list", "create", "delete", "update", "patch"]

  # Access to PVCs for backups
  - apiGroups: [""]
    resources: ["persistentvolumeclaims"]
    verbs: ["get", "list"]

  # Read secrets for database credentials
  - apiGroups: [""]
    resources: ["secrets"]
    verbs: ["get"]

---
# ClusterRole for monitoring (cross-namespace metrics)
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: octollm-monitoring
rules:
  # Read pods across all namespaces for metrics
  - apiGroups: [""]
    resources: ["pods", "services", "endpoints"]
    verbs: ["get", "list", "watch"]

  # Read nodes for cluster metrics
  - apiGroups: [""]
    resources: ["nodes", "nodes/metrics"]
    verbs: ["get", "list"]
```

#### 13.3 RoleBindings

```yaml
# manifests/72-rbac-rolebindings.yaml
---
# Bind orchestrator-role to orchestrator ServiceAccount
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: orchestrator-rolebinding
  namespace: octollm
subjects:
  - kind: ServiceAccount
    name: orchestrator
    namespace: octollm
roleRef:
  kind: Role
  name: orchestrator-role
  apiGroup: rbac.authorization.k8s.io

---
# Bind reflex-layer-role to reflex-layer ServiceAccount
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: reflex-layer-rolebinding
  namespace: octollm
subjects:
  - kind: ServiceAccount
    name: reflex-layer
    namespace: octollm
roleRef:
  kind: Role
  name: reflex-layer-role
  apiGroup: rbac.authorization.k8s.io

---
# Bind arm-role to arm-service-account
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: arm-rolebinding
  namespace: octollm
subjects:
  - kind: ServiceAccount
    name: arm-service-account
    namespace: octollm
roleRef:
  kind: Role
  name: arm-role
  apiGroup: rbac.authorization.k8s.io

---
# Bind maintenance-role to maintenance ServiceAccount
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: maintenance-rolebinding
  namespace: octollm
subjects:
  - kind: ServiceAccount
    name: maintenance
    namespace: octollm
roleRef:
  kind: Role
  name: maintenance-role
  apiGroup: rbac.authorization.k8s.io

---
# ClusterRoleBinding for monitoring
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: octollm-monitoring-binding
subjects:
  - kind: ServiceAccount
    name: prometheus
    namespace: monitoring
roleRef:
  kind: ClusterRole
  name: octollm-monitoring
  apiGroup: rbac.authorization.k8s.io
```

#### 13.4 Update Deployments to Use ServiceAccounts

Update existing deployment manifests to use the appropriate ServiceAccounts:

**Orchestrator** (add to spec.template.spec):
```yaml
spec:
  template:
    spec:
      serviceAccountName: orchestrator
      automountServiceAccountToken: true
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
```

**Reflex Layer** (add to spec.template.spec):
```yaml
spec:
  template:
    spec:
      serviceAccountName: reflex-layer
      automountServiceAccountToken: true
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
```

**Arms** (add to spec.template.spec for planner, coder, judge, guardian, retriever):
```yaml
spec:
  template:
    spec:
      serviceAccountName: arm-service-account
      automountServiceAccountToken: true
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
```

**Executor Arm** (special case - no K8s API access):
```yaml
spec:
  template:
    spec:
      serviceAccountName: executor-arm
      automountServiceAccountToken: false  # Explicitly disabled
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        readOnlyRootFilesystem: true
```

#### 13.5 Apply RBAC Configuration

```bash
# Apply all RBAC manifests
kubectl apply -f manifests/70-rbac-serviceaccounts.yaml
kubectl apply -f manifests/71-rbac-roles.yaml
kubectl apply -f manifests/72-rbac-rolebindings.yaml

# Verify ServiceAccounts
kubectl get serviceaccounts -n octollm

# Verify Roles
kubectl get roles -n octollm
kubectl describe role orchestrator-role -n octollm

# Verify RoleBindings
kubectl get rolebindings -n octollm
kubectl describe rolebinding orchestrator-rolebinding -n octollm

# Verify ClusterRoles and ClusterRoleBindings
kubectl get clusterroles | grep octollm
kubectl get clusterrolebindings | grep octollm
```

#### 13.6 Testing RBAC Permissions

**Test Orchestrator Permissions**:

```bash
# Create test pod using orchestrator ServiceAccount
kubectl run rbac-test-orchestrator \
  --image=bitnami/kubectl:latest \
  --restart=Never \
  --serviceaccount=orchestrator \
  -n octollm \
  -- sleep infinity

# Test allowed operations
kubectl exec -n octollm rbac-test-orchestrator -- kubectl get pods -n octollm
# Expected: Success

kubectl exec -n octollm rbac-test-orchestrator -- kubectl get services -n octollm
# Expected: Success

kubectl exec -n octollm rbac-test-orchestrator -- kubectl get configmaps -n octollm
# Expected: Success

# Test denied operations
kubectl exec -n octollm rbac-test-orchestrator -- kubectl delete pods -n octollm --all
# Expected: Error (forbidden)

kubectl exec -n octollm rbac-test-orchestrator -- kubectl get secrets -n octollm
# Expected: Error (forbidden)

# Cleanup
kubectl delete pod rbac-test-orchestrator -n octollm
```

**Test Arm Permissions**:

```bash
# Create test pod using arm ServiceAccount
kubectl run rbac-test-arm \
  --image=bitnami/kubectl:latest \
  --restart=Never \
  --serviceaccount=arm-service-account \
  -n octollm \
  -- sleep infinity

# Test allowed operations
kubectl exec -n octollm rbac-test-arm -- kubectl get configmap octollm-config -n octollm
# Expected: Success

kubectl exec -n octollm rbac-test-arm -- kubectl get secret octollm-secrets -n octollm
# Expected: Success

# Test denied operations
kubectl exec -n octollm rbac-test-arm -- kubectl get pods -n octollm
# Expected: Error (forbidden)

kubectl exec -n octollm rbac-test-arm -- kubectl delete secret octollm-secrets -n octollm
# Expected: Error (forbidden)

# Cleanup
kubectl delete pod rbac-test-arm -n octollm
```

**Test Executor Arm Isolation** (should have NO K8s API access):

```bash
# Create test pod using executor-arm ServiceAccount
kubectl run rbac-test-executor \
  --image=bitnami/kubectl:latest \
  --restart=Never \
  --serviceaccount=executor-arm \
  -n octollm \
  -- sleep infinity

# Test that ALL operations are denied
kubectl exec -n octollm rbac-test-executor -- kubectl get pods -n octollm
# Expected: Error (forbidden - no ServiceAccount token mounted)

kubectl exec -n octollm rbac-test-executor -- kubectl auth can-i --list -n octollm
# Expected: Error (cannot access K8s API)

# Cleanup
kubectl delete pod rbac-test-executor -n octollm
```

#### 13.7 RBAC Best Practices

**Principle of Least Privilege**:
1. **Orchestrator**: Read-only access to cluster state, limited write to dynamic configs
2. **Reflex Layer**: Minimal access (only read configs for routing)
3. **Arms**: Read-only access to configs and secrets
4. **Executor Arm**: NO Kubernetes API access (most dangerous component)
5. **Databases**: NO Kubernetes API access (not needed)

**Security Layers**:
```
Layer 1: Network Policies (prevent network access)
Layer 2: RBAC (prevent K8s API access)
Layer 3: Pod Security Standards (prevent privileged containers)
Layer 4: Seccomp/AppArmor (prevent syscall abuse)
```

**Audit Logging**:

Enable Kubernetes audit logging to track RBAC violations:

```yaml
# Add to kube-apiserver configuration
apiVersion: audit.k8s.io/v1
kind: Policy
rules:
  # Log RBAC authorization failures
  - level: Metadata
    omitStages:
      - RequestReceived
    verbs: ["*"]
    resources:
      - group: ""
        resources: ["*"]
    namespaces: ["octollm"]

  # Log Secret access
  - level: Metadata
    resources:
      - group: ""
        resources: ["secrets"]
    namespaces: ["octollm"]
```

**Monitor RBAC Events**:

```bash
# Watch for RBAC authorization failures
kubectl get events -n octollm --field-selector reason=Forbidden -w

# Check audit logs (if enabled)
kubectl logs -n kube-system kube-apiserver-<node> | grep "forbidden"

# List all ServiceAccounts and their permissions
kubectl get serviceaccounts -n octollm -o custom-columns=NAME:.metadata.name,AUTOMOUNT:.automountServiceAccountToken
```

#### 13.8 Troubleshooting RBAC Issues

**Issue: Pod cannot access K8s API**

```bash
# Check if ServiceAccount is correctly set
kubectl get pod <pod-name> -n octollm -o jsonpath='{.spec.serviceAccountName}'

# Check if token is mounted
kubectl exec -n octollm <pod-name> -- ls /var/run/secrets/kubernetes.io/serviceaccount/

# Check ServiceAccount exists
kubectl get serviceaccount <sa-name> -n octollm

# Check RoleBinding exists
kubectl get rolebinding -n octollm | grep <sa-name>
```

**Issue: Permission denied errors**

```bash
# Test what a ServiceAccount can do
kubectl auth can-i --list --as=system:serviceaccount:octollm:orchestrator -n octollm

# Test specific permission
kubectl auth can-i get pods --as=system:serviceaccount:octollm:orchestrator -n octollm

# Check Role/RoleBinding configuration
kubectl describe role orchestrator-role -n octollm
kubectl describe rolebinding orchestrator-rolebinding -n octollm
```

**Issue: Too permissive access**

```bash
# Audit all Roles for excessive permissions
kubectl get roles -n octollm -o yaml | grep -A 10 "verbs:"

# Check for wildcard permissions (dangerous)
kubectl get roles -n octollm -o yaml | grep -E "verbs:.*\*"

# List all ClusterRoles (can affect entire cluster)
kubectl get clusterroles | grep octollm
```

---
