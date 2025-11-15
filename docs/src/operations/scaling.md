# OctoLLM Scaling Guide: Comprehensive Auto-Scaling and Performance Optimization

**Version**: 1.0
**Last Updated**: 2025-11-10
**Estimated Time**: 3-4 hours
**Difficulty**: Advanced
**Target**: Production-grade horizontal and vertical scaling

## Table of Contents

1. [Overview](#overview)
2. [Scaling Strategies](#scaling-strategies)
3. [Horizontal Pod Autoscaling (HPA)](#horizontal-pod-autoscaling-hpa)
4. [Vertical Pod Autoscaling (VPA)](#vertical-pod-autoscaling-vpa)
5. [Cluster Autoscaling](#cluster-autoscaling)
6. [Database Scaling](#database-scaling)
7. [Caching Strategies](#caching-strategies)
8. [Load Testing](#load-testing)
9. [Cost Optimization](#cost-optimization)
10. [Performance Monitoring](#performance-monitoring)
11. [Troubleshooting](#troubleshooting)

---

## Overview

This guide provides comprehensive scaling strategies for OctoLLM, covering horizontal scaling (adding more pods), vertical scaling (increasing pod resources), cluster scaling (adding more nodes), and database scaling (read replicas and sharding).

### Scaling Objectives

| Metric | Target | Scaling Strategy |
|--------|--------|------------------|
| **Request Latency (P95)** | <500ms | HPA based on latency |
| **Request Latency (P99)** | <2s | HPA + VPA optimization |
| **Throughput** | 1000+ req/sec | HPA + cluster autoscaling |
| **Resource Utilization** | 60-80% CPU/Memory | VPA + right-sizing |
| **Cost Efficiency** | <$5 per 1M requests | HPA min replicas + spot instances |
| **Availability** | 99.9% uptime | Multi-replica + PDB |

### Architecture for Scaling

```mermaid
graph TB
    subgraph "Load Distribution"
        LB[Load Balancer]
        ING[Ingress Controller]
    end

    subgraph "Application Tier - Auto-Scaling"
        REFLEX[Reflex Layer<br/>3-20 replicas<br/>HPA: CPU 60%]
        ORCH[Orchestrator<br/>2-10 replicas<br/>HPA: CPU 70%]

        subgraph "Arms - Independent HPA"
            PLANNER[Planner<br/>1-5 replicas]
            EXEC[Executor<br/>1-10 replicas]
            CODER[Coder<br/>1-8 replicas]
            JUDGE[Judge<br/>1-5 replicas]
            GUARD[Guardian<br/>2-10 replicas]
            RETR[Retriever<br/>1-8 replicas]
        end
    end

    subgraph "Data Tier - Scaling"
        PG_PRIMARY[(PostgreSQL Primary)]
        PG_REPLICA1[(PG Replica 1)]
        PG_REPLICA2[(PG Replica 2)]
        REDIS_CLUSTER[(Redis Cluster<br/>6 nodes)]
        QDRANT_SHARD1[(Qdrant Shard 1)]
        QDRANT_SHARD2[(Qdrant Shard 2)]
    end

    subgraph "Infrastructure"
        CA[Cluster Autoscaler]
        NODES[Kubernetes Nodes<br/>3-20 nodes]
    end

    LB --> ING
    ING --> REFLEX
    REFLEX --> ORCH
    ORCH --> PLANNER & EXEC & CODER & JUDGE & GUARD & RETR

    ORCH -.read.-> PG_REPLICA1 & PG_REPLICA2
    ORCH -.write.-> PG_PRIMARY
    PG_PRIMARY -.replicate.-> PG_REPLICA1 & PG_REPLICA2

    REFLEX --> REDIS_CLUSTER
    RETR --> QDRANT_SHARD1 & QDRANT_SHARD2

    CA --> NODES
```

---

## Scaling Strategies

### 1. Reactive Scaling (HPA)

**Description**: Scale based on current metrics (CPU, memory, custom metrics)

**Advantages**:
- Automatic response to load changes
- No manual intervention required
- Cost-efficient (scale down when idle)

**Disadvantages**:
- Lag time between metric breach and new pods ready (~2-3 minutes)
- Can't anticipate traffic spikes

**Best For**: Steady-state workloads with gradual load changes

### 2. Predictive Scaling (KEDA)

**Description**: Scale based on predicted metrics using historical data

**Advantages**:
- Proactive scaling before load arrives
- Better for spiky traffic patterns
- Reduces cold start delays

**Disadvantages**:
- Requires historical data for prediction
- More complex configuration

**Best For**: Workloads with predictable patterns (e.g., business hours traffic)

### 3. Manual Scaling

**Description**: Administrator manually sets replica count

**Advantages**:
- Full control over resource allocation
- Predictable costs

**Disadvantages**:
- No automatic response to load
- Risk of under/over-provisioning

**Best For**: Development, testing, or very stable workloads

---

## Horizontal Pod Autoscaling (HPA)

### HPA Overview

Horizontal Pod Autoscaler automatically scales the number of pod replicas based on observed metrics. OctoLLM uses HPA for all stateless components.

### Orchestrator HPA

```yaml
# k8s/hpa/orchestrator-hpa.yaml
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
  maxReplicas: 10
  metrics:
    # CPU-based scaling
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    # Memory-based scaling
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
    # Custom metric: Task queue depth
    - type: Pods
      pods:
        metric:
          name: octollm_task_queue_depth
        target:
          type: AverageValue
          averageValue: "10"
    # Custom metric: API latency (P95)
    - type: Pods
      pods:
        metric:
          name: octollm_api_latency_p95_seconds
        target:
          type: AverageValue
          averageValue: "0.5"  # 500ms
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
      policies:
        - type: Percent
          value: 50  # Scale down max 50% of current replicas
          periodSeconds: 60
        - type: Pods
          value: 2  # Or max 2 pods at a time
          periodSeconds: 60
      selectPolicy: Min  # Use most conservative policy
    scaleUp:
      stabilizationWindowSeconds: 0  # Scale up immediately
      policies:
        - type: Percent
          value: 100  # Can double replicas
          periodSeconds: 60
        - type: Pods
          value: 4  # Or add max 4 pods at a time
          periodSeconds: 60
      selectPolicy: Max  # Use most aggressive policy
```

### Reflex Layer HPA

```yaml
# k8s/hpa/reflex-layer-hpa.yaml
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
  minReplicas: 3  # Higher minimum for high throughput
  maxReplicas: 20
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 60  # Lower threshold for faster response
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 75
    # Custom metric: Request rate
    - type: Pods
      pods:
        metric:
          name: octollm_reflex_requests_per_second
        target:
          type: AverageValue
          averageValue: "500"  # 500 req/sec per pod
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 180  # 3 minutes
      policies:
        - type: Percent
          value: 30
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0
      policies:
        - type: Percent
          value: 150  # Can add 150% of current replicas
          periodSeconds: 30  # Every 30 seconds
      selectPolicy: Max
```

### Arm-Specific HPAs

**Planner Arm**:
```yaml
# k8s/hpa/planner-arm-hpa.yaml
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
  minReplicas: 1
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 75
    # Custom: Planning requests queue
    - type: Pods
      pods:
        metric:
          name: octollm_planner_queue_depth
        target:
          type: AverageValue
          averageValue: "5"
```

**Executor Arm** (highest scaling needs):
```yaml
# k8s/hpa/executor-arm-hpa.yaml
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
  maxReplicas: 10  # Highest max for high execution demand
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
    # Custom: Execution queue depth
    - type: Pods
      pods:
        metric:
          name: octollm_executor_queue_depth
        target:
          type: AverageValue
          averageValue: "8"
```

**Coder Arm**:
```yaml
# k8s/hpa/coder-arm-hpa.yaml
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
  minReplicas: 1
  maxReplicas: 8
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 75
    - type: Pods
      pods:
        metric:
          name: octollm_coder_queue_depth
        target:
          type: AverageValue
          averageValue: "6"
```

**Judge Arm**:
```yaml
# k8s/hpa/judge-arm-hpa.yaml
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
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

**Guardian Arm** (critical security component):
```yaml
# k8s/hpa/guardian-arm-hpa.yaml
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
  minReplicas: 2  # Always keep 2 for security
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 65
    # PII detection is CPU-intensive
    - type: Pods
      pods:
        metric:
          name: octollm_guardian_pii_checks_per_second
        target:
          type: AverageValue
          averageValue: "100"
```

**Retriever Arm**:
```yaml
# k8s/hpa/retriever-arm-hpa.yaml
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
  minReplicas: 1
  maxReplicas: 8
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    # Custom: Vector search latency
    - type: Pods
      pods:
        metric:
          name: octollm_retriever_latency_p95_seconds
        target:
          type: AverageValue
          averageValue: "0.2"  # 200ms
```

### Custom Metrics Implementation

To enable custom metrics-based HPA, you need to expose Prometheus metrics and configure the Prometheus Adapter:

**1. Application Metrics** (already implemented in `docs/engineering/logging-observability.md`):

```python
# orchestrator/metrics.py
from prometheus_client import Gauge

TASK_QUEUE_DEPTH = Gauge(
    'octollm_task_queue_depth',
    'Number of tasks waiting in queue',
    ['component']
)

API_LATENCY_P95 = Gauge(
    'octollm_api_latency_p95_seconds',
    'API latency at 95th percentile',
    ['endpoint']
)
```

**2. Prometheus Adapter Configuration**:

```yaml
# k8s/monitoring/prometheus-adapter-config.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: adapter-config
  namespace: monitoring
data:
  config.yaml: |
    rules:
      # Task queue depth metric
      - seriesQuery: 'octollm_task_queue_depth'
        resources:
          overrides:
            namespace: {resource: "namespace"}
            pod: {resource: "pod"}
        name:
          matches: "^octollm_task_queue_depth"
          as: "octollm_task_queue_depth"
        metricsQuery: 'avg_over_time(octollm_task_queue_depth[1m])'

      # API latency metric
      - seriesQuery: 'octollm_api_latency_p95_seconds'
        resources:
          overrides:
            namespace: {resource: "namespace"}
            pod: {resource: "pod"}
        name:
          matches: "^octollm_api_latency_p95_seconds"
          as: "octollm_api_latency_p95_seconds"
        metricsQuery: 'max_over_time(octollm_api_latency_p95_seconds[1m])'

      # Reflex requests per second
      - seriesQuery: 'octollm_reflex_http_requests_total'
        resources:
          overrides:
            namespace: {resource: "namespace"}
            pod: {resource: "pod"}
        name:
          matches: "^octollm_reflex_http_requests_total"
          as: "octollm_reflex_requests_per_second"
        metricsQuery: 'rate(octollm_reflex_http_requests_total[1m])'
```

**3. Deploy Prometheus Adapter**:

```bash
# Add Prometheus Community Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install Prometheus Adapter
helm install prometheus-adapter prometheus-community/prometheus-adapter \
  --namespace monitoring \
  --create-namespace \
  --set prometheus.url=http://prometheus-server.monitoring.svc \
  --set prometheus.port=80 \
  -f k8s/monitoring/prometheus-adapter-config.yaml
```

**4. Verify Custom Metrics**:

```bash
# Check available custom metrics
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1" | jq .

# Query specific metric
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1/namespaces/octollm/pods/*/octollm_task_queue_depth" | jq .
```

---

## Vertical Pod Autoscaling (VPA)

### VPA Overview

Vertical Pod Autoscaler automatically adjusts CPU and memory requests/limits based on actual usage patterns. Use VPA when:
- You don't know optimal resource requests
- Resource usage varies significantly over time
- You want right-sizing recommendations

**Important**: VPA and HPA can conflict if both scale on CPU/memory. Use VPA in "Recommendation" mode with HPA, or use VPA for custom metrics only.

### Orchestrator VPA

```yaml
# k8s/vpa/orchestrator-vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: orchestrator-vpa
  namespace: octollm
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orchestrator
  updatePolicy:
    updateMode: "Recreate"  # Options: Off, Initial, Recreate, Auto
  resourcePolicy:
    containerPolicies:
      - containerName: orchestrator
        minAllowed:
          cpu: 200m
          memory: 512Mi
        maxAllowed:
          cpu: 4000m
          memory: 8Gi
        controlledResources: ["cpu", "memory"]
        # Scaling mode: Off (recommendations only), Auto (apply automatically)
        mode: Auto
```

### VPA Update Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Off** | Only provide recommendations | Testing, analysis |
| **Initial** | Set requests on pod creation only | Stable workloads with HPA |
| **Recreate** | Update by evicting and recreating pods | Stateless apps, can tolerate restarts |
| **Auto** | Update in-place (requires k8s 1.27+) | Best option if supported |

### Combined HPA + VPA Strategy

**Option 1: VPA in "Off" mode (Recommendations Only)**

```yaml
# k8s/vpa/orchestrator-vpa-recommendations.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: orchestrator-vpa
  namespace: octollm
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: orchestrator
  updatePolicy:
    updateMode: "Off"  # Only recommendations, no automatic updates
```

Then manually review recommendations:

```bash
# Get VPA recommendations
kubectl describe vpa orchestrator-vpa -n octollm

# Example output:
# Recommendation:
#   Container Recommendations:
#     Container Name:  orchestrator
#     Lower Bound:
#       Cpu:     500m
#       Memory:  1Gi
#     Target:
#       Cpu:     1000m
#       Memory:  2Gi
#     Uncapped Target:
#       Cpu:     1500m
#       Memory:  3Gi
#     Upper Bound:
#       Cpu:     2000m
#       Memory:  4Gi
```

**Option 2: HPA for horizontal scaling, VPA for vertical (separate metrics)**

```yaml
# HPA scales on custom metrics (queue depth)
# VPA scales on CPU/memory
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: orchestrator-hpa
spec:
  metrics:
    # Only custom metrics, no CPU/memory
    - type: Pods
      pods:
        metric:
          name: octollm_task_queue_depth
        target:
          type: AverageValue
          averageValue: "10"
---
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: orchestrator-vpa
spec:
  updatePolicy:
    updateMode: "Auto"
  resourcePolicy:
    containerPolicies:
      - containerName: orchestrator
        # VPA manages CPU/memory
        controlledResources: ["cpu", "memory"]
```

### VPA for All Components

```bash
# Apply VPAs for all arms
for arm in planner executor coder judge guardian retriever; do
  cat <<EOF | kubectl apply -f -
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: ${arm}-arm-vpa
  namespace: octollm
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: ${arm}-arm
  updatePolicy:
    updateMode: "Off"  # Recommendations only with HPA
  resourcePolicy:
    containerPolicies:
      - containerName: ${arm}
        minAllowed:
          cpu: 100m
          memory: 256Mi
        maxAllowed:
          cpu: 2000m
          memory: 4Gi
        controlledResources: ["cpu", "memory"]
EOF
done
```

---

## Cluster Autoscaling

### Cluster Autoscaler Overview

Cluster Autoscaler automatically adds or removes nodes based on pod resource requests. It scales the cluster when:
- Pods are unschedulable due to insufficient resources
- Nodes are underutilized (<50% for extended period)

### GKE Cluster Autoscaler

```bash
# Enable Cluster Autoscaler on GKE
gcloud container clusters update CLUSTER_NAME \
  --enable-autoscaling \
  --min-nodes 3 \
  --max-nodes 20 \
  --zone ZONE

# Per node pool
gcloud container node-pools update POOL_NAME \
  --cluster=CLUSTER_NAME \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10 \
  --zone=ZONE
```

### EKS Cluster Autoscaler

```yaml
# k8s/cluster-autoscaler/eks-cluster-autoscaler.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: cluster-autoscaler
  namespace: kube-system
spec:
  replicas: 1
  selector:
    matchLabels:
      app: cluster-autoscaler
  template:
    metadata:
      labels:
        app: cluster-autoscaler
    spec:
      serviceAccountName: cluster-autoscaler
      containers:
        - name: cluster-autoscaler
          image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.28.0
          command:
            - ./cluster-autoscaler
            - --v=4
            - --stderrthreshold=info
            - --cloud-provider=aws
            - --skip-nodes-with-local-storage=false
            - --expander=least-waste
            - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/CLUSTER_NAME
            - --balance-similar-node-groups
            - --skip-nodes-with-system-pods=false
          env:
            - name: AWS_REGION
              value: us-west-2
          resources:
            requests:
              cpu: 100m
              memory: 300Mi
            limits:
              cpu: 100m
              memory: 300Mi
```

### AKS Cluster Autoscaler

```bash
# Enable on AKS
az aks update \
  --resource-group RESOURCE_GROUP \
  --name CLUSTER_NAME \
  --enable-cluster-autoscaler \
  --min-count 3 \
  --max-count 20
```

### Node Affinity and Taints/Tolerations

**Database Node Pool** (high IOPS, no application pods):

```yaml
# k8s/nodes/database-nodepool-taint.yaml
# Apply taint to database nodes
kubectl taint nodes DB_NODE_NAME dedicated=database:NoSchedule

# PostgreSQL StatefulSet with toleration
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgresql
spec:
  template:
    spec:
      tolerations:
        - key: "dedicated"
          operator: "Equal"
          value: "database"
          effect: "NoSchedule"
      affinity:
        nodeAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            nodeSelectorTerms:
              - matchExpressions:
                  - key: node-type
                    operator: In
                    values:
                      - database
```

**Arm Pod Distribution** (spread across availability zones):

```yaml
# k8s/deployments/executor-arm-with-affinity.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: executor-arm
spec:
  template:
    spec:
      affinity:
        # Prefer spreading across zones
        podAntiAffinity:
          preferredDuringSchedulingIgnoredDuringExecution:
            - weight: 100
              podAffinityTerm:
                labelSelector:
                  matchExpressions:
                    - key: app
                      operator: In
                      values:
                        - executor-arm
                topologyKey: topology.kubernetes.io/zone
        # Require at least 2 different nodes
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
            - labelSelector:
                matchExpressions:
                  - key: app
                    operator: In
                    values:
                      - executor-arm
              topologyKey: kubernetes.io/hostname
```

---

## Database Scaling

### PostgreSQL Read Replicas

**Primary-Replica Setup with pgpool-II**:

```yaml
# k8s/databases/postgresql-replica.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgresql-replica
  namespace: octollm
spec:
  serviceName: postgresql-replica
  replicas: 2  # 2 read replicas
  selector:
    matchLabels:
      app: postgresql-replica
  template:
    metadata:
      labels:
        app: postgresql-replica
    spec:
      containers:
        - name: postgresql
          image: postgres:15-alpine
          env:
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: password
            - name: POSTGRES_REPLICATION_MODE
              value: "slave"
            - name: POSTGRES_MASTER_HOST
              value: "postgresql-primary.octollm.svc.cluster.local"
            - name: POSTGRES_REPLICATION_USER
              value: "replicator"
            - name: POSTGRES_REPLICATION_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: postgres-secret
                  key: replication-password
          volumeMounts:
            - name: data
              mountPath: /var/lib/postgresql/data
          resources:
            requests:
              cpu: 1000m
              memory: 2Gi
            limits:
              cpu: 2000m
              memory: 4Gi
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: octollm-fast-ssd
        resources:
          requests:
            storage: 50Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgresql-replica
  namespace: octollm
spec:
  selector:
    app: postgresql-replica
  ports:
    - port: 5432
      targetPort: 5432
  type: ClusterIP
```

**Application Configuration for Read Replicas**:

```python
# orchestrator/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import random

# Connection strings
PRIMARY_URL = "postgresql://user:pass@postgresql-primary:5432/octollm"
REPLICA_URLS = [
    "postgresql://user:pass@postgresql-replica-0:5432/octollm",
    "postgresql://user:pass@postgresql-replica-1:5432/octollm",
]

# Create engines
primary_engine = create_engine(PRIMARY_URL, pool_size=10, max_overflow=20)
replica_engines = [
    create_engine(url, pool_size=5, max_overflow=10) for url in REPLICA_URLS
]

# Session makers
PrimarySession = sessionmaker(bind=primary_engine)
ReplicaSession = sessionmaker(bind=random.choice(replica_engines))

# Usage
def get_task(task_id: str):
    """Read from replica"""
    session = ReplicaSession()
    return session.query(Task).filter(Task.id == task_id).first()

def create_task(task: Task):
    """Write to primary"""
    session = PrimarySession()
    session.add(task)
    session.commit()
```

### Qdrant Scaling and Sharding

**Qdrant Cluster Setup** (3 nodes with sharding):

```yaml
# k8s/databases/qdrant-cluster.yaml
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
      containers:
        - name: qdrant
          image: qdrant/qdrant:v1.7.0
          ports:
            - containerPort: 6333
              name: http
            - containerPort: 6334
              name: grpc
          env:
            - name: QDRANT_CLUSTER_ENABLED
              value: "true"
            - name: QDRANT_CLUSTER_P2P_PORT
              value: "6335"
            # Use StatefulSet pod names for cluster discovery
            - name: QDRANT_CLUSTER_BOOTSTRAP_PEERS
              value: "qdrant-0.qdrant:6335,qdrant-1.qdrant:6335,qdrant-2.qdrant:6335"
          volumeMounts:
            - name: data
              mountPath: /qdrant/storage
          resources:
            requests:
              cpu: 500m
              memory: 2Gi
            limits:
              cpu: 2000m
              memory: 8Gi
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: octollm-fast-ssd
        resources:
          requests:
            storage: 100Gi
```

**Qdrant Collection with Sharding**:

```python
# arms/retriever/memory_setup.py
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, ShardingMethod

client = QdrantClient(url="http://qdrant:6333")

# Create collection with sharding
client.create_collection(
    collection_name="knowledge_base",
    vectors_config=VectorParams(
        size=384,
        distance=Distance.COSINE
    ),
    shard_number=6,  # 2 shards per node × 3 nodes
    sharding_method=ShardingMethod.AUTO,
    replication_factor=2,  # Each shard replicated 2x for redundancy
    write_consistency_factor=1,  # Acknowledge after 1 replica writes
)
```

### Redis Cluster Mode

**Redis Cluster Deployment** (6 nodes: 3 masters + 3 replicas):

```yaml
# k8s/databases/redis-cluster.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cluster
  namespace: octollm
spec:
  serviceName: redis-cluster
  replicas: 6
  selector:
    matchLabels:
      app: redis-cluster
  template:
    metadata:
      labels:
        app: redis-cluster
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          command:
            - redis-server
            - --cluster-enabled
            - "yes"
            - --cluster-config-file
            - /data/nodes.conf
            - --cluster-node-timeout
            - "5000"
            - --appendonly
            - "yes"
            - --maxmemory
            - "2gb"
            - --maxmemory-policy
            - "allkeys-lru"
          ports:
            - containerPort: 6379
              name: client
            - containerPort: 16379
              name: gossip
          volumeMounts:
            - name: data
              mountPath: /data
          resources:
            requests:
              cpu: 500m
              memory: 2Gi
            limits:
              cpu: 1000m
              memory: 3Gi
  volumeClaimTemplates:
    - metadata:
        name: data
      spec:
        accessModes: ["ReadWriteOnce"]
        storageClassName: octollm-fast-ssd
        resources:
          requests:
            storage: 20Gi
```

**Initialize Redis Cluster**:

```bash
# Wait for all pods to be ready
kubectl wait --for=condition=ready pod -l app=redis-cluster -n octollm --timeout=300s

# Create cluster (3 masters, 3 replicas)
kubectl exec -it redis-cluster-0 -n octollm -- redis-cli --cluster create \
  redis-cluster-0.redis-cluster:6379 \
  redis-cluster-1.redis-cluster:6379 \
  redis-cluster-2.redis-cluster:6379 \
  redis-cluster-3.redis-cluster:6379 \
  redis-cluster-4.redis-cluster:6379 \
  redis-cluster-5.redis-cluster:6379 \
  --cluster-replicas 1 \
  --cluster-yes

# Verify cluster
kubectl exec -it redis-cluster-0 -n octollm -- redis-cli cluster info
kubectl exec -it redis-cluster-0 -n octollm -- redis-cli cluster nodes
```

---

## Caching Strategies

### Multi-Tier Caching Architecture

```mermaid
graph TB
    REQ[Request]

    subgraph "L1 Cache - In-Memory"
        L1[Python @lru_cache<br/>TTL: 60s<br/>Size: 128 entries]
    end

    subgraph "L2 Cache - Redis"
        L2[Redis Cluster<br/>TTL: 5 min<br/>Size: 10GB]
    end

    subgraph "L3 Cache - Database Result Cache"
        L3[PostgreSQL Materialized Views<br/>Refresh: 1 hour]
    end

    subgraph "Source"
        DB[(Database)]
        LLM[LLM API]
        VECTOR[(Vector DB)]
    end

    REQ --> L1
    L1 -->|Miss| L2
    L2 -->|Miss| L3
    L3 -->|Miss| DB & LLM & VECTOR

    DB & LLM & VECTOR -.Populate.-> L3
    L3 -.Populate.-> L2
    L2 -.Populate.-> L1
```

### L1: In-Memory Caching (Python)

```python
# orchestrator/caching.py
from functools import lru_cache
from typing import Dict, Any
import time
import hashlib

class TTLCache:
    """Time-based LRU cache"""
    def __init__(self, maxsize: int = 128, ttl: int = 60):
        self.maxsize = maxsize
        self.ttl = ttl
        self.cache: Dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any:
        if key in self.cache:
            value, timestamp = self.cache[key]
            if time.time() - timestamp < self.ttl:
                return value
            else:
                del self.cache[key]  # Expired
        return None

    def set(self, key: str, value: Any):
        if len(self.cache) >= self.maxsize:
            # Evict oldest entry
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        self.cache[key] = (value, time.time())

# Global cache instance
task_cache = TTLCache(maxsize=256, ttl=120)  # 2 minutes

def cache_key(*args, **kwargs) -> str:
    """Generate cache key from arguments"""
    key_data = str(args) + str(sorted(kwargs.items()))
    return hashlib.md5(key_data.encode()).hexdigest()

# Usage with decorator
def cached_task_result(ttl: int = 60):
    def decorator(func):
        cache = TTLCache(ttl=ttl)

        def wrapper(*args, **kwargs):
            key = cache_key(*args, **kwargs)
            result = cache.get(key)
            if result is not None:
                return result

            result = func(*args, **kwargs)
            cache.set(key, result)
            return result

        return wrapper
    return decorator

# Example usage
@cached_task_result(ttl=120)
def get_arm_capabilities(arm_id: str) -> Dict:
    """Expensive operation to fetch arm capabilities"""
    # This will be cached for 2 minutes
    return fetch_from_database(arm_id)
```

### L2: Redis Caching

```python
# orchestrator/redis_cache.py
import redis
import json
from typing import Any, Optional
import pickle

class RedisCache:
    """Redis-backed cache with automatic serialization"""

    def __init__(self, redis_url: str, default_ttl: int = 300):
        self.client = redis.from_url(redis_url, decode_responses=False)
        self.default_ttl = default_ttl

    def get(self, key: str) -> Optional[Any]:
        """Get cached value"""
        value = self.client.get(key)
        if value:
            return pickle.loads(value)
        return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set cached value with TTL"""
        serialized = pickle.dumps(value)
        self.client.setex(key, ttl or self.default_ttl, serialized)

    def delete(self, key: str):
        """Invalidate cache entry"""
        self.client.delete(key)

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return self.client.exists(key) > 0

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Get multiple cached values"""
        values = self.client.mget(keys)
        return {
            key: pickle.loads(val) if val else None
            for key, val in zip(keys, values)
        }

    def set_many(self, items: dict[str, Any], ttl: Optional[int] = None):
        """Set multiple cached values"""
        pipe = self.client.pipeline()
        for key, value in items.items():
            serialized = pickle.dumps(value)
            pipe.setex(key, ttl or self.default_ttl, serialized)
        pipe.execute()

# Global cache instance
cache = RedisCache(redis_url="redis://redis-cluster:6379", default_ttl=300)

# Usage example
def get_task_result(task_id: str) -> Dict:
    cache_key = f"task:result:{task_id}"

    # Try L1 cache first (in-memory)
    result = task_cache.get(cache_key)
    if result:
        return result

    # Try L2 cache (Redis)
    result = cache.get(cache_key)
    if result:
        # Populate L1 cache
        task_cache.set(cache_key, result)
        return result

    # Fetch from database
    result = fetch_task_from_db(task_id)

    # Populate both caches
    cache.set(cache_key, result, ttl=600)  # 10 minutes in Redis
    task_cache.set(cache_key, result)      # 2 minutes in memory

    return result
```

### Cache Warming Strategy

```python
# orchestrator/cache_warming.py
import asyncio
from typing import List
import logging

logger = logging.getLogger(__name__)

class CacheWarmer:
    """Proactively warm caches for frequently accessed data"""

    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache

    async def warm_arm_capabilities(self):
        """Pre-cache arm capabilities"""
        arm_ids = ["planner", "executor", "coder", "judge", "guardian", "retriever"]

        for arm_id in arm_ids:
            try:
                capabilities = await fetch_arm_capabilities(arm_id)
                cache_key = f"arm:capabilities:{arm_id}"
                self.cache.set(cache_key, capabilities, ttl=3600)  # 1 hour
                logger.info(f"Warmed cache for arm: {arm_id}")
            except Exception as e:
                logger.error(f"Failed to warm cache for arm {arm_id}: {e}")

    async def warm_common_queries(self):
        """Pre-cache results of common queries"""
        common_queries = [
            "SELECT * FROM entities WHERE entity_type = 'tool' LIMIT 100",
            "SELECT * FROM recent_tasks ORDER BY created_at DESC LIMIT 50",
        ]

        for query in common_queries:
            try:
                result = await execute_query(query)
                cache_key = f"query:{hash(query)}"
                self.cache.set(cache_key, result, ttl=600)  # 10 minutes
            except Exception as e:
                logger.error(f"Failed to warm cache for query: {e}")

    async def warm_on_startup(self):
        """Warm caches on application startup"""
        logger.info("Starting cache warming...")
        await asyncio.gather(
            self.warm_arm_capabilities(),
            self.warm_common_queries(),
        )
        logger.info("Cache warming complete")

    async def warm_periodically(self, interval: int = 300):
        """Periodically refresh caches"""
        while True:
            await asyncio.sleep(interval)
            await self.warm_on_startup()

# Usage in FastAPI startup
from fastapi import FastAPI

app = FastAPI()

@app.on_event("startup")
async def startup_event():
    warmer = CacheWarmer(redis_cache=cache)
    await warmer.warm_on_startup()

    # Start background warming task
    asyncio.create_task(warmer.warm_periodically(interval=600))  # Every 10 min
```

### Cache Invalidation Patterns

```python
# orchestrator/cache_invalidation.py

class CacheInvalidator:
    """Intelligent cache invalidation"""

    def __init__(self, redis_cache: RedisCache):
        self.cache = redis_cache

    def invalidate_task(self, task_id: str):
        """Invalidate all caches related to a task"""
        patterns = [
            f"task:result:{task_id}",
            f"task:status:{task_id}",
            f"task:plan:{task_id}",
        ]
        for pattern in patterns:
            self.cache.delete(pattern)

    def invalidate_arm(self, arm_id: str):
        """Invalidate arm-related caches"""
        self.cache.delete(f"arm:capabilities:{arm_id}")
        self.cache.delete(f"arm:status:{arm_id}")

    def invalidate_pattern(self, pattern: str):
        """Invalidate all keys matching pattern"""
        # Use Redis SCAN for large key spaces
        cursor = 0
        while True:
            cursor, keys = self.cache.client.scan(cursor, match=pattern, count=100)
            if keys:
                self.cache.client.delete(*keys)
            if cursor == 0:
                break

# Usage example: Invalidate on update
def update_task_result(task_id: str, result: Dict):
    # Update database
    save_to_database(task_id, result)

    # Invalidate caches
    invalidator = CacheInvalidator(cache)
    invalidator.invalidate_task(task_id)
```

---

## Load Testing

### K6 Load Testing Scripts

**Basic Load Test**:

```javascript
// tests/load/basic-load-test.js
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '5m', target: 100 },   // Stay at 100 users
    { duration: '2m', target: 200 },   // Ramp up to 200 users
    { duration: '5m', target: 200 },   // Stay at 200 users
    { duration: '2m', target: 0 },     // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<500', 'p(99)<2000'],  // 95% < 500ms, 99% < 2s
    http_req_failed: ['rate<0.05'],                   // Error rate < 5%
    errors: ['rate<0.1'],                             // Custom error rate < 10%
  },
};

// API base URL
const BASE_URL = 'https://octollm.example.com/api/v1';

// Sample tasks
const tasks = [
  { goal: 'List files in /tmp directory', priority: 'low' },
  { goal: 'Write a Python function to sort a list', priority: 'medium' },
  { goal: 'Analyze security of a web application', priority: 'high' },
];

export default function () {
  // Select random task
  const task = tasks[Math.floor(Math.random() * tasks.length)];

  // Submit task
  const submitRes = http.post(
    `${BASE_URL}/tasks`,
    JSON.stringify(task),
    {
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer YOUR_API_KEY'
      },
    }
  );

  check(submitRes, {
    'task submitted': (r) => r.status === 202,
    'task_id returned': (r) => JSON.parse(r.body).task_id !== undefined,
  });

  if (submitRes.status !== 202) {
    errorRate.add(1);
    return;
  }

  const taskId = JSON.parse(submitRes.body).task_id;

  // Poll for completion (max 30 seconds)
  let completed = false;
  for (let i = 0; i < 30 && !completed; i++) {
    sleep(1);

    const statusRes = http.get(`${BASE_URL}/tasks/${taskId}`);
    check(statusRes, {
      'status check successful': (r) => r.status === 200,
    });

    if (statusRes.status === 200) {
      const status = JSON.parse(statusRes.body).status;
      if (status === 'completed' || status === 'failed') {
        completed = true;

        check(statusRes, {
          'task completed successfully': (r) => JSON.parse(r.body).status === 'completed',
        });
      }
    }
  }

  if (!completed) {
    errorRate.add(1);
  }

  sleep(1);  // Think time between requests
}
```

**Stress Test** (push beyond capacity):

```javascript
// tests/load/stress-test.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 100 },
    { duration: '5m', target: 500 },   // Push to 500 users
    { duration: '5m', target: 1000 },  // Push to 1000 users
    { duration: '5m', target: 2000 },  // Push to 2000 users (likely breaking point)
    { duration: '5m', target: 0 },
  ],
  thresholds: {
    // Relaxed thresholds for stress test
    http_req_duration: ['p(50)<1000'],  // Median < 1s
    http_req_failed: ['rate<0.5'],      // Allow higher error rate
  },
};

const BASE_URL = 'https://octollm.example.com/api/v1';

export default function () {
  const res = http.post(
    `${BASE_URL}/tasks`,
    JSON.stringify({ goal: 'Simple task', priority: 'low' }),
    { headers: { 'Content-Type': 'application/json' } }
  );

  check(res, {
    'request completed': (r) => r.status >= 200 && r.status < 500,
  });
}
```

**Soak Test** (sustained load):

```javascript
// tests/load/soak-test.js
export const options = {
  stages: [
    { duration: '5m', target: 100 },      // Ramp up
    { duration: '3h', target: 100 },      // Stay at 100 users for 3 hours
    { duration: '5m', target: 0 },        // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],
    http_req_failed: ['rate<0.01'],       // Very low error rate
  },
};

// Same test logic as basic-load-test.js
```

**Run Load Tests**:

```bash
# Install k6
# macOS
brew install k6

# Linux
sudo apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6

# Run tests
k6 run tests/load/basic-load-test.js

# Run with custom VUs and duration
k6 run --vus 100 --duration 10m tests/load/basic-load-test.js

# Run stress test
k6 run tests/load/stress-test.js

# Run soak test
k6 run tests/load/soak-test.js

# Output results to InfluxDB for Grafana
k6 run --out influxdb=http://localhost:8086/k6 tests/load/basic-load-test.js
```

---

## Cost Optimization

### Cost Analysis

**Monthly Cost Breakdown** (estimated for medium load):

| Component | Resources | Monthly Cost (AWS) | Monthly Cost (GCP) |
|-----------|-----------|-------------------|-------------------|
| **Kubernetes Control Plane** | 1 master node | $73 (EKS) | $73 (GKE) |
| **Worker Nodes** | 4 × c5.2xlarge (8 vCPU, 16GB) | $550 | $500 |
| **Database Storage** | 500 GB SSD | $50 | $85 |
| **Load Balancer** | 1 ALB | $20 | $20 |
| **Data Transfer** | 1 TB egress | $90 | $120 |
| **LLM API Costs** | 10M tokens/day | $300 (GPT-3.5) | Same |
| **Total** | - | **$1,083** | **$1,098** |

### Cost Optimization Strategies

**1. Spot Instances for Non-Critical Workloads**:

```yaml
# k8s/nodes/spot-nodepool.yaml (AWS)
apiVersion: v1
kind: ConfigMap
metadata:
  name: spot-nodepool-config
  namespace: kube-system
data:
  spot-instances.yaml: |
    # Use spot instances for executor and coder arms (can tolerate interruptions)
    nodeSelector:
      node-type: spot
    tolerations:
      - key: "spot"
        operator: "Equal"
        value: "true"
        effect: "NoSchedule"
```

```bash
# Create spot instance node group (EKS)
eksctl create nodegroup \
  --cluster=octollm \
  --name=spot-workers \
  --instance-types=c5.2xlarge,c5.xlarge \
  --spot \
  --nodes-min=1 \
  --nodes-max=10

# GKE
gcloud container node-pools create spot-workers \
  --cluster=octollm \
  --spot \
  --machine-type=n2-standard-8 \
  --num-nodes=2 \
  --enable-autoscaling \
  --min-nodes=1 \
  --max-nodes=10
```

**2. Reserved Capacity for Baseline Load**:

```bash
# Reserve capacity for 2 always-on nodes (40-60% discount)
# AWS: Purchase EC2 Reserved Instances
# GCP: Purchase Committed Use Discounts
# Azure: Purchase Reserved VM Instances

# Example savings:
# On-Demand: c5.2xlarge = $0.34/hr × 24 × 30 = $245/month
# Reserved (1-year): $0.20/hr × 24 × 30 = $145/month
# Savings: $100/month per node = $200/month for 2 nodes
```

**3. Right-Size Pods with VPA**:

```bash
# Use VPA recommendations to reduce over-provisioning
# Example: Orchestrator initially allocated 2 CPU, 4GB RAM
# VPA recommendation: 1 CPU, 2GB RAM (50% reduction)
# Savings: $20-30/month per pod × 2 replicas = $40-60/month
```

**4. LLM API Cost Optimization**:

```python
# orchestrator/llm_optimization.py
from typing import Dict, Any

class LLMCostOptimizer:
    """Optimize LLM API costs"""

    # Model pricing (per 1K tokens)
    PRICING = {
        "gpt-4": {"input": 0.03, "output": 0.06},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-3.5-turbo": {"input": 0.001, "output": 0.002},
        "claude-3-opus": {"input": 0.015, "output": 0.075},
        "claude-3-sonnet": {"input": 0.003, "output": 0.015},
    }

    def select_model(self, task_complexity: str, max_budget: float) -> str:
        """Select cheapest model that meets requirements"""

        if task_complexity == "high":
            # Use expensive model for complex tasks
            return "gpt-4-turbo"
        elif task_complexity == "medium":
            # Use mid-tier model
            return "gpt-3.5-turbo"
        else:
            # Use cheapest model for simple tasks
            return "gpt-3.5-turbo"

    def estimate_cost(self, model: str, tokens: int) -> float:
        """Estimate cost for token usage"""
        pricing = self.PRICING.get(model, self.PRICING["gpt-3.5-turbo"])
        # Assume 50/50 split input/output
        cost = (tokens / 2 / 1000 * pricing["input"]) + \
               (tokens / 2 / 1000 * pricing["output"])
        return cost

    async def call_with_budget(self, prompt: str, max_cost: float) -> Dict[str, Any]:
        """Call LLM with cost constraints"""
        estimated_tokens = len(prompt.split()) * 1.3  # Rough estimate

        # Find cheapest model under budget
        for model in ["gpt-3.5-turbo", "gpt-4-turbo", "gpt-4"]:
            estimated_cost = self.estimate_cost(model, estimated_tokens)
            if estimated_cost <= max_cost:
                return await call_llm(model, prompt)

        raise ValueError(f"No model available under budget ${max_cost}")

# Use in Orchestrator
optimizer = LLMCostOptimizer()
model = optimizer.select_model(task_complexity="low", max_budget=0.01)
```

**5. Caching to Reduce LLM Calls**:

```python
# Target: 40% cache hit rate = 40% reduction in LLM costs
# Example: $300/month LLM costs × 40% = $120/month savings
```

**6. Scale to Zero for Dev/Staging**:

```yaml
# k8s/dev/scale-to-zero.yaml
# Use KEDA with cron scaling for dev environments
apiVersion: keda.sh/v1alpha1
kind: ScaledObject
metadata:
  name: orchestrator-cron-scaling
  namespace: octollm-dev
spec:
  scaleTargetRef:
    name: orchestrator
  minReplicaCount: 0  # Scale to zero
  maxReplicaCount: 2
  triggers:
    # Scale up during business hours only
    - type: cron
      metadata:
        timezone: America/Los_Angeles
        start: 0 9 * * 1-5    # 9 AM Mon-Fri
        end: 0 18 * * 1-5      # 6 PM Mon-Fri
        desiredReplicas: "1"
```

**Total Estimated Savings**:
- Spot instances: $200/month
- Reserved capacity: $200/month
- Right-sizing: $60/month
- LLM caching: $120/month
- Dev scale-to-zero: $100/month
- **Total**: ~$680/month savings (38% reduction)

---

## Performance Monitoring

### Grafana Dashboards for Scaling

```json
{
  "dashboard": {
    "title": "OctoLLM Auto-Scaling Dashboard",
    "panels": [
      {
        "title": "HPA Current Replicas",
        "type": "graph",
        "targets": [
          {
            "expr": "kube_horizontalpodautoscaler_status_current_replicas{namespace=\"octollm\"}",
            "legendFormat": "{{horizontalpodautoscaler}} - current"
          },
          {
            "expr": "kube_horizontalpodautoscaler_status_desired_replicas{namespace=\"octollm\"}",
            "legendFormat": "{{horizontalpodautoscaler}} - desired"
          }
        ]
      },
      {
        "title": "HPA Scaling Events",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(kube_horizontalpodautoscaler_status_current_replicas{namespace=\"octollm\"}[5m])",
            "legendFormat": "{{horizontalpodautoscaler}}"
          }
        ]
      },
      {
        "title": "CPU Utilization vs HPA Target",
        "type": "graph",
        "targets": [
          {
            "expr": "avg(rate(container_cpu_usage_seconds_total{namespace=\"octollm\"}[5m])) by (pod) * 100",
            "legendFormat": "{{pod}} - actual"
          },
          {
            "expr": "kube_horizontalpodautoscaler_spec_target_metric{namespace=\"octollm\",metric_name=\"cpu\"}",
            "legendFormat": "HPA target"
          }
        ]
      },
      {
        "title": "Cluster Node Count",
        "type": "stat",
        "targets": [
          {
            "expr": "count(kube_node_info)"
          }
        ]
      },
      {
        "title": "Pod Scheduling Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(scheduler_scheduling_duration_seconds_bucket[5m]))",
            "legendFormat": "P95 scheduling latency"
          }
        ]
      },
      {
        "title": "Unschedulable Pods",
        "type": "stat",
        "targets": [
          {
            "expr": "sum(kube_pod_status_phase{namespace=\"octollm\",phase=\"Pending\"})"
          }
        ],
        "alert": {
          "conditions": [
            {
              "evaluator": { "type": "gt", "params": [5] },
              "query": { "params": ["A", "5m", "now"] }
            }
          ]
        }
      }
    ]
  }
}
```

### Scaling Metrics to Track

```python
# orchestrator/scaling_metrics.py
from prometheus_client import Gauge, Counter, Histogram

# Scaling decision metrics
SCALING_DECISION = Counter(
    'octollm_scaling_decision_total',
    'Number of scaling decisions',
    ['component', 'direction']  # direction: up, down, none
)

POD_REPLICA_COUNT = Gauge(
    'octollm_pod_replicas',
    'Current number of pod replicas',
    ['component']
)

SCALING_LAG_SECONDS = Histogram(
    'octollm_scaling_lag_seconds',
    'Time from metric breach to new pod ready',
    ['component'],
    buckets=[10, 30, 60, 120, 180, 300]  # 10s to 5min
)

# Track when scaling is triggered
def record_scaling_event(component: str, direction: str, lag_seconds: float):
    SCALING_DECISION.labels(component=component, direction=direction).inc()
    SCALING_LAG_SECONDS.labels(component=component).observe(lag_seconds)

    # Update replica count
    current_replicas = get_current_replica_count(component)
    POD_REPLICA_COUNT.labels(component=component).set(current_replicas)
```

---

## Troubleshooting

### Common Scaling Issues

**Issue 1: HPA Not Scaling**

**Symptoms**:
- CPU/memory usage above target, but no scaling
- `kubectl describe hpa` shows "unknown" metrics

**Diagnosis**:
```bash
# Check HPA status
kubectl describe hpa orchestrator-hpa -n octollm

# Check metrics-server
kubectl get deployment metrics-server -n kube-system
kubectl top nodes
kubectl top pods -n octollm

# Check custom metrics
kubectl get --raw "/apis/custom.metrics.k8s.io/v1beta1"
```

**Resolution**:
```bash
# Install/restart metrics-server
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# For custom metrics, check Prometheus Adapter
kubectl logs -n monitoring deployment/prometheus-adapter
```

**Issue 2: Pods Stuck in Pending (Insufficient Resources)**

**Symptoms**:
- New pods not starting
- Events show "Insufficient cpu" or "Insufficient memory"

**Diagnosis**:
```bash
# Check pending pods
kubectl get pods -n octollm | grep Pending

# Check events
kubectl get events -n octollm --sort-by='.lastTimestamp'

# Check node resources
kubectl describe nodes | grep -A 5 "Allocated resources"
```

**Resolution**:
```bash
# Option 1: Trigger cluster autoscaler (add nodes)
# Cluster autoscaler should automatically add nodes

# Option 2: Reduce resource requests
# Edit deployment to request less CPU/memory

# Option 3: Manually add node
# AWS
eksctl scale nodegroup --cluster=octollm --name=workers --nodes=5

# GCP
gcloud container clusters resize octollm --num-nodes=5
```

**Issue 3: Rapid Scaling Oscillation**

**Symptoms**:
- HPA scales up, then immediately scales down
- Flapping between replica counts

**Diagnosis**:
```bash
# Check HPA behavior config
kubectl get hpa orchestrator-hpa -o yaml | grep -A 20 behavior

# Check metric stability
kubectl top pods -n octollm --watch
```

**Resolution**:
```yaml
# Increase stabilization window
spec:
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 600  # Increase to 10 minutes
    scaleUp:
      stabilizationWindowSeconds: 60   # Keep responsive
```

**Issue 4: Database Read Replica Lag**

**Symptoms**:
- Stale data returned from queries
- Replication lag metrics high

**Diagnosis**:
```sql
-- Check replication lag (PostgreSQL)
SELECT
  client_addr,
  state,
  pg_wal_lsn_diff(pg_current_wal_lsn(), sent_lsn) AS pending_bytes,
  pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn) AS replay_lag_bytes
FROM pg_stat_replication;
```

**Resolution**:
```bash
# Increase replica resources (more disk IOPS)
# Scale up replica instance size

# Reduce write load on primary
# Batch writes, use connection pooling

# Tune PostgreSQL replication settings
wal_level = replica
max_wal_senders = 10
wal_keep_size = 1GB  # Increase if network latency high
```

**Issue 5: Cost Overrun from Over-Scaling**

**Symptoms**:
- Unexpectedly high cloud bill
- Many pods running but low utilization

**Diagnosis**:
```bash
# Check current replica counts
kubectl get hpa -n octollm

# Check pod utilization
kubectl top pods -n octollm

# Check HPA metrics
kubectl describe hpa -n octollm
```

**Resolution**:
```bash
# Reduce maxReplicas in HPA
kubectl patch hpa orchestrator-hpa -n octollm -p '{"spec":{"maxReplicas":5}}'

# Increase target utilization (scale more conservatively)
kubectl patch hpa orchestrator-hpa -n octollm -p '{"spec":{"metrics":[{"type":"Resource","resource":{"name":"cpu","target":{"type":"Utilization","averageUtilization":80}}}]}}'

# Review and optimize resource requests with VPA recommendations
```

---

## Conclusion

This comprehensive scaling guide provides production-ready configurations for:

1. **Horizontal Pod Autoscaling**: CPU, memory, and custom metrics-based scaling for all components
2. **Vertical Pod Autoscaling**: Resource right-sizing recommendations and automatic updates
3. **Cluster Autoscaling**: Automatic node provisioning across cloud providers
4. **Database Scaling**: Read replicas, sharding, and clustering strategies
5. **Caching**: Multi-tier caching with Redis and in-memory strategies
6. **Load Testing**: K6 scripts for stress, soak, and performance testing
7. **Cost Optimization**: Spot instances, reserved capacity, and LLM cost reduction
8. **Monitoring**: Grafana dashboards and Prometheus metrics for scaling observability
9. **Troubleshooting**: Solutions for common scaling issues

### Next Steps

1. **Implement HPAs**: Apply HPA configurations for all components
2. **Enable Cluster Autoscaler**: Configure for your cloud provider
3. **Set Up Monitoring**: Deploy Grafana dashboards for scaling metrics
4. **Run Load Tests**: Establish performance baselines with k6
5. **Optimize Costs**: Implement spot instances and caching strategies
6. **Document Baselines**: Record current performance and cost metrics
7. **Iterate**: Continuously tune based on real-world usage patterns

### See Also

- [Kubernetes Deployment Guide](./kubernetes-deployment.md) - Production deployment
- [Performance Tuning Guide](./performance-tuning.md) - Application-level optimization
- [Monitoring and Alerting Guide](./monitoring-alerting.md) - Observability setup
- [Troubleshooting Playbooks](./troubleshooting-playbooks.md) - Incident response

---

**Document Maintainers**: OctoLLM Operations Team
**Last Review**: 2025-11-10
**Next Review**: 2025-12-10
