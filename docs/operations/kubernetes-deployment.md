# Kubernetes Deployment Guide

**Estimated Time**: 2-3 hours
**Difficulty**: Advanced
**Prerequisites**: Kubernetes cluster access, kubectl configured, basic Kubernetes knowledge

## Overview

This guide walks you through deploying OctoLLM to a production Kubernetes cluster with:
- High availability and auto-scaling
- Persistent storage for databases
- Service mesh integration (optional)
- Monitoring and observability
- Security best practices

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Cluster Requirements](#cluster-requirements)
3. [Namespace Setup](#namespace-setup)
4. [Storage Configuration](#storage-configuration)
5. [Database Deployment](#database-deployment)
6. [Core Services Deployment](#core-services-deployment)
7. [Ingress Configuration](#ingress-configuration)
8. [Scaling Configuration](#scaling-configuration)
9. [Security Hardening](#security-hardening)
10. [Monitoring Setup](#monitoring-setup)
11. [Verification](#verification)
12. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools

```bash
# Verify kubectl installation
kubectl version --client

# Verify Helm installation (v3+)
helm version

# Verify cluster access
kubectl cluster-info
kubectl get nodes
```

### Recommended Versions

| Component | Minimum Version | Recommended |
|-----------|----------------|-------------|
| **Kubernetes** | 1.25+ | 1.28+ |
| **kubectl** | 1.25+ | 1.28+ |
| **Helm** | 3.10+ | 3.13+ |
| **Container Runtime** | containerd 1.6+ | containerd 1.7+ |

### Required Kubernetes Features

- **StorageClasses** - For persistent volumes
- **RBAC** - For service accounts and permissions
- **NetworkPolicies** - For network isolation
- **HorizontalPodAutoscaler** - For auto-scaling
- **Ingress Controller** - For external access (nginx, traefik, etc.)

---

## Cluster Requirements

### Node Resources

**Minimum Cluster** (Development/Testing):
- 3 nodes (1 master, 2 workers)
- 4 vCPU per node
- 16 GB RAM per node
- 100 GB SSD storage per node

**Production Cluster**:
- 5+ nodes (1 master, 4+ workers)
- 8 vCPU per node
- 32 GB RAM per node
- 200 GB SSD storage per node
- Separate node pool for databases (higher IOPS)

### Network Requirements

```yaml
# Required network connectivity
- Intra-cluster: All pods must communicate (CNI configured)
- External API access: OpenAI, Anthropic, etc. (egress allowed)
- Ingress: HTTPS (443) for external requests
- Monitoring: Prometheus scraping (internal)
```

---

## Namespace Setup

### Create OctoLLM Namespace

```bash
# Create namespace
kubectl create namespace octollm

# Set as default for this session
kubectl config set-context --current --namespace=octollm

# Verify
kubectl get namespace octollm
```

### Namespace Configuration

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: octollm
  labels:
    name: octollm
    env: production
---
apiVersion: v1
kind: ResourceQuota
metadata:
  name: octollm-quota
  namespace: octollm
spec:
  hard:
    requests.cpu: "32"
    requests.memory: 64Gi
    requests.storage: 500Gi
    persistentvolumeclaims: "10"
    pods: "50"
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
      cpu: 100m
      memory: 128Mi
    type: Container
```

Apply the configuration:

```bash
kubectl apply -f k8s/namespace.yaml
```

---

## Storage Configuration

### StorageClass Configuration

```yaml
# k8s/storage/storageclass.yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: octollm-fast-ssd
provisioner: kubernetes.io/aws-ebs  # Change based on cloud provider
parameters:
  type: gp3
  iopsPerGB: "50"
  encrypted: "true"
allowVolumeExpansion: true
reclaimPolicy: Retain
volumeBindingMode: WaitForFirstConsumer
```

For different cloud providers:

**AWS (EBS)**:
```yaml
provisioner: kubernetes.io/aws-ebs
parameters:
  type: gp3  # or io2 for higher IOPS
  iopsPerGB: "50"
```

**GCP (Persistent Disk)**:
```yaml
provisioner: kubernetes.io/gce-pd
parameters:
  type: pd-ssd
  replication-type: regional-pd
```

**Azure (Disk)**:
```yaml
provisioner: kubernetes.io/azure-disk
parameters:
  storageaccounttype: Premium_LRS
  kind: Managed
```

Apply storage configuration:

```bash
kubectl apply -f k8s/storage/storageclass.yaml
```

---

## Database Deployment

### PostgreSQL Deployment

```yaml
# k8s/databases/postgres.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: postgres-config
  namespace: octollm
data:
  POSTGRES_DB: octollm
  POSTGRES_USER: octollm
---
apiVersion: v1
kind: Secret
metadata:
  name: postgres-secret
  namespace: octollm
type: Opaque
stringData:
  POSTGRES_PASSWORD: "CHANGE_ME_SECURE_PASSWORD"  # Use sealed secrets in production
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: octollm
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: octollm-fast-ssd
  resources:
    requests:
      storage: 50Gi
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
  namespace: octollm
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        ports:
        - containerPort: 5432
          name: postgres
        envFrom:
        - configMapRef:
            name: postgres-config
        - secretRef:
            name: postgres-secret
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
          subPath: postgres
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
        readinessProbe:
          exec:
            command:
            - pg_isready
            - -U
            - octollm
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: postgres-storage
        persistentVolumeClaim:
          claimName: postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
  namespace: octollm
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
  clusterIP: None  # Headless service for StatefulSet
```

### Redis Deployment

```yaml
# k8s/databases/redis.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: redis-config
  namespace: octollm
data:
  redis.conf: |
    maxmemory 2gb
    maxmemory-policy allkeys-lru
    appendonly yes
    appendfsync everysec
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: octollm
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: octollm-fast-ssd
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis
  namespace: octollm
spec:
  serviceName: redis
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        ports:
        - containerPort: 6379
          name: redis
        command:
        - redis-server
        - /etc/redis/redis.conf
        volumeMounts:
        - name: redis-config
          mountPath: /etc/redis
        - name: redis-storage
          mountPath: /data
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
      volumes:
      - name: redis-config
        configMap:
          name: redis-config
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: redis
  namespace: octollm
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
  clusterIP: None
```

### Qdrant Deployment

```yaml
# k8s/databases/qdrant.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: qdrant-pvc
  namespace: octollm
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: octollm-fast-ssd
  resources:
    requests:
      storage: 20Gi
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
  namespace: octollm
spec:
  serviceName: qdrant
  replicas: 1
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
        volumeMounts:
        - name: qdrant-storage
          mountPath: /qdrant/storage
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
            path: /
            port: 6333
          initialDelaySeconds: 5
          periodSeconds: 5
      volumes:
      - name: qdrant-storage
        persistentVolumeClaim:
          claimName: qdrant-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: qdrant
  namespace: octollm
spec:
  selector:
    app: qdrant
  ports:
  - port: 6333
    targetPort: 6333
    name: http
  - port: 6334
    targetPort: 6334
    name: grpc
  clusterIP: None
```

Deploy all databases:

```bash
kubectl apply -f k8s/databases/postgres.yaml
kubectl apply -f k8s/databases/redis.yaml
kubectl apply -f k8s/databases/qdrant.yaml

# Wait for databases to be ready
kubectl wait --for=condition=ready pod -l app=postgres --timeout=300s
kubectl wait --for=condition=ready pod -l app=redis --timeout=300s
kubectl wait --for=condition=ready pod -l app=qdrant --timeout=300s
```

---

## Core Services Deployment

### ConfigMap for Shared Configuration

```yaml
# k8s/core/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: octollm-config
  namespace: octollm
data:
  LOG_LEVEL: "info"
  ENVIRONMENT: "production"

  # Database URLs (internal DNS)
  POSTGRES_HOST: "postgres.octollm.svc.cluster.local"
  POSTGRES_PORT: "5432"
  POSTGRES_DB: "octollm"

  REDIS_HOST: "redis.octollm.svc.cluster.local"
  REDIS_PORT: "6379"

  QDRANT_HOST: "qdrant.octollm.svc.cluster.local"
  QDRANT_PORT: "6333"
```

### Secret for API Keys

```yaml
# k8s/core/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: octollm-secrets
  namespace: octollm
type: Opaque
stringData:
  # LLM API Keys (replace with actual keys)
  OPENAI_API_KEY: "sk-XXXXXXXXXXXXXXXXXXXXX"
  ANTHROPIC_API_KEY: "sk-ant-XXXXXXXXXXXXXXXXXXXXX"

  # Database credentials
  POSTGRES_PASSWORD: "SECURE_PASSWORD_HERE"

  # JWT Secret for API authentication
  JWT_SECRET: "SECURE_RANDOM_STRING_32_CHARS_MIN"
```

**IMPORTANT**: In production, use **Sealed Secrets** or **External Secrets Operator** to manage secrets securely:

```bash
# Example with Sealed Secrets
kubeseal --format=yaml < k8s/core/secrets.yaml > k8s/core/sealed-secrets.yaml
kubectl apply -f k8s/core/sealed-secrets.yaml
```

### Reflex Layer Deployment

```yaml
# k8s/core/reflex-layer.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: reflex-layer
  namespace: octollm
spec:
  replicas: 3
  selector:
    matchLabels:
      app: reflex-layer
  template:
    metadata:
      labels:
        app: reflex-layer
    spec:
      containers:
      - name: reflex-layer
        image: octollm/reflex-layer:latest
        ports:
        - containerPort: 8001
          name: http
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
        resources:
          requests:
            cpu: 200m
            memory: 256Mi
          limits:
            cpu: 500m
            memory: 512Mi
        livenessProbe:
          httpGet:
            path: /health
            port: 8001
          initialDelaySeconds: 10
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8001
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: reflex-layer
  namespace: octollm
spec:
  selector:
    app: reflex-layer
  ports:
  - port: 8001
    targetPort: 8001
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
```

### Orchestrator Deployment

```yaml
# k8s/core/orchestrator.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: orchestrator
  namespace: octollm
spec:
  replicas: 2
  selector:
    matchLabels:
      app: orchestrator
  template:
    metadata:
      labels:
        app: orchestrator
    spec:
      containers:
      - name: orchestrator
        image: octollm/orchestrator:latest
        ports:
        - containerPort: 8000
          name: http
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
        resources:
          requests:
            cpu: 1000m
            memory: 2Gi
          limits:
            cpu: 2000m
            memory: 4Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 15
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
---
apiVersion: v1
kind: Service
metadata:
  name: orchestrator
  namespace: octollm
spec:
  selector:
    app: orchestrator
  ports:
  - port: 8000
    targetPort: 8000
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
```

### Arm Deployments (Example: Planner Arm)

```yaml
# k8s/arms/planner-arm.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: planner-arm
  namespace: octollm
spec:
  replicas: 2
  selector:
    matchLabels:
      app: planner-arm
  template:
    metadata:
      labels:
        app: planner-arm
    spec:
      containers:
      - name: planner-arm
        image: octollm/planner-arm:latest
        ports:
        - containerPort: 8100
          name: http
        envFrom:
        - configMapRef:
            name: octollm-config
        - secretRef:
            name: octollm-secrets
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
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
---
apiVersion: v1
kind: Service
metadata:
  name: planner-arm
  namespace: octollm
spec:
  selector:
    app: planner-arm
  ports:
  - port: 8100
    targetPort: 8100
  type: ClusterIP
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
```

Deploy core services:

```bash
kubectl apply -f k8s/core/configmap.yaml
kubectl apply -f k8s/core/secrets.yaml
kubectl apply -f k8s/core/reflex-layer.yaml
kubectl apply -f k8s/core/orchestrator.yaml
kubectl apply -f k8s/arms/planner-arm.yaml

# Deploy remaining arms similarly...
# kubectl apply -f k8s/arms/executor-arm.yaml
# kubectl apply -f k8s/arms/coder-arm.yaml
# kubectl apply -f k8s/arms/judge-arm.yaml
# kubectl apply -f k8s/arms/guardian-arm.yaml
# kubectl apply -f k8s/arms/retriever-arm.yaml
```

---

## Ingress Configuration

### NGINX Ingress Controller

```yaml
# k8s/ingress/nginx-ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: octollm-ingress
  namespace: octollm
  annotations:
    kubernetes.io/ingress.class: "nginx"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-connect-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "120"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "120"
spec:
  tls:
  - hosts:
    - api.octollm.example.com
    secretName: octollm-tls
  rules:
  - host: api.octollm.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: orchestrator
            port:
              number: 8000
```

### Install cert-manager for TLS

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Create ClusterIssuer for Let's Encrypt
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF

# Apply ingress
kubectl apply -f k8s/ingress/nginx-ingress.yaml
```

---

## Scaling Configuration

### Cluster Autoscaler (AWS Example)

```yaml
# k8s/scaling/cluster-autoscaler.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: cluster-autoscaler
  namespace: kube-system
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cluster-autoscaler
rules:
  - apiGroups: [""]
    resources: ["events", "endpoints"]
    verbs: ["create", "patch"]
  - apiGroups: [""]
    resources: ["pods/eviction"]
    verbs: ["create"]
  - apiGroups: [""]
    resources: ["pods/status"]
    verbs: ["update"]
  - apiGroups: [""]
    resources: ["endpoints"]
    resourceNames: ["cluster-autoscaler"]
    verbs: ["get", "update"]
  - apiGroups: [""]
    resources: ["nodes"]
    verbs: ["watch", "list", "get", "update"]
  - apiGroups: [""]
    resources: ["pods", "services", "replicationcontrollers", "persistentvolumeclaims", "persistentvolumes"]
    verbs: ["watch", "list", "get"]
  - apiGroups: ["extensions"]
    resources: ["replicasets", "daemonsets"]
    verbs: ["watch", "list", "get"]
  - apiGroups: ["policy"]
    resources: ["poddisruptionbudgets"]
    verbs: ["watch", "list"]
  - apiGroups: ["apps"]
    resources: ["statefulsets", "replicasets", "daemonsets"]
    verbs: ["watch", "list", "get"]
  - apiGroups: ["storage.k8s.io"]
    resources: ["storageclasses", "csinodes"]
    verbs: ["watch", "list", "get"]
  - apiGroups: ["batch", "extensions"]
    resources: ["jobs"]
    verbs: ["get", "list", "watch", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cluster-autoscaler
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: cluster-autoscaler
subjects:
  - kind: ServiceAccount
    name: cluster-autoscaler
    namespace: kube-system
---
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
      - image: k8s.gcr.io/autoscaling/cluster-autoscaler:v1.28.0
        name: cluster-autoscaler
        resources:
          limits:
            cpu: 100m
            memory: 300Mi
          requests:
            cpu: 100m
            memory: 300Mi
        command:
          - ./cluster-autoscaler
          - --v=4
          - --stderrthreshold=info
          - --cloud-provider=aws
          - --skip-nodes-with-local-storage=false
          - --expander=least-waste
          - --node-group-auto-discovery=asg:tag=k8s.io/cluster-autoscaler/enabled,k8s.io/cluster-autoscaler/octollm-cluster
```

### Pod Disruption Budgets

```yaml
# k8s/scaling/pdb.yaml
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

---

## Security Hardening

### Network Policies

```yaml
# k8s/security/network-policies.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: orchestrator-network-policy
  namespace: octollm
spec:
  podSelector:
    matchLabels:
      app: orchestrator
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: reflex-layer
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
  - to:
    - podSelector:
        matchLabels:
          app: qdrant
    ports:
    - protocol: TCP
      port: 6333
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 53  # DNS
    - protocol: UDP
      port: 53
  - to:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 8100  # Arms
    - protocol: TCP
      port: 8101
    - protocol: TCP
      port: 8102
---
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: database-network-policy
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
          app: orchestrator
    - podSelector:
        matchLabels:
          app: planner-arm
    ports:
    - protocol: TCP
      port: 5432
```

### Pod Security Standards

```yaml
# k8s/security/pod-security.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: octollm
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### Security Context Example

```yaml
# Add to deployment templates
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
containers:
- name: orchestrator
  securityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
    capabilities:
      drop:
      - ALL
```

Apply security configurations:

```bash
kubectl apply -f k8s/security/network-policies.yaml
kubectl apply -f k8s/security/pod-security.yaml
```

---

## Monitoring Setup

### Prometheus ServiceMonitor

```yaml
# k8s/monitoring/service-monitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: octollm-metrics
  namespace: octollm
spec:
  selector:
    matchLabels:
      monitoring: "true"
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### Add monitoring labels to services

```yaml
# Update services with label
metadata:
  labels:
    monitoring: "true"
```

### Grafana Dashboard ConfigMap

```yaml
# k8s/monitoring/grafana-dashboard.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: octollm-dashboard
  namespace: monitoring
data:
  octollm-overview.json: |
    {
      "dashboard": {
        "title": "OctoLLM Overview",
        "panels": [
          {
            "title": "Request Rate",
            "targets": [
              {
                "expr": "rate(http_requests_total{namespace=\"octollm\"}[5m])"
              }
            ]
          }
        ]
      }
    }
```

---

## Verification

### Deployment Verification Script

```bash
#!/bin/bash
# k8s/scripts/verify-deployment.sh

set -e

NAMESPACE="octollm"

echo "=== OctoLLM Kubernetes Deployment Verification ==="

# Check namespace
echo -n "Checking namespace... "
kubectl get namespace $NAMESPACE &> /dev/null && echo "✓" || (echo "✗" && exit 1)

# Check databases
echo -n "Checking PostgreSQL... "
kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=60s &> /dev/null && echo "✓" || echo "✗"

echo -n "Checking Redis... "
kubectl wait --for=condition=ready pod -l app=redis -n $NAMESPACE --timeout=60s &> /dev/null && echo "✓" || echo "✗"

echo -n "Checking Qdrant... "
kubectl wait --for=condition=ready pod -l app=qdrant -n $NAMESPACE --timeout=60s &> /dev/null && echo "✓" || echo "✗"

# Check core services
echo -n "Checking Reflex Layer... "
kubectl wait --for=condition=ready pod -l app=reflex-layer -n $NAMESPACE --timeout=60s &> /dev/null && echo "✓" || echo "✗"

echo -n "Checking Orchestrator... "
kubectl wait --for=condition=ready pod -l app=orchestrator -n $NAMESPACE --timeout=60s &> /dev/null && echo "✓" || echo "✗"

# Check arms
for arm in planner executor coder judge guardian retriever; do
  echo -n "Checking ${arm} arm... "
  kubectl wait --for=condition=ready pod -l app=${arm}-arm -n $NAMESPACE --timeout=60s &> /dev/null && echo "✓" || echo "✗"
done

# Test API endpoint
echo -n "Testing API health endpoint... "
ORCHESTRATOR_POD=$(kubectl get pod -l app=orchestrator -n $NAMESPACE -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n $NAMESPACE $ORCHESTRATOR_POD -- curl -sf http://localhost:8000/health &> /dev/null && echo "✓" || echo "✗"

echo ""
echo "=== Deployment Status ==="
kubectl get pods -n $NAMESPACE
```

Run verification:

```bash
chmod +x k8s/scripts/verify-deployment.sh
./k8s/scripts/verify-deployment.sh
```

### Test API from Outside Cluster

```bash
# Get ingress IP/hostname
INGRESS_HOST=$(kubectl get ingress octollm-ingress -n octollm -o jsonpath='{.status.loadBalancer.ingress[0].hostname}')

# Test health endpoint
curl https://$INGRESS_HOST/health

# Submit test task
curl -X POST https://$INGRESS_HOST/api/v1/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "goal": "Test deployment",
    "constraints": ["Quick verification"],
    "priority": "low"
  }'
```

---

## Troubleshooting

### Common Issues

#### 1. Pods Not Starting

```bash
# Check pod status
kubectl get pods -n octollm

# Describe pod for events
kubectl describe pod <pod-name> -n octollm

# Check logs
kubectl logs <pod-name> -n octollm --previous
```

**Common causes**:
- Image pull errors (check image name/tag)
- Resource limits too low
- Missing secrets or configmaps
- Node capacity issues

#### 2. Database Connection Failures

```bash
# Test database connectivity from orchestrator pod
kubectl exec -it <orchestrator-pod> -n octollm -- sh

# Inside pod, test PostgreSQL
nc -zv postgres.octollm.svc.cluster.local 5432

# Test Redis
nc -zv redis.octollm.svc.cluster.local 6379
```

**Solutions**:
- Verify service DNS resolution
- Check network policies
- Ensure databases are ready before deploying apps

#### 3. Ingress Not Working

```bash
# Check ingress status
kubectl get ingress -n octollm
kubectl describe ingress octollm-ingress -n octollm

# Check nginx ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx
```

**Solutions**:
- Verify ingress controller is installed
- Check DNS configuration
- Verify TLS certificate issuance

#### 4. Auto-scaling Not Triggering

```bash
# Check HPA status
kubectl get hpa -n octollm
kubectl describe hpa orchestrator-hpa -n octollm

# Check metrics server
kubectl top pods -n octollm
```

**Solutions**:
- Install metrics-server if missing
- Verify resource requests are set
- Check HPA metric thresholds

### Debugging Commands

```bash
# Get all resources in namespace
kubectl get all -n octollm

# Check events
kubectl get events -n octollm --sort-by='.lastTimestamp'

# Port forward for local access
kubectl port-forward svc/orchestrator 8000:8000 -n octollm

# Execute shell in pod
kubectl exec -it <pod-name> -n octollm -- /bin/sh

# View logs with follow
kubectl logs -f <pod-name> -n octollm

# View logs from all replicas
kubectl logs -l app=orchestrator -n octollm --tail=50
```

---

## Production Checklist

Before going to production, ensure:

### Security
- [ ] Secrets managed with Sealed Secrets or External Secrets
- [ ] Network policies applied and tested
- [ ] Pod security standards enforced
- [ ] RBAC properly configured
- [ ] TLS certificates configured
- [ ] Image scanning enabled
- [ ] Security context configured for all pods

### Reliability
- [ ] Resource requests and limits set
- [ ] Liveness and readiness probes configured
- [ ] HPA configured and tested
- [ ] PDB configured for critical services
- [ ] Backup strategy for databases
- [ ] Disaster recovery plan documented

### Monitoring
- [ ] Prometheus metrics exposed
- [ ] Grafana dashboards created
- [ ] Alerting rules configured
- [ ] Log aggregation configured
- [ ] Distributed tracing enabled

### Performance
- [ ] Load testing completed
- [ ] Database indexes optimized
- [ ] Connection pooling configured
- [ ] Caching strategy verified
- [ ] Resource limits tuned

---

## Next Steps

After successful deployment:

1. **Set up monitoring** - Follow [Monitoring and Alerting Guide](monitoring-alerting.md)
2. **Configure backups** - Set up automated database backups
3. **Load testing** - Use [Performance Tuning Guide](performance-tuning.md)
4. **Disaster recovery** - Test recovery procedures
5. **Documentation** - Document your specific configuration

## See Also

- [Docker Compose Setup](docker-compose-setup.md)
- [Monitoring and Alerting](monitoring-alerting.md)
- [Troubleshooting Playbooks](troubleshooting-playbooks.md)
- [Performance Tuning](performance-tuning.md)
